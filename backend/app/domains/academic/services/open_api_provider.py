"""Academic domain provider for the cross-domain open-API search registry."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.academic.services.talent_service import TalentService
from app.domains.shared.services.open_api.registry import UnifiedTalentSummary


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
                talent_id=int(t.talent_id),
                name=str(t.name or t.name_en or ""),
                identifier=None,
                url=None,
                tags=[str(t.role_type)] if getattr(t, "role_type", None) else [],
            )
            for t in talents
        ]
