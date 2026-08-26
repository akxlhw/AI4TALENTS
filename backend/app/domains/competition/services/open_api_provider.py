"""Competition domain provider for the cross-domain open-API search registry."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.competition.services.comp_talent_service import CompTalentService
from app.domains.shared.services.open_api.registry import (
    UnifiedTalentSummary,
    register_search_provider,
)


class CompetitionSearchProvider:
    domain = "competition"

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def search(self, keyword: str, limit: int) -> list[UnifiedTalentSummary]:
        summaries, _total = await CompTalentService(self.session).list_talents(
            keyword=keyword, sort_by="rating_desc", page=1, page_size=limit
        )
        return [
            UnifiedTalentSummary(
                domain=self.domain,
                talent_id=s.talent_id,
                name=s.real_name or s.handle or "",
                identifier=s.handle,
                url=s.profile_url,
                tags=[t for t in (s.specialties or [])][:5],
            )
            for s in summaries
        ]


register_search_provider("competition", CompetitionSearchProvider)
