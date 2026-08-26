"""Lab domain provider for the cross-domain open-API search registry."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.lab.services.lab_talent_service import LabTalentService
from app.domains.shared.services.open_api.registry import UnifiedTalentSummary


class LabSearchProvider:
    domain = "lab"

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def search(self, keyword: str, limit: int) -> list[UnifiedTalentSummary]:
        summaries, _total = await LabTalentService(self.session).list_talents(
            keyword=keyword, page=1, page_size=limit
        )
        return [
            UnifiedTalentSummary(
                domain=self.domain,
                talent_id=s.talent_id,
                name=s.name or "",
                identifier=None,
                url=getattr(s, "homepage", None),
                tags=list(getattr(s, "research_areas", None) or [])[:5],
            )
            for s in summaries
        ]
