"""Lab talent service — browse/search/detail business logic."""

from __future__ import annotations

from urllib.parse import quote_plus

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.domains.lab.repositories.lab_talent_repository import LabTalentRepository
from app.domains.lab.schemas.lab_talent import (
    HomepagePreviewResponse,
    LabProfileResponse,
    LabTalentDetail,
    LabTalentSummary,
    LabWithTalents,
    MentorshipResponse,
)


def _linkedin_search_url(name: str, affiliation: str) -> str:
    """Build a Google search URL as a LinkedIn-discovery fallback link.

    Combines the person's quoted name with their lab affiliation and the
    "linkedin" keyword, e.g. "Joshua Aduol" Princeton CS / ML linkedin.
    Used only when the crawler found no real LinkedIn profile URL — a real
    link in social_links always takes precedence over this fallback.
    """
    parts = [f'"{name.strip()}"']
    if affiliation.strip():
        parts.append(affiliation.strip())
    parts.append("linkedin")
    return "https://www.google.com/search?q=" + quote_plus(" ".join(parts))


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
        data = talent.to_detail_dict()
        # LinkedIn fallback: without a crawler-found real profile URL, expose a
        # Google search URL instead. A real link always takes precedence.
        links = dict(data.get("social_links") or {})
        if "linkedin" not in links:
            affiliation = data.get("lab_name") or data.get("parent_lab") or ""
            links["linkedin"] = _linkedin_search_url(data["name"], affiliation)
        data["social_links"] = links
        return LabTalentDetail(**data)

    async def get_mentorship(self, talent_id: int) -> MentorshipResponse:
        """Get mentorship info: advisors + students supervised by this talent."""
        from app.domains.lab.schemas.lab_talent import AdvisorStudentItem

        talent = await self.repo.get_by_id(talent_id)
        if not talent:
            raise NotFoundError("LabTalent", talent_id)

        # Try to find advisor's talent_id (if advisor is also in DB)
        advisor_id = None
        co_advisor_id = None
        if talent.advisor:
            adv = await self.repo.find_by_name(talent.advisor)
            if adv:
                advisor_id = adv.talent_id
        if talent.co_advisor:
            co_adv = await self.repo.find_by_name(talent.co_advisor)
            if co_adv:
                co_advisor_id = co_adv.talent_id

        # Reverse lookup: students whose advisor is this person
        students_raw = await self.repo.get_students(talent.name)
        students = [
            AdvisorStudentItem(
                talent_id=row.talent_id,
                name=row.name,
                role_type=row.role_type,
                academic_level=row.academic_level,
                cohort_year=row.cohort_year,
                parent_lab=row.parent_lab,
            )
            for row in students_raw
        ]

        return MentorshipResponse(
            advisor=talent.advisor,
            co_advisor=talent.co_advisor,
            advisor_talent_id=advisor_id,
            co_advisor_talent_id=co_advisor_id,
            students=students,
        )

    async def list_labs(self, *, preview_limit: int = 6) -> list[LabWithTalents]:
        """List parent labs with a preview of their talents."""
        labs = await self.repo.list_labs_with_talents(preview_limit=preview_limit)
        return [LabWithTalents(**lab) for lab in labs]

    async def get_lab_profile(self, parent_lab: str) -> LabProfileResponse:
        """Get lab profile (metadata + aggregated stats). Raises NotFoundError."""
        profile = await self.repo.get_lab_profile(parent_lab)
        if not profile:
            raise NotFoundError("Lab", parent_lab)
        return LabProfileResponse(**profile)

    async def get_homepage_preview(self, talent_id: int) -> HomepagePreviewResponse:
        """Get talent's homepage preview — cache-first, fetch on miss/expiry."""
        from datetime import datetime, timedelta

        from app.domains.lab.services.homepage_preview_service import (
            _HOMEPAGE_CACHE_TTL_SECONDS,
            HomepagePreviewService,
        )

        talent = await self.repo.get_by_id(talent_id)
        if not talent:
            raise NotFoundError("LabTalent", talent_id)

        if not talent.homepage:
            return HomepagePreviewResponse(html="", base_url="", status="no_homepage")

        homepage_url: str = str(talent.homepage)

        # Cache hit and still fresh — return immediately
        if talent.homepage_cache and talent.homepage_cached_at:
            age = datetime.utcnow() - talent.homepage_cached_at
            if age < timedelta(seconds=_HOMEPAGE_CACHE_TTL_SECONDS):
                return HomepagePreviewResponse(
                    html=str(talent.homepage_cache),
                    base_url=homepage_url,
                    title="",
                    status="ok",
                )

        # Cache miss or expired — fetch, clean, and persist
        preview_svc = HomepagePreviewService()
        result = await preview_svc.fetch_preview(homepage_url)
        if result["status"] == "ok" and result["html"]:
            talent.homepage_cache = result["html"]
            talent.homepage_cached_at = datetime.utcnow()
            await self.session.commit()
        return HomepagePreviewResponse(**result)
