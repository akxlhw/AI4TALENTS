"""Phase 1: Execute venue sub-tasks to collect works."""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domains.academic.repositories.venue_repository import VenueSubTaskRepository
from app.domains.academic.services.collect.phases.base import PhaseContext, PhaseHandler
from app.domains.academic.services.collect.progress_tracker import ProgressTracker
from app.domains.academic.services.collect.venue_executor import VenueSubTaskExecutor
from app.domains.academic.services.data_fetchers import WorkFetcher

logger = logging.getLogger(__name__)


class PhaseCollectHandler(PhaseHandler):
    """Phase 1: Fetch works from venues via sub-tasks."""

    phase_code = "phase_1_collect"
    phase_name = "采集论文数据"
    phase_progress = 20
    is_critical = True

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
        max_retries = settings.COLLECT_SUBTASK_RETRY_COUNT

        for sub_task in sub_tasks:
            # Skip already-completed sub-tasks on rerun (saves API quota)
            if sub_task.status == "completed":
                continue

            venue_name = None
            works_fetched = 0
            last_error = None

            for attempt in range(max_retries):
                try:
                    if venue_name is None:
                        venue_name = await self.venue_executor.get_venue_name(sub_task.venue_id)

                    works_fetched = await self.venue_executor.execute(task, sub_task, progress)
                    last_error = None
                    break  # Success — exit retry loop
                except Exception as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        wait_seconds = settings.COLLECT_SUBTASK_RETRY_BASE_WAIT * (2**attempt)
                        self.progress_tracker.add_log(
                            "warning",
                            f"Venue {sub_task.venue_id} 第 {attempt + 1} 次采集失败，"
                            f"{wait_seconds}秒后重试",
                            {"error": str(e)},
                        )
                        logger.warning(
                            f"Sub-task {sub_task.sub_task_id} (venue {sub_task.venue_id}) "
                            f"attempt {attempt + 1} failed, retrying in {wait_seconds}s: {e}"
                        )
                        await asyncio.sleep(wait_seconds)
                    else:
                        # Final attempt failed
                        if venue_name is None:
                            venue_name = await self.venue_executor.get_venue_name(sub_task.venue_id)
                        error_msg = f"Venue {sub_task.venue_id}: {str(e)}"
                        progress.errors.append(error_msg)
                        self.progress_tracker.add_log(
                            "error", f"采集失败: {venue_name}", {"error": str(e)}
                        )
                        await self.sub_task_repo.update_status(
                            sub_task.sub_task_id, "failed", error_message=str(e)
                        )

            if last_error is None:
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
                    step_msg = f"采集论文 ({progress.completed_venues}/{len(sub_tasks)} venues)"

                await self.progress_tracker.update_progress(task, step_msg, work_progress)
                logger.debug(f"完成采集: {venue_name} ({works_fetched} works)")
