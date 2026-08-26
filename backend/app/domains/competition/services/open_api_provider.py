"""Competition domain provider for the cross-domain open-API search registry."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.competition.services.comp_talent_service import CompTalentService
from app.domains.shared.services.open_api.registry import UnifiedTalentSummary


class CompetitionSearchProvider:
    domain = "competition"

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def search(self, keyword: str, limit: int) -> list[UnifiedTalentSummary]:
        summaries, _total = await CompTalentService(self.session).list_talents(
            keyword=keyword,
            country_code=None,
            school=None,
            min_rating=None,
            rank_title=None,
            sort_by="rating_desc",
            page=1,
            page_size=limit,
        )
        return [
            UnifiedTalentSummary(
                domain=self.domain,
                talent_id=s.talent_id,
                name=s.real_name or s.handle or "",
                identifier=s.handle,
                url=s.avatar_url,
                tags=[],
            )
            for s in summaries
        ]
