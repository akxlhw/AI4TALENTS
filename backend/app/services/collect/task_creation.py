"""
Task creation service for collection tasks.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sync import CollectTask
from app.models.tech_element import TechElement
from app.models.venue import VenueSubTask
from app.repositories.venue_repository import VenueTechBindingRepository, VenueSubTaskRepository

logger = logging.getLogger(__name__)


class TaskCreationService:
    """Service for creating collection tasks"""

    # Time window defaults
    FULL_COLLECTION_START_YEAR = 2020
    INCREMENTAL_LOOKBACK_DAYS = 30

    def __init__(self, session: AsyncSession):
        self.session = session
        self.binding_repo = VenueTechBindingRepository(session)
        self.sub_task_repo = VenueSubTaskRepository(session)

    def get_time_window(
        self,
        mode: str,
        last_collect_at: Optional[datetime] = None
    ) -> tuple[datetime, datetime]:
        """Calculate time window for collection"""
        end_date = datetime.utcnow()

        if mode == "full" or not last_collect_at:
            start_date = datetime(self.FULL_COLLECTION_START_YEAR, 1, 1)
        else:
            # For incremental, look back 30 days from last collection
            lookback = timedelta(days=self.INCREMENTAL_LOOKBACK_DAYS)
            start_date = last_collect_at - lookback

        return start_date, end_date

    async def create_task(
        self,
        tech_element_id: int,
        mode: str = "full",
        triggered_by: Optional[int] = None
    ) -> CollectTask:
        """Create a new collection task"""
        # Generate task code
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        task_code = f"COL-{tech_element_id}-{timestamp}"

        # Get time window
        tech_element = await self.session.execute(
            select(TechElement).where(TechElement.tech_element_id == tech_element_id)
        )
        tech_element = tech_element.scalar_one_or_none()
        last_collect = tech_element.last_collect_at if tech_element else None

        start_date, end_date = self.get_time_window(mode, last_collect)

        # Create task
        task = CollectTask(
            task_code=task_code,
            tech_element_id=tech_element_id,
            collect_mode=mode,
            time_window_start=start_date,
            time_window_end=end_date,
            triggered_by=triggered_by,
            triggered_at=datetime.utcnow(),
            status="pending"
        )
        self.session.add(task)
        await self.session.flush()

        # Create venue sub-tasks
        bindings = await self.binding_repo.get_by_tech_element(tech_element_id, is_enabled=True)
        for binding in bindings:
            venue_sub_task = VenueSubTask(
                task_id=task.task_id,
                venue_id=binding.venue_id,
                status="pending",
                time_window_start=start_date,
                time_window_end=end_date
            )
            await self.sub_task_repo.create(venue_sub_task)

        await self.session.commit()

        logger.info(
            f"Created task {task.task_id} ({task_code}) for tech_element {tech_element_id} "
            f"with {len(bindings)} venue sub-tasks"
        )

        return task

    async def get_task(self, task_id: int) -> Optional[CollectTask]:
        """Get a task by ID"""
        result = await self.session.execute(
            select(CollectTask).where(CollectTask.task_id == task_id)
        )
        return result.scalar_one_or_none()
