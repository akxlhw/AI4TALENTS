"""Phase 1: Execute venue sub-tasks to collect works."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.academic.repositories.venue_repository import VenueSubTaskRepository
from app.domains.academic.services.collect.phases.base import PhaseContext, PhaseHandler
from app.domains.academic.services.collect.progress_tracker import ProgressTracker
from app.domains.academic.services.collect.venue_executor import VenueSubTaskExecutor
from app.domains.academic.services.data_fetchers import WorkFetcher

logger = logging.getLogger(__name__)


class PhaseCollectHandler(PhaseHandler):
    """Phase 1: Fetch works from venues via sub-tasks."""

    phase_name = "采集论文数据"
    phase_progress = 20

    def __init__(
        self,
        session: AsyncSession,
        progress_tracker: ProgressTracker,
        work_fetcher: WorkFetcher | None = None,
    ) -> None:
        super().__init__(session, progress_tracker)
        self.sub_task_repo = VenueSubTaskRepository(session)
        self.venue_executor = VenueSubTaskExecutor(session, work_fetcher)

    async def execute(self, context: PhaseContext) -> None:
        task = context.task
        progress = context.progress

        progress.current_step = "Fetching works from venues"
        self.progress_tracker.add_log(
            "info", f"开始执行 Venue 采集，共 {progress.total_venues} 个子任务"
        )

        sub_tasks = await self.sub_task_repo.get_by_task(task.task_id)
        progress.total_venues = len(sub_tasks)

        estimated_total = context.estimated_total
        for sub_task in sub_tasks:
            try:
                venue_name = await self.venue_executor.get_venue_name(sub_task.venue_id)

                works_fetched = await self.venue_executor.execute(task, sub_task, progress)
                progress.completed_venues += 1
                progress.total_works += works_fetched

                # Calculate progress based on estimated total (Phase 1 range: 5%-20%)
                if estimated_total > 0:
                    work_progress = int((progress.total_works / estimated_total) * 15) + 5
                    work_progress = min(work_progress, 19)  # Cap at 19%
                    step_msg = f"采集论文 ({progress.total_works}/{estimated_total})"
                else:
                    # Fallback: progress based on venue count
                    work_progress = int((progress.completed_venues / len(sub_tasks)) * 15) + 5
                    step_msg = (
                        f"采集论文 ({progress.completed_venues}/{len(sub_tasks)} venues)"
                    )

                await self.progress_tracker.update_progress(task, step_msg, work_progress)

                # Commit after each venue sub-task to save progress
                await self.session.commit()
                logger.debug(f"完成采集: {venue_name} ({works_fetched} works)")
            except Exception as e:
                venue_name = await self.venue_executor.get_venue_name(sub_task.venue_id)
                error_msg = f"Venue {sub_task.venue_id}: {str(e)}"
                progress.errors.append(error_msg)
                self.progress_tracker.add_log(
                    "error", f"采集失败: {venue_name}", {"error": str(e)}
                )
                await self.sub_task_repo.update_status(
                    sub_task.sub_task_id, "failed", error_message=str(e)
                )
                await self.session.commit()
