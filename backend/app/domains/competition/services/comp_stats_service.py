"""Competition overview stats service."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.competition.repositories.competition_repository import CompetitionRepository
from app.domains.competition.schemas.competition import CompOverviewOut, CompSeriesOut
from app.domains.competition.services.comp_contest_service import to_summary as contest_summary
from app.domains.competition.services.comp_talent_service import to_summary as talent_summary


class CompStatsService:
    """Overview statistics for the competition domain."""

    def __init__(self, session: AsyncSession):
        self.repo = CompetitionRepository(session)

    async def get_overview(self) -> CompOverviewOut:
        total_talents = await self.repo.count_visible_talents()
        total_contests = await self.repo.count_contests()
        total_medalists = await self.repo.count_medalists()
        total_countries = await self.repo.count_countries()
        series_rows = await self.repo.list_series_with_counts()
        enabled_series = sum(1 for s, _, _ in series_rows if s.is_enabled)
        top = await self.repo.top_rated_talents(limit=10)
        recent_rows, _ = await self.repo.list_contests(page=1, page_size=5)
        return CompOverviewOut(
            total_talents=total_talents,
            total_contests=total_contests,
            total_series=enabled_series,
            total_medalists=total_medalists,
            total_countries=total_countries,
            top_talents=[talent_summary(t) for t in top],
            recent_contests=[contest_summary(c, rc) for c, rc in recent_rows],
        )

    async def list_series(self) -> list[CompSeriesOut]:
        rows = await self.repo.list_series_with_counts()
        return [
            CompSeriesOut(
                series_id=series.series_id,
                code=series.code,
                name=series.name,
                name_en=series.name_en,
                homepage=series.homepage,
                description=series.description,
                logo_url=series.logo_url,
                is_enabled=series.is_enabled,
                talents_count=talents_count,
                contests_count=contests_count,
            )
            for series, talents_count, contests_count in rows
        ]
