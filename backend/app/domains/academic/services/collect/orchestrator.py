"""Collection orchestrator for managing the complete collection pipeline.

The orchestrator is intentionally thin: it coordinates 11 phase handlers
and handles cross-cutting concerns (status checks, cancellation, logging).
Each phase's business logic lives in its own handler under ``phases/``.
"""

from __future__ import annotations

import asyncio
import logging
import traceback
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metrics import (
    COLLECTION_ERRORS_TOTAL,
    COLLECTION_TASKS_ACTIVE,
    COLLECTION_TASKS_TOTAL,
)
from app.domains.academic.models.sync import CollectTask
from app.domains.academic.repositories.venue_repository import (
    VenueRepository,
    VenueSubTaskRepository,
)
from app.domains.academic.services.collect.phases import (
    PhaseBuildStatsHandler,
    PhaseCollectHandler,
    PhaseContext,
    PhaseFetchAuthorsHandler,
    PhaseFetchInstitutionsHandler,
    PhaseFetchWorksHandler,
    PhaseNormalizeAuthorsHandler,
    PhaseNormalizeSchoolsHandler,
    PhaseSchoolStatsHandler,
    PhaseSyncServingHandler,
    PhaseTechBelongHandler,
    PhaseTopicTagsHandler,
)
from app.domains.academic.services.collect.progress_tracker import ProgressTracker
from app.domains.academic.services.collect.venue_executor import VenueSubTaskExecutor
from app.domains.academic.services.data_fetchers import (
    AuthorFetcher,
    InstitutionFetcher,
    WorkFetcher,
)

logger = logging.getLogger(__name__)


class PhaseProgress:
    """Progress percentage constants for each pipeline stage."""

    TASK_START = 0
    ESTIMATE = 2
    COLLECT_START = 5
    COLLECT_END = 20
    FETCH_AUTHORS = 20
    FETCH_INSTITUTIONS = 30
    NORMALIZE_SCHOOLS = 40
    NORMALIZE_AUTHORS = 50
    CALCULATE_TECH_BELONG = 60
    SYNC_SERVING_LAYER = 70
    FETCH_SELECTED_WORKS = 75
    UPDATE_TOPIC_TAGS = 80
    UPDATE_SCHOOL_STATS = 90
    BUILD_STATISTICS = 95
    COMPLETED = 100


