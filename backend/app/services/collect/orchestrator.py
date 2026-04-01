"""
Collection orchestrator for managing the complete collection pipeline.
"""
import asyncio
import json
import logging
import traceback
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, TypedDict

from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sync import CollectTask
from app.models.raw_data import RawWork, RawAuthor, RawInstitution, AuthorTechBelong
from app.models.tech_element import TechDirection, TechElement
from app.repositories.venue_repository import VenueRepository, VenueSubTaskRepository
from app.repositories.raw_data_repository import (
    RawWorkRepository, RawAuthorRepository, RawInstitutionRepository, AuthorTechBelongRepository
)
from app.services.common.progress import CollectionProgress
from app.services.collect.progress_tracker import ProgressTracker
from app.services.collect.venue_executor import VenueSubTaskExecutor
from app.services.normalizers import AuthorNormalizer, SchoolNormalizer, TechBelongCalculator
from app.services.data_fetchers import WorkFetcher, AuthorFetcher, InstitutionFetcher
from app.models.talent import SelectedWork

logger = logging.getLogger(__name__)


class PhaseProgress:
    """各阶段的进度百分比常量

    用于统一管理采集流水线各阶段的进度显示。
    进度从 0% 到 100%，每个阶段分配一个合理的百分比区间。
    """
    # 任务启动
    TASK_START = 0

    # Phase 0: 预估任务规模
    ESTIMATE = 2

    # Phase 1: 采集论文数据 (5% - 20%)
    COLLECT_START = 5
    COLLECT_END = 20

    # Phase 2: 获取作者数据
    FETCH_AUTHORS = 20

    # Phase 3: 获取机构数据
    FETCH_INSTITUTIONS = 30

    # Phase 4: 标准化学校
    NORMALIZE_SCHOOLS = 40

    # Phase 5: 标准化作者
    NORMALIZE_AUTHORS = 50

    # Phase 6: 计算技术归属
    CALCULATE_TECH_BELONG = 60

    # Phase 7: 同步到服务层
    SYNC_SERVING_LAYER = 70

    # Phase 8: 获取代表作品
    FETCH_SELECTED_WORKS = 75

    # Phase 9: 更新技术标签
    UPDATE_TOPIC_TAGS = 80

    # Phase 10: 更新学校统计
    UPDATE_SCHOOL_STATS = 90

    # Phase 11: 构建统计数据
    BUILD_STATISTICS = 95

    # 任务完成
    COMPLETED = 100


class NewTalentInfo(TypedDict):
    """新入库学者信息

    用于 _fetch_selected_works 方法的参数类型定义。
    """
    talent_id: int
    openalex_author_id: str
    works_count: int


