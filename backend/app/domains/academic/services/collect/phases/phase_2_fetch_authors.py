"""Phase 2: Fetch all unique authors from collected works."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.academic.repositories.raw_data_repository import (
    RawAuthorRepository,
    RawWorkRepository,
)
from app.domains.academic.services.collect.phases.base import PhaseContext, PhaseHandler
from app.domains.academic.services.collect.progress_tracker import ProgressTracker
from app.domains.academic.services.data_fetchers import AuthorFetcher

logger = logging.getLogger(__name__)


class PhaseFetchAuthorsHandler(PhaseHandler):
    """Phase 2: Fetch missing authors from OpenAlex API."""

    phase_name = "获取作者数据"
    phase_progress = 20

    def __init__(
        self,
        session: AsyncSession,
        progress_tracker: ProgressTracker,
        author_fetcher: AuthorFetcher | None = None,
    ) -> None:
        super().__init__(session, progress_tracker)
        self.raw_work_repo = RawWorkRepository(session)
        self.raw_author_repo = RawAuthorRepository(session)
        self.author_fetcher = author_fetcher

    async def execute(self, context: PhaseContext) -> None:
        progress = context.progress
        progress.current_step = "Fetching authors"

        if not self.author_fetcher:
            self.progress_tracker.add_log("warning", "Author fetcher not configured")
            return

        all_author_ids = await self.raw_work_repo.get_author_ids_by_task(context.task.task_id)
        if not all_author_ids:
            return

        progress.total_authors = len(all_author_ids)
        missing_ids = await self.raw_author_repo.get_missing_author_ids(list(all_author_ids))

        if missing_ids:
            author_progress = await self.author_fetcher.fetch_authors_by_ids(
                author_ids=missing_ids, task_id=context.task.task_id
            )
            self.progress_tracker.add_log(
                "info", f"获取作者: {author_progress.fetched}/{len(all_author_ids)}"
            )
        else:
            logger.debug(f"All {len(all_author_ids)} authors already in database")
