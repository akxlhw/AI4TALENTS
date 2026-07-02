"""Lab stats service — overview statistics for the lab library."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.lab.repositories.lab_talent_repository import LabTalentRepository
from app.domains.lab.schemas.lab_talent import LabStatsResponse


class LabStatsService:
    """Service computing overview statistics."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = LabTalentRepository(session)

    async def get_stats(self) -> LabStatsResponse:
        """Compute and return overview statistics."""
        data = await self.repo.get_stats()
        return LabStatsResponse(**data)
