"""
Collection orchestrator for managing the complete collection pipeline.
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

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

    async def execute_task(self, task_id: int) -> CollectionProgress:
        """Execute a collection task through all layers"""
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
            await self.progress_tracker.update_progress(task, "预估任务规模", 2)
            estimated_total = await self._estimate_total_works(task)
            progress.estimated_works = estimated_total
            if estimated_total > 0:
                self.progress_tracker.add_log("info", f"预估论文总数: {estimated_total}")
                task.total_records = estimated_total  # 预存预计数
            await self.session.flush()

            # Phase 1: Execute venue sub-tasks
            await self.progress_tracker.update_progress(task, "采集论文数据", 5)
            await self._execute_venue_sub_tasks(task, progress)

            # Phase 2: Fetch authors from collected author IDs
            await self.progress_tracker.update_progress(task, "获取作者数据", 20)
            await self._fetch_all_authors(task_id, progress)

            # Phase 3: Fetch institutions from collected institution IDs
            await self.progress_tracker.update_progress(task, "获取机构数据", 30)
            await self._fetch_all_institutions(task_id, progress)

            # Phase 4: Normalize schools
            await self.progress_tracker.update_progress(task, "标准化学校", 40)
            await self._normalize_schools(task_id, progress)

            # Phase 5: Normalize authors
            await self.progress_tracker.update_progress(task, "标准化作者", 50)
            await self._normalize_authors(task_id, progress)

            # Phase 6: Calculate tech belong relationships
            await self.progress_tracker.update_progress(task, "计算技术归属", 60)
            await self._calculate_tech_belong(task_id, task.tech_element_id)

            # Phase 7: Sync to serving layer (delegated to sync service)
            await self.progress_tracker.update_progress(task, "同步到服务层", 70)
            new_talents = await self._sync_to_serving_layer(task_id, task.tech_element_id, progress)

            # Phase 8: Fetch selected works for NEW talents
            await self.progress_tracker.update_progress(task, "获取代表作品", 75)
            await self._fetch_selected_works(new_talents, progress)

            # Phase 9: Update talent topic_tags from tech tags
            await self.progress_tracker.update_progress(task, "更新技术标签", 80)
            await self._update_talent_topic_tags(task_id, progress)

            # Phase 10: Update school statistics
            await self.progress_tracker.update_progress(task, "更新学校统计", 90)
            await self._update_school_statistics(task_id, progress)

            # Phase 11: Build statistics for homepage
            await self.progress_tracker.update_progress(task, "构建统计数据", 95)
            await self._build_statistics(task_id, progress)

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

        except Exception as e:
            await self.progress_tracker.update_task_status(task, "failed", str(e))
            progress.status = "failed"
            progress.errors.append(str(e))
            self.progress_tracker.add_log("error", f"任务执行失败: {str(e)}")

        # Save logs to task
        await self.progress_tracker.save_logs(task)
        await self.session.commit()
        return progress

    async def _estimate_total_works(self, task: CollectTask) -> int:
        """预估任务的总论文数

        在采集开始前调用 OpenAlex API 获取每个 Venue 的预计论文数。
        这允许：
        1. 在任务列表显示预计规模
        2. 计算准确的进度百分比
        3. 帮助用户评估任务规模

        API 开销：N 次 API 调用（N = Venue 数量），每次约 1KB 响应
        """
        sub_tasks = await self.sub_task_repo.get_by_task(task.task_id)
        total = 0

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
                    self.progress_tracker.add_log("warning", f"{venue.venue_name if venue else sub_task.venue_id}: 预估失败 - {str(e)}")

        await self.session.flush()
        return total

    async def _execute_venue_sub_tasks(self, task: CollectTask, progress: CollectionProgress):
        """Phase 1: Execute all venue sub-tasks"""
        progress.current_step = "Fetching works from venues"
        self.progress_tracker.add_log("info", "开始执行Venue采集子任务")

        sub_tasks = await self.sub_task_repo.get_by_task(task.task_id)
        progress.total_venues = len(sub_tasks)
        self.progress_tracker.add_log("info", f"加载 {len(sub_tasks)} 个采集子任务")

        estimated_total = progress.estimated_works
        for sub_task in sub_tasks:
            try:
                venue_name = await self.venue_executor.get_venue_name(sub_task.venue_id)
                self.progress_tracker.add_log("info", f"开始采集: {venue_name}")

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
                self.progress_tracker.add_log("info", f"完成采集: {venue_name}", {"works": works_fetched})
            except Exception as e:
                venue_name = await self.venue_executor.get_venue_name(sub_task.venue_id)
                error_msg = f"Venue {sub_task.venue_id}: {str(e)}"
                progress.errors.append(error_msg)
                self.progress_tracker.add_log("error", f"采集失败: {venue_name}", {"error": str(e)})
                await self.sub_task_repo.update_status(sub_task.sub_task_id, "failed", error_message=str(e))

    async def _fetch_all_authors(self, task_id: int, progress: CollectionProgress):
        """Phase 2: Fetch all unique authors from collected works"""
        progress.current_step = "Fetching authors"
        self.progress_tracker.add_log("info", "开始获取作者数据")

        if not self.author_fetcher:
            self.progress_tracker.add_log("warning", "Author fetcher not configured")
            return

        # Get all unique author IDs from raw works using repository
        all_author_ids = await self.raw_work_repo.get_author_ids_by_task(task_id)

        # Also get from all raw_works if task-specific query returns nothing
        if not all_author_ids:
            all_author_ids = await self.raw_work_repo.get_all_author_ids(limit=10000)

        if not all_author_ids:
            self.progress_tracker.add_log("info", "未找到作者ID")
            return

        # Count total unique authors found
        progress.total_authors = len(all_author_ids)
        self.progress_tracker.add_log("info", f"从论文中提取 {len(all_author_ids)} 位唯一作者")

        # Find which authors are already collected
        missing_ids = await self.raw_author_repo.get_missing_author_ids(list(all_author_ids))

        # Fetch missing authors
        if missing_ids:
            self.progress_tracker.add_log("info", f"需要获取 {len(missing_ids)} 位新作者")
            author_progress = await self.author_fetcher.fetch_authors_by_ids(
                author_ids=missing_ids,
                task_id=task_id
            )
            self.progress_tracker.add_log("info", f"实际获取 {author_progress.fetched} 位作者")
        else:
            self.progress_tracker.add_log("info", "所有作者已存在于数据库中")

    async def _fetch_all_institutions(self, task_id: int, progress: CollectionProgress):
        """Phase 3: Fetch all unique institutions from collected authors"""
        progress.current_step = "Fetching institutions"
        self.progress_tracker.add_log("info", "开始获取机构数据")

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
            self.progress_tracker.add_log("info", "未找到机构ID")
            return

        # Count total unique institutions
        progress.total_institutions = len(institution_ids)
        self.progress_tracker.add_log("info", f"从作者中提取 {len(institution_ids)} 个唯一机构")

        # Find which institutions are already collected
        missing_ids = await self.raw_inst_repo.get_missing_ids(institution_ids)

        # Fetch missing institutions
        if missing_ids:
            self.progress_tracker.add_log("info", f"需要获取 {len(missing_ids)} 个新机构")
            inst_progress = await self.institution_fetcher.fetch_institutions_by_ids(
                institution_ids=missing_ids,
                task_id=task_id
            )
            self.progress_tracker.add_log("info", f"实际获取 {inst_progress.fetched} 个机构")
        else:
            self.progress_tracker.add_log("info", "所有机构已存在于数据库中")

    async def _normalize_schools(self, task_id: int, progress: CollectionProgress):
        """Phase 4: Normalize collected institutions to StdSchool"""
        progress.current_step = "Normalizing schools"
        self.progress_tracker.add_log("info", "开始标准化学校数据")

        result = await self.school_normalizer.normalize_all_institutions(task_id=task_id, limit=10000)
        progress.normalized_schools = result.processed

        self.progress_tracker.add_log("info", f"学校标准化完成: {progress.normalized_schools} 所学校")

    async def _normalize_authors(self, task_id: int, progress: CollectionProgress):
        """Phase 5: Normalize collected authors"""
        progress.current_step = "Normalizing authors"
        self.progress_tracker.add_log("info", "开始标准化作者数据")

        result = await self.author_normalizer.normalize_all_authors(task_id=task_id, limit=10000)
        progress.normalized_authors = result.processed

        self.progress_tracker.add_log("info", f"作者标准化完成: {progress.normalized_authors} 位作者")

    async def _calculate_tech_belong(self, task_id: int, tech_element_id: int):
        """Phase 6: Calculate author-tech element relationships"""
        self.progress_tracker.add_log("info", "开始计算技术归属关系")

        # Get all venues for this tech element
        sub_tasks = await self.sub_task_repo.get_by_task(task_id)

        for sub_task in sub_tasks:
            if sub_task.status == "completed":
                await self.tech_belong_calculator.calculate_for_venue(
                    venue_id=sub_task.venue_id,
                    tech_element_id=tech_element_id,
                    task_id=task_id
                )

        self.progress_tracker.add_log("info", "技术归属计算完成")

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
        self.progress_tracker.add_log("info", "开始同步到服务层")

        sync = ServingLayerOrchestrator(self.session)

        # Get default tech direction
        default_direction_id = await self._get_default_tech_direction(tech_element_id)

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

        self.progress_tracker.add_log("info", f"服务层同步完成", {
            "synced_authors": progress.synced_authors,
            "created_talents": progress.created_talents,
            "created_tech_tags": progress.created_tech_tags
        })

        # 返回新创建的学者列表（用于获取代表作品）
        return stats.get("new_talents_for_works", [])

    async def _fetch_selected_works(
        self,
        new_talents: List[dict],
        progress: CollectionProgress
    ):
        """Phase 8: Fetch selected works for newly created talents

        只为新入库的教授获取代表作品，按引用数排序取前 10 篇。

        Args:
            new_talents: 新创建的学者列表，每项包含 talent_id, openalex_author_id, works_count
            progress: 进度对象
        """
        from app.services.common.openalex_utils import REQUEST_DELAY

        if not new_talents:
            self.progress_tracker.add_log("info", "无需获取代表作品（无新增教授）")
            return

        progress.current_step = "Fetching selected works"
        self.progress_tracker.add_log("info", f"开始为 {len(new_talents)} 位新入库教授获取代表作品")

        total_fetched = 0
        total_inserted = 0

        for i, talent_info in enumerate(new_talents):
            try:
                talent_id = talent_info["talent_id"]
                openalex_author_id = talent_info["openalex_author_id"]
                works_count = talent_info.get("works_count", 0)

                # 只为论文数 > 5 的学者获取代表作品
                if works_count <= 5:
                    self.progress_tracker.add_log("debug", f"跳过 talent_id={talent_id}（论文数 {works_count} <= 5）")
                    continue

                # 获取代表作品（按引用数排序，最多 10 篇）
                works = await self.work_fetcher.fetch_author_top_works(
                    openalex_author_id=openalex_author_id,
                    max_works=10
                )

                if not works:
                    self.progress_tracker.add_log("debug", f"talent_id={talent_id} 无代表作品")
                    continue

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

                # 每 10 个请求暂停 1 秒（API 限速）
                if (i + 1) % 10 == 0:
                    await asyncio.sleep(1)

            except Exception as e:
                self.progress_tracker.add_log("warning", f"获取代表作品失败: talent_id={talent_info.get('talent_id')}, error={str(e)}")

        await self.session.flush()
        self.progress_tracker.add_log("info", f"代表作品获取完成: {total_fetched} 位教授，{total_inserted} 篇作品")

    async def _update_talent_topic_tags(self, task_id: int, progress: CollectionProgress):
        """Phase 8: Update talent topic_tags from tech tags"""
        from app.models.talent import Talent
        from app.models.tech_element import TalentTechTag, TechElement
        from sqlalchemy.orm import selectinload

        progress.current_step = "Updating topic tags"
        self.progress_tracker.add_log("info", "开始更新人才技术标签")

        # Get all talents with their tech tags and tech elements (eager load to avoid lazy loading issues)
        result = await self.session.execute(
            select(Talent).options(
                selectinload(Talent.tech_tags).selectinload(TalentTechTag.tech_element)
            )
        )
        talents = result.scalars().all()

        updated_count = 0
        for talent in talents:
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
        for row in result:
            school_id, prof_count, stu_count = row
            if school_id:
                await self.session.execute(
                    School.__table__.update()
                    .where(School.school_id == school_id)
                    .values(professor_count=prof_count, student_count=stu_count)
                )
                updated_schools += 1

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
        """Get or create default tech direction ID for a tech element"""
        result = await self.session.execute(
            select(TechDirection).where(
                TechDirection.tech_element_id == tech_element_id,
                TechDirection.is_enabled == True
            ).order_by(TechDirection.sort_order).limit(1)
        )
        direction = result.scalar_one_or_none()

        if direction:
            return direction.tech_direction_id

        # No tech direction exists, create a default one
        # Get tech element for the name
        te_result = await self.session.execute(
            select(TechElement).where(TechElement.tech_element_id == tech_element_id)
        )
        tech_element = te_result.scalar_one_or_none()

        if not tech_element:
            logger.warning(f"Tech element {tech_element_id} not found, cannot create default direction")
            return None

        # Create default direction
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
