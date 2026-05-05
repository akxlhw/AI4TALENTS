"""Phase 4: Normalize collected institutions to StdSchool."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.academic.services.collect.phases.base import PhaseContext, PhaseHandler
from app.domains.academic.services.collect.progress_tracker import ProgressTracker
from app.domains.academic.services.normalizers import SchoolNormalizer


class PhaseNormalizeSchoolsHandler(PhaseHandler):
    """Phase 4: Normalize raw institutions into standardized schools."""

    phase_name = "标准化学校"
    phase_progress = 40

    def __init__(self, session: AsyncSession, progress_tracker: ProgressTracker) -> None:
        super().__init__(session, progress_tracker)
        self.school_normalizer = SchoolNormalizer(session)

    async def execute(self, context: PhaseContext) -> None:
        progress = context.progress
        progress.current_step = "Normalizing schools"

        result = await self.school_normalizer.normalize_all_institutions(
            task_id=context.task.task_id
        )
        progress.normalized_schools = result.processed

        if result.processed > 0:
            self.progress_tracker.add_log("info", f"标准化学校: {result.processed}")
