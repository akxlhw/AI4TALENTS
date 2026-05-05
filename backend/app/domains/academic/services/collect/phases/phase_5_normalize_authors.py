"""Phase 5: Normalize collected authors."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.academic.services.collect.phases.base import PhaseContext, PhaseHandler
from app.domains.academic.services.collect.progress_tracker import ProgressTracker
from app.domains.academic.services.normalizers import AuthorNormalizer


class PhaseNormalizeAuthorsHandler(PhaseHandler):
    """Phase 5: Normalize raw authors into standardized authors."""

    phase_name = "标准化作者"
    phase_progress = 50

    def __init__(self, session: AsyncSession, progress_tracker: ProgressTracker) -> None:
        super().__init__(session, progress_tracker)
        self.author_normalizer = AuthorNormalizer(session)

    async def execute(self, context: PhaseContext) -> None:
        progress = context.progress
        progress.current_step = "Normalizing authors"

        result = await self.author_normalizer.normalize_all_authors(task_id=context.task.task_id)
        progress.normalized_authors = result.processed

        if result.processed > 0:
            self.progress_tracker.add_log("info", f"标准化作者: {result.processed}")
