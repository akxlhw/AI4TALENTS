"""Lab talent service — browse/search/detail business logic."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.domains.lab.repositories.lab_talent_repository import LabTalentRepository
from app.domains.lab.schemas.lab_talent import LabTalentDetail, LabTalentSummary


class LabTalentService:
    """Service for listing, searching, and viewing lab talents."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = LabTalentRepository(session)

    async def list_talents(
        self,
        *,
        keyword: str | None = None,
        parent_lab: str | None = None,
        lab_name: str | None = None,
        role_type: str | None = None,
        academic_level: str | None = None,
        research_area: str | None = None,
        cohort_year_gte: int | None = None,
        sort_by: str = "created_desc",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[LabTalentSummary], int]:
        """List talents with filters. Returns (summaries, total)."""
        items, total = await self.repo.list_talents(
            keyword=keyword,
            parent_lab=parent_lab,
            lab_name=lab_name,
            role_type=role_type,
            academic_level=academic_level,
            research_area=research_area,
            cohort_year_gte=cohort_year_gte,
            sort_by=sort_by,
            page=page,
            page_size=page_size,
        )
        summaries = [LabTalentSummary(**t.to_summary_dict()) for t in items]
        return summaries, total

    async def get_talent_detail(self, talent_id: int) -> LabTalentDetail:
        """Get full detail for a single talent. Raises NotFoundError if missing."""
        talent = await self.repo.get_by_id(talent_id)
        if not talent:
            raise NotFoundError("LabTalent", talent_id)
        return LabTalentDetail(**talent.to_detail_dict())
