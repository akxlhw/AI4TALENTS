"""Phase 6: Calculate author-tech domain relationships."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.venue_repository import VenueSubTaskRepository
from app.services.collect.phases.base import PhaseContext, PhaseHandler
from app.services.collect.progress_tracker import ProgressTracker
from app.services.normalizers import TechBelongCalculator


class PhaseTechBelongHandler(PhaseHandler):
    """Phase 6: Calculate tech-belong relationships for completed venues."""

    phase_name = "计算技术归属"
    phase_progress = 60

    def __init__(self, session: AsyncSession, progress_tracker: ProgressTracker) -> None:
        super().__init__(session, progress_tracker)
        self.sub_task_repo = VenueSubTaskRepository(session)
        self.tech_belong_calculator = TechBelongCalculator(session)

    async def execute(self, context: PhaseContext) -> None:
        sub_tasks = await self.sub_task_repo.get_by_task(context.task.task_id)
        for sub_task in sub_tasks:
            if sub_task.status == "completed":
                await self.tech_belong_calculator.calculate_for_venue(
                    venue_id=sub_task.venue_id,
                    tech_domain_id=context.task.tech_domain_id,
                    task_id=context.task.task_id,
                )
