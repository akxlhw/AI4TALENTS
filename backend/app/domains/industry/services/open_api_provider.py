"""Industry domain provider for the cross-domain open-API search registry."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.industry.services.industry_talent_service import IndustryTalentService
from app.domains.shared.services.open_api.registry import (
    UnifiedTalentSummary,
    register_search_provider,
)


class IndustrySearchProvider:
    domain = "industry"

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def search(self, keyword: str, limit: int) -> list[UnifiedTalentSummary]:
        summaries, _total = await IndustryTalentService(self.session).list_talents(
            keyword=keyword, page=1, page_size=limit
        )
        items: list[UnifiedTalentSummary] = []
        for s in summaries:
            tags = [
                t
                for t in (
                    getattr(s, "current_title", None),
                    getattr(s, "current_org", None),
                )
                if t
            ]
            # PII redaction: profile_url (contact link) is never exposed
            items.append(
                UnifiedTalentSummary(
                    domain=self.domain,
                    talent_id=s.talent_id,
                    name=s.name or "",
                    identifier=None,
                    url=None,
                    tags=tags,
                )
            )
        return items


register_search_provider("industry", IndustrySearchProvider)
