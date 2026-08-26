"""Open-source domain provider for the cross-domain open-API search registry."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.open_source.services.os_developer_service import OSDeveloperService
from app.domains.shared.services.open_api.registry import (
    UnifiedTalentSummary,
    register_search_provider,
)


class OpenSourceSearchProvider:
    domain = "open_source"

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def search(self, keyword: str, limit: int) -> list[UnifiedTalentSummary]:
        developers, _total = await OSDeveloperService(self.session).list_developers(
            q=keyword, page=1, page_size=limit
        )
        return [
            UnifiedTalentSummary(
                domain=self.domain,
                talent_id=d.developer_id,
                name=d.name or d.github_login or "",
                identifier=d.github_login,
                url=f"https://github.com/{d.github_login}" if d.github_login else None,
                tags=[t for t in (d.tech_tags or [])][:5],
            )
            for d in developers
        ]


register_search_provider("open_source", OpenSourceSearchProvider)
