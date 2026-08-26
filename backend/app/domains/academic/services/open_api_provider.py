"""Academic domain provider for the cross-domain open-API search registry."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.academic.services.talent_service import TalentService
from app.domains.shared.services.open_api.registry import (
    UnifiedTalentSummary,
    register_search_provider,
)


class AcademicSearchProvider:
    domain = "academic"

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def search(self, keyword: str, limit: int) -> list[UnifiedTalentSummary]:
        talents, _total = await TalentService(self.session).search_talents_basic(
            keyword, page=1, page_size=limit
        )
        return [
            UnifiedTalentSummary(
                domain=self.domain,
                talent_id=t.talent_id,
                name=t.name or t.name_en or "",
                identifier=None,
                url=None,
                tags=[t.role_type] if getattr(t, "role_type", None) else [],
            )
            for t in talents
        ]


register_search_provider("academic", AcademicSearchProvider)