class CollectionOrchestrator:
    """Orchestrates the collection pipeline through 11 phase handlers."""

    def __init__(
        self,
        session: AsyncSession,
        work_fetcher: WorkFetcher | None = None,
        author_fetcher: AuthorFetcher | None = None,
        institution_fetcher: InstitutionFetcher | None = None,
        email: str | None = None,
    ) -> None:
        self.session = session

        # Repositories (still needed for Phase 0 estimation & helpers)
        self.venue_repo = VenueRepository(session)
        self.sub_task_repo = VenueSubTaskRepository(session)

        # Fetchers
        self.work_fetcher = work_fetcher or WorkFetcher(session)
        self.author_fetcher = author_fetcher or AuthorFetcher(session)
        self.institution_fetcher = institution_fetcher or InstitutionFetcher(session)

        # Progress tracking
        self.progress_tracker = ProgressTracker(session)

        # Venue executor (Phase 0 estimation uses it for venue names)
        self.venue_executor = VenueSubTaskExecutor(session, self.work_fetcher)

        # Phase handlers — each encapsulates a single pipeline stage
        self._handlers: list = [
            PhaseCollectHandler(session, self.progress_tracker, self.work_fetcher),
            PhaseFetchAuthorsHandler(session, self.progress_tracker, self.author_fetcher),
            PhaseFetchInstitutionsHandler(session, self.progress_tracker, self.institution_fetcher),
            PhaseNormalizeSchoolsHandler(session, self.progress_tracker),
            PhaseNormalizeAuthorsHandler(session, self.progress_tracker),
            PhaseTechBelongHandler(session, self.progress_tracker),
            PhaseSyncServingHandler(session, self.progress_tracker),
            PhaseFetchWorksHandler(session, self.progress_tracker, self.work_fetcher),
            PhaseSchoolStatsHandler(session, self.progress_tracker),
            PhaseBuildStatsHandler(session, self.progress_tracker),
        ]

    async def _check_task_status(self, task_id: int) -> str:
        result = await self.session.execute(
            select(CollectTask.status).where(CollectTask.task_id == task_id)
        )
        return result.scalar_one_or_none() or "unknown"

    async def _should_cancel(self, task_id: int) -> bool:
        status = await self._check_task_status(task_id)
        return status in ("cancelled", "cancelling")

    async def _handle_cancellation(self, task: CollectTask, progress) -> None:
        await self.progress_tracker.update_task_status(task, "cancelled")
        progress.status = "cancelled"
        self.progress_tracker.add_log("info", "任务被用户取消")
        await self.progress_tracker.save_logs(task)
        await self.session.commit()

    async def execute_task(self, task_id: int):
        """Execute a collection task through all phases."""

        progress = self.progress_tracker.create_progress(task_id)
        self.progress_tracker.reset_logs()

        task = await self.session.execute(select(CollectTask).where(CollectTask.task_id == task_id))
        task = task.scalar_one_or_none()
        if not task:
            progress.status = "failed"
            progress.errors.append("Task not found")
            return progress

        await self.progress_tracker.update_task_status(task, "running")
        self.progress_tracker.add_log("info", "任务开始执行")
        await self.session.flush()

        # Metrics: task started
        COLLECTION_TASKS_TOTAL.inc()
        COLLECTION_TASKS_ACTIVE.inc()

        try:
            # Phase 0: Estimate (kept in orchestrator — lightweight pre-check)
            await self.progress_tracker.update_progress(
                task, "预估任务规模", PhaseProgress.ESTIMATE
            )
            estimated_total = await self._estimate_total_works(task)
            if estimated_total < 0:
                self.progress_tracker.add_log("warning", "预估失败，使用 Venue 数量计算进度")
            else:
                progress.estimated_works = estimated_total
                if estimated_total > 0:
                    self.progress_tracker.add_log("info", f"预估论文总数: {estimated_total}")
                    task.total_records = estimated_total
            await self.session.commit()

            if await self._should_cancel(task_id):
                await self._handle_cancellation(task, progress)
                return progress

            # Build shared context for phase handlers
            context = PhaseContext(task=task, progress=progress, estimated_total=estimated_total)

            # Determine resume point from checkpoint
            handler_index_map = {h.phase_code: i for i, h in enumerate(self._handlers)}
            last_completed_idx = handler_index_map.get(task.last_completed_phase or "", -1)

            # Phase 1-11: delegated to handlers
            for handler in self._handlers:
                current_idx = handler_index_map[handler.phase_code]
                if current_idx <= last_completed_idx:
                    self.progress_tracker.add_log(
                        "info", f"跳过 {handler.phase_name}，已在上次完成"
                    )
                    continue

                await self.progress_tracker.update_progress(
                    task, handler.phase_name, handler.phase_progress
                )
                try:
                    result = await handler.execute(context)
                except Exception as phase_err:
                    await self.session.rollback()
                    self.progress_tracker.add_log(
                        "error",
                        f"Phase '{handler.phase_name}' failed: {phase_err}",
                        {"traceback": traceback.format_exc()},
                    )
                    logger.error(f"Task {task_id} phase '{handler.phase_name}' failed: {phase_err}")
                    if handler.is_critical:
                        raise
                    else:
                        progress.errors.append(
                            f"Non-critical phase '{handler.phase_name}' failed: {phase_err}"
                        )
                        continue

                # Phase success: commit results and save checkpoint
                if isinstance(handler, PhaseCollectHandler):
                    task.total_records = progress.total_works

                await self.session.commit()
                await self._save_checkpoint(task, handler.phase_code)

                # Phase 7 returns new talents for Phase 8
                if isinstance(handler, PhaseSyncServingHandler) and result:
                    context.new_talents = result

                if await self._should_cancel(task_id):
                    await self._handle_cancellation(task, progress)
                    return progress

            # Post-phase: build result summary
            task.total_records = progress.total_works
            task.success_records = progress.synced_authors
            task.processed_records = progress.normalized_authors
            task.skipped_records = progress.normalized_schools

            venue_details = await self._build_venue_details(task.task_id)
            task.result_summary = {
                "total_works": progress.total_works,
                "total_authors": progress.total_authors,
                "normalized_authors": progress.normalized_authors,
                "normalized_schools": progress.normalized_schools,
                "synced_authors": progress.synced_authors,
                "created_talents": progress.created_talents,
                "updated_talents": progress.updated_talents,
                "created_tech_tags": progress.created_tech_tags,
                "venue_details": venue_details,
                "total_duration": self._calculate_duration(task.started_at, task.completed_at),
            }

            await self.progress_tracker.update_task_status(task, "completed")
            progress.status = "completed"
            self.progress_tracker.add_log("info", "任务执行完成")
            COLLECTION_TASKS_ACTIVE.dec()

        except asyncio.CancelledError:
            await self.progress_tracker.update_task_status(task, "cancelled")
            progress.status = "cancelled"
            self.progress_tracker.add_log("info", "任务被取消")
            COLLECTION_TASKS_ACTIVE.dec()

        except Exception as e:
            error_detail = {
                "error": str(e),
                "type": type(e).__name__,
                "traceback": traceback.format_exc(),
                "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            }
            await self.progress_tracker.update_task_status(task, "failed", str(e))
            progress.status = "failed"
            progress.errors.append(error_detail)
            self.progress_tracker.add_log("error", f"任务执行失败: {str(e)}", error_detail)
            logger.error(f"Task {task_id} failed:\n{traceback.format_exc()}")
            COLLECTION_TASKS_ACTIVE.dec()
            COLLECTION_ERRORS_TOTAL.inc()

        await self.progress_tracker.save_logs(task)
        await self.session.commit()
        return progress

    async def _estimate_total_works(self, task: CollectTask) -> int:
        """Phase 0: Estimate total works count before collection."""
        sub_tasks = await self.sub_task_repo.get_by_task(task.task_id)
        total = 0
        failed_count = 0

        year_from = task.time_window_start.year if task.time_window_start else None
        year_to = task.time_window_end.year if task.time_window_end else None

        venue_ids = [st.venue_id for st in sub_tasks]
        venues_map = await self.venue_repo.get_by_ids(venue_ids)

        for sub_task in sub_tasks:
            venue = venues_map.get(sub_task.venue_id)
            if venue and self.work_fetcher:
                try:
                    count = await self.work_fetcher.get_work_count_from_venue(
                        venue, year_from=year_from, year_to=year_to
                    )
                    if hasattr(sub_task, "estimated_works"):
                        sub_task.estimated_works = count
                    total += count
                    self.progress_tracker.add_log(
                        "info", f"{venue.venue_name}: 预估 {count} 篇论文"
                    )
                except Exception as e:
                    failed_count += 1
                    self.progress_tracker.add_log(
                        "warning",
                        f"{venue.venue_name if venue else sub_task.venue_id}: 预估失败 - {str(e)}",
                    )

        await self.session.flush()

        if failed_count == len(sub_tasks) and len(sub_tasks) > 0:
            self.progress_tracker.add_log(
                "warning", "所有 Venue 预估失败，进度显示将基于 Venue 数量而非论文数量"
            )
            return -1

        return total

    async def get_task_progress(self, task_id: int) -> dict:
        """Get progress summary for a task."""
        task = await self.session.execute(select(CollectTask).where(CollectTask.task_id == task_id))
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
            "error_message": task.error_message,
        }

    async def _build_venue_details(self, task_id: int) -> list[dict]:
        """Build venue detail list for result summary."""
        sub_tasks = await self.sub_task_repo.get_by_task(task_id)
        venue_ids = [st.venue_id for st in sub_tasks]
        venues_map = await self.venue_repo.get_by_ids(venue_ids)

        venue_details = []
        for sub_task in sub_tasks:
            venue = venues_map.get(sub_task.venue_id)
            if venue:
                duration = None
                if sub_task.started_at and sub_task.completed_at:
                    delta = sub_task.completed_at - sub_task.started_at
                    total_seconds = int(delta.total_seconds())
                    if total_seconds >= 60:
                        duration = f"{total_seconds // 60}分{total_seconds % 60}秒"
                    else:
                        duration = f"{total_seconds}秒"

                venue_details.append(
                    {
                        "venue_id": venue.venue_code or str(sub_task.venue_id),
                        "venue_name": venue.venue_name,
                        "status": sub_task.status or "unknown",
                        "fetched": sub_task.works_fetched or 0,
                        "saved": sub_task.new_authors or 0,
                        "duration": duration,
                        "error": sub_task.error_message,
                    }
                )
        return venue_details

    # ------------------------------------------------------------------
    # Backward-compatible shims (tests and external callers may reference
    # these private methods directly).  Each shim delegates to the
    # corresponding phase handler.
    # ------------------------------------------------------------------

    async def _execute_venue_sub_tasks(self, task: CollectTask, progress) -> None:
        """Shim: Phase 1 — delegates to :class:`PhaseCollectHandler`."""
        context = PhaseContext(task=task, progress=progress)
        handler = PhaseCollectHandler(self.session, self.progress_tracker, self.work_fetcher)
        await handler.execute(context)

    async def _fetch_all_authors(self, task_id: int, progress) -> None:
        """Shim: Phase 2 — delegates to :class:`PhaseFetchAuthorsHandler`."""
        from app.domains.academic.models.sync import CollectTask

        task = await self.session.execute(select(CollectTask).where(CollectTask.task_id == task_id))
        task = task.scalar_one_or_none()
        if not task:
            return
        context = PhaseContext(task=task, progress=progress)
        handler = PhaseFetchAuthorsHandler(self.session, self.progress_tracker, self.author_fetcher)
        await handler.execute(context)

    async def _fetch_all_institutions(self, task_id: int, progress) -> None:
        """Shim: Phase 3 — delegates to :class:`PhaseFetchInstitutionsHandler`."""
        from app.domains.academic.models.sync import CollectTask

        task = await self.session.execute(select(CollectTask).where(CollectTask.task_id == task_id))
        task = task.scalar_one_or_none()
        if not task:
            return
        context = PhaseContext(task=task, progress=progress)
        handler = PhaseFetchInstitutionsHandler(
            self.session, self.progress_tracker, self.institution_fetcher
        )
        await handler.execute(context)

    async def _normalize_schools(self, task_id: int, progress) -> None:
        """Shim: Phase 4 — delegates to :class:`PhaseNormalizeSchoolsHandler`."""
        from app.domains.academic.models.sync import CollectTask

        task = await self.session.execute(select(CollectTask).where(CollectTask.task_id == task_id))
        task = task.scalar_one_or_none()
        if not task:
            return
        context = PhaseContext(task=task, progress=progress)
        handler = PhaseNormalizeSchoolsHandler(self.session, self.progress_tracker)
        await handler.execute(context)

    async def _normalize_authors(self, task_id: int, progress) -> None:
        """Shim: Phase 5 — delegates to :class:`PhaseNormalizeAuthorsHandler`."""
        from app.domains.academic.models.sync import CollectTask

        task = await self.session.execute(select(CollectTask).where(CollectTask.task_id == task_id))
        task = task.scalar_one_or_none()
        if not task:
            return
        context = PhaseContext(task=task, progress=progress)
        handler = PhaseNormalizeAuthorsHandler(self.session, self.progress_tracker)
        await handler.execute(context)

    async def _calculate_tech_belong(self, task_id: int, tech_domain_id: int) -> None:
        """Shim: Phase 6 — delegates to :class:`PhaseTechBelongHandler`."""
        from app.domains.academic.models.sync import CollectTask

        task = await self.session.execute(select(CollectTask).where(CollectTask.task_id == task_id))
        task = task.scalar_one_or_none()
        if not task:
            return
        context = PhaseContext(task=task, progress=self.progress_tracker.create_progress(task_id))
        handler = PhaseTechBelongHandler(self.session, self.progress_tracker)
        await handler.execute(context)

    async def _sync_to_serving_layer(
        self, task_id: int, tech_domain_id: int, progress
    ) -> list[dict]:
        """Shim: Phase 7 — delegates to :class:`PhaseSyncServingHandler`."""
        from app.domains.academic.models.sync import CollectTask

        task = await self.session.execute(select(CollectTask).where(CollectTask.task_id == task_id))
        task = task.scalar_one_or_none()
        if not task:
            return []
        context = PhaseContext(task=task, progress=progress)
        handler = PhaseSyncServingHandler(self.session, self.progress_tracker)
        return await handler.execute(context)

    async def _fetch_selected_works(self, new_talents: list[dict], progress) -> None:
        """Shim: Phase 8 — delegates to :class:`PhaseFetchWorksHandler`."""
        context = PhaseContext(
            task=None,  # type: ignore[arg-type]
            progress=progress,
            new_talents=new_talents,
        )
        handler = PhaseFetchWorksHandler(self.session, self.progress_tracker, self.work_fetcher)
        await handler.execute(context)

    async def _update_talent_topic_tags(self, task_id: int, progress) -> None:
        """Shim: Phase 9 — delegates to :class:`PhaseTopicTagsHandler`."""
        from app.domains.academic.models.sync import CollectTask

        task = await self.session.execute(select(CollectTask).where(CollectTask.task_id == task_id))
        task = task.scalar_one_or_none()
        if not task:
            self.progress_tracker.add_log("warning", f"任务 {task_id} 不存在")
            return
        context = PhaseContext(task=task, progress=progress)
        handler = PhaseTopicTagsHandler(self.session, self.progress_tracker)
        await handler.execute(context)

    async def _update_school_statistics(self, task_id: int, progress) -> None:
        """Shim: Phase 10 — delegates to :class:`PhaseSchoolStatsHandler`."""
        from app.domains.academic.models.sync import CollectTask

        task = await self.session.execute(select(CollectTask).where(CollectTask.task_id == task_id))
        task = task.scalar_one_or_none()
        if not task:
            return
        context = PhaseContext(task=task, progress=progress)
        handler = PhaseSchoolStatsHandler(self.session, self.progress_tracker)
        await handler.execute(context)

    async def _build_statistics(self, task_id: int, progress) -> None:
        """Shim: Phase 11 — delegates to :class:`PhaseBuildStatsHandler`."""
        from app.domains.academic.models.sync import CollectTask

        task = await self.session.execute(select(CollectTask).where(CollectTask.task_id == task_id))
        task = task.scalar_one_or_none()
        if not task:
            return
        context = PhaseContext(task=task, progress=progress)
        handler = PhaseBuildStatsHandler(self.session, self.progress_tracker)
        await handler.execute(context)

    async def _save_checkpoint(self, task: CollectTask, phase_code: str) -> None:
        """Persist checkpoint so that a retried task can resume after this phase."""
        task.last_completed_phase = phase_code
        await self.session.flush()

    def _calculate_duration(self, started_at, completed_at) -> str | None:
        """Calculate human-readable task duration."""
        if not started_at or not completed_at:
            return None

        delta = completed_at - started_at
        total_seconds = int(delta.total_seconds())

        if total_seconds >= 3600:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            return f"{hours}时{minutes}分{seconds}秒"
        elif total_seconds >= 60:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}分{seconds}秒"
        return f"{total_seconds}秒"
