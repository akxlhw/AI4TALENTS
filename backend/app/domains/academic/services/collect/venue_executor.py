"""
Venue sub-task executor for collection tasks.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.academic.models.sync import CollectTask
from app.domains.academic.models.venue import VenueSubTask
from app.domains.academic.repositories.venue_repository import (
    VenueRepository,
    VenueSubTaskRepository,
    VenueTechBindingRepository,
)
from app.domains.academic.services.common.progress import CollectionProgress

logger = logging.getLogger(__name__)


class VenueSubTaskExecutor:
    """Executor for individual venue sub-tasks"""

    def __init__(self, session: AsyncSession, work_fetcher=None):
        self.session = session
        self.venue_repo = VenueRepository(session)
        self.sub_task_repo = VenueSubTaskRepository(session)
        self.binding_repo = VenueTechBindingRepository(session)
        self.work_fetcher = work_fetcher

    async def execute(
        self, task: CollectTask, sub_task: VenueSubTask, progress: CollectionProgress
    ) -> int:
        """Execute collection for a single venue

        Returns number of works fetched
        """
        # Get venue
        venue = await self.venue_repo.get_by_id(sub_task.venue_id)
        if not venue or not venue.openalex_source_id:
            await self.sub_task_repo.update_status(sub_task.sub_task_id, "skipped")
            return 0

        # Update sub-task status
        await self.sub_task_repo.update_status(sub_task.sub_task_id, "running")

        # Fetch works
        year_from = task.time_window_start.year if task.time_window_start else None
        year_to = task.time_window_end.year if task.time_window_end else None

        work_progress = await self.work_fetcher.fetch_works_from_venue(
            venue=venue,
            year_from=year_from,
            year_to=year_to,
            task_id=task.task_id,
            sub_task_id=sub_task.sub_task_id,
        )

        # Update sub-task with counts
        await self.sub_task_repo.update_status(
            sub_task.sub_task_id, "completed", works_fetched=work_progress.fetched
        )

        # Update binding status
        await self.binding_repo.update_collect_status(
            venue.venue_id, task.tech_domain_id, "completed"
        )

        # Update venue last_collect_at
        await self.venue_repo.update_last_collect_at(venue.venue_id, datetime.now(timezone.utc).replace(tzinfo=None))

        return work_progress.fetched

    async def get_venue_name(self, venue_id: int) -> str:
        """Get venue name for logging"""
        venue = await self.venue_repo.get_by_id(venue_id)
        return venue.venue_name if venue else f"Venue {venue_id}"
