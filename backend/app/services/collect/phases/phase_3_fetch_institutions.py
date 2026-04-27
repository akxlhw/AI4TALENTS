"""Phase 3: Fetch all unique institutions from collected authors."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.raw_data import RawAuthor
from app.repositories.raw_data_repository import RawInstitutionRepository
from app.services.collect.phases.base import PhaseContext, PhaseHandler
from app.services.collect.progress_tracker import ProgressTracker
from app.services.data_fetchers import InstitutionFetcher

logger = logging.getLogger(__name__)


class PhaseFetchInstitutionsHandler(PhaseHandler):
    """Phase 3: Fetch missing institutions from OpenAlex API.

    Collects three types of institution IDs:
    1. last_known_institution_id (legacy)
    2. primary_education_id (education)
    3. primary_company_id (company)
    """

    phase_name = "获取机构数据"
    phase_progress = 30

    def __init__(
        self,
        session: AsyncSession,
        progress_tracker: ProgressTracker,
        institution_fetcher: InstitutionFetcher | None = None,
    ) -> None:
        super().__init__(session, progress_tracker)
        self.raw_inst_repo = RawInstitutionRepository(session)
        self.institution_fetcher = institution_fetcher

    async def execute(self, context: PhaseContext) -> None:
        progress = context.progress
        progress.current_step = "Fetching institutions"

        if not self.institution_fetcher:
            self.progress_tracker.add_log("warning", "Institution fetcher not configured")
            return

        result = await self.session.execute(
            select(
                RawAuthor.last_known_institution_id,
                RawAuthor.primary_education_id,
                RawAuthor.primary_company_id,
            )
            .where(RawAuthor.fetch_task_id == context.task.task_id)
        )

        institution_ids: set[str] = set()
        for row in result.fetchall():
            if row[0]:
                institution_ids.add(row[0])
            if row[1]:
                institution_ids.add(row[1])
            if row[2]:
                institution_ids.add(row[2])

        if not institution_ids:
            return

        progress.total_institutions = len(institution_ids)
        missing_ids = await self.raw_inst_repo.get_missing_ids(list(institution_ids))

        if missing_ids:
            inst_progress = await self.institution_fetcher.fetch_institutions_by_ids(
                institution_ids=missing_ids, task_id=context.task.task_id
            )
            self.progress_tracker.add_log(
                "info", f"获取机构: {inst_progress.fetched}/{len(institution_ids)}"
            )
        else:
            logger.debug(f"All {len(institution_ids)} institutions already in database")