class CollectionOrchestrator:
    """Orchestrates the complete collection pipeline through all 11 phases

    Phase 0:  预估任务规模
    Phase 1:  执行Venue采集子任务（获取论文）
    Phase 2:  获取作者数据
    Phase 3:  获取机构数据
    Phase 4:  标准化学校
    Phase 5:  标准化作者
    Phase 6:  计算技术归属
    Phase 7:  同步到服务层
    Phase 8:  获取代表作品
    Phase 9:  更新技术标签
    Phase 10: 更新学校统计
    Phase 11: 构建统计数据
    """

    def __init__(self, session: AsyncSession, work_fetcher=None, author_fetcher=None, institution_fetcher=None, email: Optional[str] = None):
        self.session = session

        # Repositories
        self.venue_repo = VenueRepository(session)
        self.sub_task_repo = VenueSubTaskRepository(session)
        self.raw_work_repo = RawWorkRepository(session)
        self.raw_author_repo = RawAuthorRepository(session)
        self.raw_inst_repo = RawInstitutionRepository(session)

        # Fetchers (create default if not provided)
        self.work_fetcher = work_fetcher or WorkFetcher(session)
        self.author_fetcher = author_fetcher or AuthorFetcher(session)
        self.institution_fetcher = institution_fetcher or InstitutionFetcher(session)

        # Normalizers
        self.author_normalizer = AuthorNormalizer(session)
        self.school_normalizer = SchoolNormalizer(session)
        self.tech_belong_calculator = TechBelongCalculator(session)

        # Progress tracking
        self.progress_tracker = ProgressTracker(session)

        # Venue executor
        self.venue_executor = VenueSubTaskExecutor(session, self.work_fetcher)

    async def _check_task_status(self, task_id: int) -> str:
        """检查任务当前状态

        Args:
            task_id: 任务ID

        Returns:
            任务状态字符串，如果任务不存在返回 "unknown"
        """
        result = await self.session.execute(
            select(CollectTask.status).where(CollectTask.task_id == task_id)
        )
        status = result.scalar_one_or_none()
        return status or "unknown"

    async def _should_cancel(self, task_id: int) -> bool:
        """检查任务是否应该被取消

        Args:
            task_id: 任务ID

        Returns:
            如果任务状态为 cancelled 或 cancelling 返回 True
        """
        status = await self._check_task_status(task_id)
        return status in ("cancelled", "cancelling")

    async def execute_task(self, task_id: int) -> CollectionProgress:
        """Execute a collection task through all layers

        支持任务取消：在每个阶段开始前检查任务状态，
        如果状态为 cancelled 或 cancelling，则停止执行。
        """
        progress = self.progress_tracker.create_progress(task_id)
        self.progress_tracker.reset_logs()

        # Get task
        task = await self.session.execute(
            select(CollectTask).where(CollectTask.task_id == task_id)
        )
        task = task.scalar_one_or_none()
        if not task:
            progress.status = "failed"
            progress.errors.append("Task not found")
            return progress

        # Update task status
        await self.progress_tracker.update_task_status(task, "running")
        self.progress_tracker.add_log("info", "任务开始执行")
        await self.session.flush()

        try:
            # Phase 0: Estimate total works count
            await self.progress_tracker.update_progress(task, "预估任务规模", PhaseProgress.ESTIMATE)
            estimated_total = await self._estimate_total_works(task)

            # 处理预估失败的情况
            if estimated_total < 0:
                self.progress_tracker.add_log("warning", "预估失败，使用 Venue 数量计算进度")
                progress.estimated_works = 0
            else:
                progress.estimated_works = estimated_total
                if estimated_total > 0:
                    self.progress_tracker.add_log("info", f"预估论文总数: {estimated_total}")
                    task.total_records = estimated_total  # 预存预计数

            # Commit after estimation to release database lock
            await self.session.commit()

            # 检查取消
            if await self._should_cancel(task_id):
                await self._handle_cancellation(task, progress)
                return progress

            # Phase 1: Execute venue sub-tasks
            await self.progress_tracker.update_progress(task, "采集论文数据", PhaseProgress.COLLECT_START)
            await self._execute_venue_sub_tasks(task, progress)
            # Commit after venue collection to release database lock
            await self.session.commit()

            # 检查取消
            if await self._should_cancel(task_id):
                await self._handle_cancellation(task, progress)
                return progress

            # Phase 2: Fetch authors from collected author IDs
            await self.progress_tracker.update_progress(task, "获取作者数据", PhaseProgress.FETCH_AUTHORS)
            await self._fetch_all_authors(task_id, progress)
            # Commit after author fetch to release database lock
            await self.session.commit()

            # 检查取消
            if await self._should_cancel(task_id):
                await self._handle_cancellation(task, progress)
                return progress

            # Phase 3: Fetch institutions from collected institution IDs
            await self.progress_tracker.update_progress(task, "获取机构数据", PhaseProgress.FETCH_INSTITUTIONS)
            await self._fetch_all_institutions(task_id, progress)
            # Commit after institution fetch to release database lock
            await self.session.commit()

            # 检查取消
            if await self._should_cancel(task_id):
                await self._handle_cancellation(task, progress)
                return progress

            # Phase 4: Normalize schools
            await self.progress_tracker.update_progress(task, "标准化学校", PhaseProgress.NORMALIZE_SCHOOLS)
            await self._normalize_schools(task_id, progress)
            # Commit after school normalization to release database lock
            await self.session.commit()

            # 检查取消
            if await self._should_cancel(task_id):
                await self._handle_cancellation(task, progress)
                return progress

            # Phase 5: Normalize authors
            await self.progress_tracker.update_progress(task, "标准化作者", PhaseProgress.NORMALIZE_AUTHORS)
            await self._normalize_authors(task_id, progress)
            # Commit after author normalization to release database lock
            await self.session.commit()

            # 检查取消
            if await self._should_cancel(task_id):
                await self._handle_cancellation(task, progress)
                return progress

            # Phase 6: Calculate tech belong relationships
            await self.progress_tracker.update_progress(task, "计算技术归属", PhaseProgress.CALCULATE_TECH_BELONG)
            await self._calculate_tech_belong(task_id, task.tech_element_id)
            # Commit after tech belong calculation to release database lock
            await self.session.commit()

            # 检查取消
            if await self._should_cancel(task_id):
                await self._handle_cancellation(task, progress)
                return progress

            # Phase 7: Sync to serving layer (delegated to sync service)
            await self.progress_tracker.update_progress(task, "同步到服务层", PhaseProgress.SYNC_SERVING_LAYER)
            new_talents = await self._sync_to_serving_layer(task_id, task.tech_element_id, progress)
            # Commit after serving layer sync to release database lock
            await self.session.commit()

            # 检查取消
            if await self._should_cancel(task_id):
                await self._handle_cancellation(task, progress)
                return progress

            # Phase 8: Fetch selected works for NEW talents
            await self.progress_tracker.update_progress(task, "获取代表作品", PhaseProgress.FETCH_SELECTED_WORKS)
            await self._fetch_selected_works(new_talents, progress)
            # Commit after fetching selected works to release database lock
            await self.session.commit()

            # 检查取消
            if await self._should_cancel(task_id):
                await self._handle_cancellation(task, progress)
                return progress

            # Phase 9: Update talent topic_tags from tech tags
            await self.progress_tracker.update_progress(task, "更新技术标签", PhaseProgress.UPDATE_TOPIC_TAGS)
            await self._update_talent_topic_tags(task_id, progress)
            # Commit after updating topic tags to release database lock
            await self.session.commit()

            # 检查取消
            if await self._should_cancel(task_id):
                await self._handle_cancellation(task, progress)
                return progress

            # Phase 10: Update school statistics
            await self.progress_tracker.update_progress(task, "更新学校统计", PhaseProgress.UPDATE_SCHOOL_STATS)
            await self._update_school_statistics(task_id, progress)
            # Commit after updating school statistics to release database lock
            await self.session.commit()

            # 检查取消
            if await self._should_cancel(task_id):
                await self._handle_cancellation(task, progress)
                return progress

            # Phase 11: Build statistics for homepage
            await self.progress_tracker.update_progress(task, "构建统计数据", PhaseProgress.BUILD_STATISTICS)
            await self._build_statistics(task_id, progress)
            # Commit after building statistics to release database lock
            await self.session.commit()

            # Update task statistics
            # total_records: 采集论文数
            # success_records: 入库人才数
            # processed_records: 标准化作者数
            # skipped_records: 标准化学校数 (复用此字段)
            task.total_records = progress.total_works
            task.success_records = progress.synced_authors
            task.processed_records = progress.normalized_authors
            task.skipped_records = progress.normalized_schools

            # Mark task as completed
            await self.progress_tracker.update_task_status(task, "completed")
            progress.status = "completed"
            self.progress_tracker.add_log("info", "任务执行完成")

        except asyncio.CancelledError:
            # 任务被取消
            await self.progress_tracker.update_task_status(task, "cancelled")
            progress.status = "cancelled"
            self.progress_tracker.add_log("info", "任务被取消")

        except Exception as e:
            # 记录完整堆栈跟踪
            error_detail = {
                "error": str(e),
                "type": type(e).__name__,
                "traceback": traceback.format_exc(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            await self.progress_tracker.update_task_status(task, "failed", str(e))
            progress.status = "failed"
            progress.errors.append(error_detail)
            self.progress_tracker.add_log("error", f"任务执行失败: {str(e)}", error_detail)
            logger.error(f"Task {task_id} failed:\n{traceback.format_exc()}")

        # Save logs to task
        await self.progress_tracker.save_logs(task)
        await self.session.commit()
        return progress

    async def _handle_cancellation(self, task: CollectTask, progress: CollectionProgress):
        """处理任务取消

        Args:
            task: 采集任务
            progress: 进度对象
        """
        await self.progress_tracker.update_task_status(task, "cancelled")
        progress.status = "cancelled"
        self.progress_tracker.add_log("info", "任务被用户取消")
        await self.progress_tracker.save_logs(task)
        await self.session.commit()

    async def _estimate_total_works(self, task: CollectTask) -> int:
        """预估任务的总论文数

        在采集开始前调用 OpenAlex API 获取每个 Venue 的预计论文数。
        这允许：
        1. 在任务列表显示预计规模
        2. 计算准确的进度百分比
        3. 帮助用户评估任务规模

        API 开销：N 次 API 调用（N = Venue 数量），每次约 1KB 响应

        Returns:
            预估论文总数，如果所有预估都失败返回 -1
        """
        sub_tasks = await self.sub_task_repo.get_by_task(task.task_id)
        total = 0
        failed_count = 0

        # Get time window from task
        year_from = task.time_window_start.year if task.time_window_start else None
        year_to = task.time_window_end.year if task.time_window_end else None

        for sub_task in sub_tasks:
            venue = await self.venue_repo.get_by_id(sub_task.venue_id)
            if venue and self.work_fetcher:
                try:
                    count = await self.work_fetcher.get_work_count_from_venue(
                        venue, year_from=year_from, year_to=year_to
                    )
                    # 存储到子任务的 estimated_works 字段
                    if hasattr(sub_task, 'estimated_works'):
                        sub_task.estimated_works = count
                    total += count
                    self.progress_tracker.add_log("info", f"{venue.venue_name}: 预估 {count} 篇论文")
                except Exception as e:
                    failed_count += 1
                    self.progress_tracker.add_log("warning", f"{venue.venue_name if venue else sub_task.venue_id}: 预估失败 - {str(e)}")

        await self.session.flush()

        # 如果所有预估都失败，返回 -1 标记预估失败
        if failed_count == len(sub_tasks) and len(sub_tasks) > 0:
            self.progress_tracker.add_log(
                "warning",
                "所有 Venue 预估失败，进度显示将基于 Venue 数量而非论文数量"
            )
            return -1

        return total

    async def _execute_venue_sub_tasks(self, task: CollectTask, progress: CollectionProgress):
        """Phase 1: Execute all venue sub-tasks"""
        progress.current_step = "Fetching works from venues"
        self.progress_tracker.add_log("info", f"开始执行 Venue 采集，共 {progress.total_venues} 个子任务")

        sub_tasks = await self.sub_task_repo.get_by_task(task.task_id)
        progress.total_venues = len(sub_tasks)

        estimated_total = progress.estimated_works
        for sub_task in sub_tasks:
            try:
                venue_name = await self.venue_executor.get_venue_name(sub_task.venue_id)

                works_fetched = await self.venue_executor.execute(task, sub_task, progress)
                progress.completed_venues += 1
                progress.total_works += works_fetched

                # 基于预估总数计算进度（采集阶段占 5%-20%）
                if estimated_total > 0:
                    work_progress = int((progress.total_works / estimated_total) * 15) + 5
                    work_progress = min(work_progress, 19)  # 上限 19%，给后续阶段留空间
                    step_msg = f"采集论文 ({progress.total_works}/{estimated_total})"
                else:
                    # 回退到基于 venue 数量计算
                    work_progress = int((progress.completed_venues / len(sub_tasks)) * 15) + 5
                    step_msg = f"采集论文 ({progress.completed_venues}/{len(sub_tasks)} venues)"

                await self.progress_tracker.update_progress(task, step_msg, work_progress)

                # Commit after each venue sub-task to release database lock
                # This is critical for SQLite to allow concurrent access during long collection
                await self.session.commit()

                # Log venue completion at debug level to reduce verbosity
                logger.debug(f"完成采集: {venue_name} ({works_fetched} works)")
            except Exception as e:
                venue_name = await self.venue_executor.get_venue_name(sub_task.venue_id)
                error_msg = f"Venue {sub_task.venue_id}: {str(e)}"
                progress.errors.append(error_msg)
                self.progress_tracker.add_log("error", f"采集失败: {venue_name}", {"error": str(e)})
                await self.sub_task_repo.update_status(sub_task.sub_task_id, "failed", error_message=str(e))
                # Also commit on error to release lock
                await self.session.commit()

    async def _fetch_all_authors(self, task_id: int, progress: CollectionProgress):
        """Phase 2: Fetch all unique authors from collected works"""
        progress.current_step = "Fetching authors"

        if not self.author_fetcher:
            self.progress_tracker.add_log("warning", "Author fetcher not configured")
            return

        # Get all unique author IDs from raw works for this task
        all_author_ids = await self.raw_work_repo.get_author_ids_by_task(task_id)

        if not all_author_ids:
            return

        # Count total unique authors found
        progress.total_authors = len(all_author_ids)

        # Find which authors are already collected
        missing_ids = await self.raw_author_repo.get_missing_author_ids(list(all_author_ids))

        # Fetch missing authors
        if missing_ids:
            author_progress = await self.author_fetcher.fetch_authors_by_ids(
                author_ids=missing_ids,
                task_id=task_id
            )
            self.progress_tracker.add_log("info", f"获取作者: {author_progress.fetched}/{len(all_author_ids)}")
        else:
            logger.debug(f"All {len(all_author_ids)} authors already in database")

    async def _fetch_all_institutions(self, task_id: int, progress: CollectionProgress):
        """Phase 3: Fetch all unique institutions from collected authors"""
        progress.current_step = "Fetching institutions"

        if not self.institution_fetcher:
            self.progress_tracker.add_log("warning", "Institution fetcher not configured")
            return

        # Get all unique institution IDs from raw authors
        result = await self.session.execute(
            select(RawAuthor.last_known_institution_id).where(
                RawAuthor.last_known_institution_id.isnot(None),
                RawAuthor.last_known_institution_id != ""
            ).distinct()
        )
        institution_ids = [row[0] for row in result.fetchall() if row[0]]

        if not institution_ids:
            return

        # Count total unique institutions
        progress.total_institutions = len(institution_ids)

        # Find which institutions are already collected
        missing_ids = await self.raw_inst_repo.get_missing_ids(institution_ids)

        # Fetch missing institutions
        if missing_ids:
            inst_progress = await self.institution_fetcher.fetch_institutions_by_ids(
                institution_ids=missing_ids,
                task_id=task_id
            )
            self.progress_tracker.add_log("info", f"获取机构: {inst_progress.fetched}/{len(institution_ids)}")
        else:
            logger.debug(f"All {len(institution_ids)} institutions already in database")

    async def _normalize_schools(self, task_id: int, progress: CollectionProgress):
        """Phase 4: Normalize collected institutions to StdSchool"""
        progress.current_step = "Normalizing schools"

        result = await self.school_normalizer.normalize_all_institutions(task_id=task_id)
        progress.normalized_schools = result.processed

        if result.processed > 0:
            self.progress_tracker.add_log("info", f"标准化学校: {result.processed}")

    async def _normalize_authors(self, task_id: int, progress: CollectionProgress):
        """Phase 5: Normalize collected authors"""
        progress.current_step = "Normalizing authors"

        result = await self.author_normalizer.normalize_all_authors(task_id=task_id)
        progress.normalized_authors = result.processed

        if result.processed > 0:
            self.progress_tracker.add_log("info", f"标准化作者: {result.processed}")

    async def _calculate_tech_belong(self, task_id: int, tech_element_id: int):
        """Phase 6: Calculate author-tech element relationships"""

        # Get all venues for this tech element
        sub_tasks = await self.sub_task_repo.get_by_task(task_id)

        for sub_task in sub_tasks:
            if sub_task.status == "completed":
                await self.tech_belong_calculator.calculate_for_venue(
                    venue_id=sub_task.venue_id,
                    tech_element_id=tech_element_id,
                    task_id=task_id
                )

    async def _sync_to_serving_layer(
        self,
        task_id: int,
        tech_element_id: int,
        progress: CollectionProgress
    ) -> List[dict]:
        """Phase 7: Sync to serving layer (calls external sync service)

        Returns:
            List[dict]: 新创建的学者列表，用于后续获取代表作品
        """
        from app.services.sync import ServingLayerOrchestrator

        progress.current_step = "Syncing to serving layer"

        sync = ServingLayerOrchestrator(self.session)

        # Get or create default tech direction
        default_direction_id = await self._get_or_create_default_tech_direction(tech_element_id)

        # Execute sync
        stats = await sync.sync_all_for_task(
            task_id=task_id,
            tech_element_id=tech_element_id,
            default_tech_direction_id=default_direction_id
        )

        # Update progress
        progress.synced_authors = stats.get("authors_synced", 0)
        progress.created_talents = stats.get("authors_created", 0)
        progress.updated_talents = stats.get("authors_updated", 0)
        progress.created_tech_tags = stats.get("tags_created", 0)

        # Record errors
        for error in stats.get("errors", []):
            progress.errors.append(error)

        # Log summary
        if progress.created_talents > 0 or progress.synced_authors > 0:
            self.progress_tracker.add_log("info", f"入库人才: {progress.created_talents}, 更新: {progress.updated_talents}")

        # 返回新创建的学者列表（用于获取代表作品）
        return stats.get("new_talents_for_works", [])

    async def _fetch_selected_works(
        self,
        new_talents: List[NewTalentInfo],
        progress: CollectionProgress
    ):
        """Phase 8: Fetch selected works for newly created talents

        只为新入库的教授获取代表作品，按引用数排序取前 10 篇。
        使用 asyncio.Semaphore 控制并发数，避免 API 限速。

        Args:
            new_talents: 新创建的学者列表
            progress: 进度对象
        """
        from app.services.common.openalex_utils import REQUEST_DELAY

        if not new_talents:
            self.progress_tracker.add_log("info", "无需获取代表作品（无新增教授）")
            return

        progress.current_step = "Fetching selected works"
        self.progress_tracker.add_log("info", f"开始为 {len(new_talents)} 位新入库教授获取代表作品")

        # 使用 Semaphore 控制并发数（最多 3 个并发请求）
        semaphore = asyncio.Semaphore(3)
        total_fetched = 0
        total_inserted = 0
        errors = []

        async def fetch_for_talent(talent_info: dict):
            nonlocal total_fetched, total_inserted
            async with semaphore:
                try:
                    talent_id = talent_info["talent_id"]
                    openalex_author_id = talent_info["openalex_author_id"]
                    works_count = talent_info.get("works_count", 0)

                    # 只为论文数 > 5 的学者获取代表作品
                    if works_count <= 5:
                        return

                    # 获取代表作品（按引用数排序，最多 10 篇）
                    works = await self.work_fetcher.fetch_author_top_works(
                        openalex_author_id=openalex_author_id,
                        max_works=10
                    )

                    if not works:
                        return

                    # 插入 core_selected_work 表
                    for order, work in enumerate(works):
                        if not work.get("title"):
                            continue

                        selected_work = SelectedWork(
                            talent_id=talent_id,
                            title=work.get("title", "")[:500],  # 截断超长标题
                            publication_year=work.get("publication_year"),
                            venue_name=work.get("venue_name"),
                            citation_count=work.get("citation_count", 0),
                            source_work_id=work.get("source_work_id"),
                            doi=work.get("doi"),
                            display_order=order
                        )
                        self.session.add(selected_work)
                        total_inserted += 1

                    total_fetched += 1

                    # 限速延迟
                    await asyncio.sleep(REQUEST_DELAY)

                except Exception as e:
                    errors.append(f"talent_id={talent_info.get('talent_id')}: {str(e)}")

        # 并发执行所有请求
        await asyncio.gather(*[fetch_for_talent(t) for t in new_talents])

        await self.session.flush()

        # 记录错误
        for error in errors:
            self.progress_tracker.add_log("warning", f"获取代表作品失败: {error}")

        self.progress_tracker.add_log("info", f"代表作品获取完成: {total_fetched} 位教授，{total_inserted} 篇作品")

    async def _update_talent_topic_tags(self, task_id: int, progress: CollectionProgress):
        """Phase 9: Update talent topic_tags from tech tags

        只更新与当前任务相关的人才（通过 tech_tag 关联），避免全表查询。
        """
        from app.models.talent import Talent
        from app.models.tech_element import TalentTechTag
        from sqlalchemy.orm import selectinload

        progress.current_step = "Updating topic tags"
        self.progress_tracker.add_log("info", "开始更新人才技术标签")

        # 获取当前任务关联的 tech_element_id
        task_result = await self.session.execute(
            select(CollectTask).where(CollectTask.task_id == task_id)
        )
        task = task_result.scalar_one_or_none()
        if not task:
            self.progress_tracker.add_log("warning", f"任务 {task_id} 不存在")
            return

        tech_element_id = task.tech_element_id

        # 只查询与当前 tech_element 相关的人才，避免全表扫描
        result = await self.session.execute(
            select(Talent).options(
                selectinload(Talent.tech_tags).selectinload(TalentTechTag.tech_element)
            ).join(TalentTechTag, Talent.talent_id == TalentTechTag.talent_id)
            .where(TalentTechTag.tech_element_id == tech_element_id)
            .distinct()
        )
        talents = result.scalars().all()

        updated_count = 0
        for i, talent in enumerate(talents):
            if talent.tech_tags:
                # Get unique tech element names
                tech_names = list(set(
                    tag.tech_element.element_name
                    for tag in talent.tech_tags
                    if tag.tech_element and tag.is_enabled
                ))
                if tech_names:
                    talent.topic_tags = tech_names
                    updated_count += 1

                # Commit every 100 talents to release database lock
                if (i + 1) % 100 == 0:
                    await self.session.commit()

        await self.session.flush()
        self.progress_tracker.add_log("info", f"更新了 {updated_count} 个人才的技术标签")

    async def _update_school_statistics(self, task_id: int, progress: CollectionProgress):
        """Phase 9: Update school professor_count and student_count"""
        from app.models.school import School
        from app.models.talent import Talent
        from sqlalchemy import func

        progress.current_step = "Updating school statistics"
        self.progress_tracker.add_log("info", "开始更新学校统计")

        # Reset all school counts
        await self.session.execute(
            School.__table__.update().values(professor_count=0, student_count=0)
        )

        # Calculate and update counts
        result = await self.session.execute(
            select(
                Talent.school_id,
                func.count(case((Talent.role_type == 'professor', 1))).label('professor_count'),
                func.count(case((Talent.role_type.in_(['student', 'graduate']), 1))).label('student_count')
            ).where(
                Talent.school_id.isnot(None),
                Talent.is_visible == True
            ).group_by(Talent.school_id)
        )

        updated_schools = 0
        for i, row in enumerate(result):
            school_id, prof_count, stu_count = row
            if school_id:
                await self.session.execute(
                    School.__table__.update()
                    .where(School.school_id == school_id)
                    .values(professor_count=prof_count, student_count=stu_count)
                )
                updated_schools += 1

                # Commit every 50 schools to release database lock
                if (i + 1) % 50 == 0:
                    await self.session.commit()

        await self.session.flush()
        self.progress_tracker.add_log("info", f"更新了 {updated_schools} 所学校的统计")

    async def _build_statistics(self, task_id: int, progress: CollectionProgress):
        """Phase 8: Build statistics snapshots for homepage"""
        from app.builders.stat_builder import StatBuilder

        progress.current_step = "Building statistics"
        self.progress_tracker.add_log("info", "开始生成统计数据")

        try:
            builder = StatBuilder(self.session, batch_id=task_id, version=f"task-{task_id}")
            result = await builder.build()

            if result.success:
                self.progress_tracker.add_log("info", f"统计数据生成完成", {
                    "records_created": result.records_created
                })
            else:
                self.progress_tracker.add_log("warning", f"统计数据生成失败: {result.errors}")
        except Exception as e:
            self.progress_tracker.add_log("warning", f"统计数据生成异常: {str(e)}")

    async def _get_default_tech_direction(self, tech_element_id: int) -> Optional[int]:
        """获取默认技术方向ID（只获取，不创建）

        Args:
            tech_element_id: 技术要素ID

        Returns:
            默认技术方向ID，如果不存在返回 None
        """
        result = await self.session.execute(
            select(TechDirection.tech_direction_id).where(
                TechDirection.tech_element_id == tech_element_id,
                TechDirection.is_enabled == True
            ).order_by(TechDirection.sort_order).limit(1)
        )
        return result.scalar_one_or_none()

    async def _create_default_tech_direction(self, tech_element_id: int) -> Optional[int]:
        """创建默认技术方向

        Args:
            tech_element_id: 技术要素ID

        Returns:
            新创建的技术方向ID，如果技术要素不存在返回 None
        """
        te_result = await self.session.execute(
            select(TechElement).where(TechElement.tech_element_id == tech_element_id)
        )
        tech_element = te_result.scalar_one_or_none()

        if not tech_element:
            logger.warning(f"Tech element {tech_element_id} not found, cannot create default direction")
            return None

        new_direction = TechDirection(
            direction_code=f"{tech_element.element_code}-DEFAULT",
            direction_name=f"{tech_element.element_name}（默认）",
            tech_element_id=tech_element_id,
            sort_order=0,
            is_enabled=True
        )
        self.session.add(new_direction)
        await self.session.flush()

        logger.info(f"Created default tech direction for {tech_element.element_name}")
        return new_direction.tech_direction_id

    async def _get_or_create_default_tech_direction(self, tech_element_id: int) -> Optional[int]:
        """获取或创建默认技术方向ID

        先尝试获取已存在的默认方向，不存在则创建新的。

        Args:
            tech_element_id: 技术要素ID

        Returns:
            默认技术方向ID
        """
        # 先尝试获取
        direction_id = await self._get_default_tech_direction(tech_element_id)
        if direction_id:
            return direction_id

        # 不存在则创建
        return await self._create_default_tech_direction(tech_element_id)

    async def get_task_progress(self, task_id: int) -> Dict[str, Any]:
        """Get progress for a task"""
        task = await self.session.execute(
            select(CollectTask).where(CollectTask.task_id == task_id)
        )
        task = task.scalar_one_or_none()

        if not task:
            return {"error": "Task not found"}

        sub_tasks = await self.sub_task_repo.get_by_task(task_id)

        completed = sum(1 for st in sub_tasks if st.status == "completed")
        failed = sum(1 for st in sub_tasks if st.status == "failed")
        running = sum(1 for st in sub_tasks if st.status == "running")

        return {
            "task_id": task.task_id,
            "status": task.status,
            "collect_mode": task.collect_mode,
            "total_venues": len(sub_tasks),
            "completed_venues": completed,
            "running_venues": running,
            "failed_venues": failed,
            "progress_percent": int((completed / len(sub_tasks)) * 100) if sub_tasks else 0,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "error_message": task.error_message
        }
