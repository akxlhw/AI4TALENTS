"""Competition contest query service."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.competition.models.competition import CompContest
from app.domains.competition.repositories.competition_repository import CompetitionRepository
from app.domains.competition.schemas.competition import (
    CompContestDetail,
    CompContestSummary,
    CompLeaderboardEntry,
    CompTeamLeaderboardEntry,
)


def to_summary(contest: CompContest, results_count: int = 0) -> CompContestSummary:
    return CompContestSummary(
        contest_id=contest.contest_id,
        series_code=contest.source_code,
        external_id=contest.external_id,
        name=contest.name,
        start_time=contest.start_time,
        season=contest.season,
        status=contest.status,
        source_url=contest.source_url,
        results_count=results_count,
    )


class CompContestService:
    """Contest list/detail (leaderboard) assembly."""

    def __init__(self, session: AsyncSession):
        self.repo = CompetitionRepository(session)

    async def list_contests(
        self,
        *,
        series_code: str | None,
        season: str | None,
        keyword: str | None,
        year_gte: int | None,
        page: int,
        page_size: int,
    ) -> tuple[list[CompContestSummary], int]:
        rows, total = await self.repo.list_contests(
            series_code=series_code,
            season=season,
            keyword=keyword,
            year_gte=year_gte,
            page=page,
            page_size=page_size,
        )
        return [to_summary(c, rc) for c, rc in rows], total

    async def get_detail(self, contest_id: int) -> CompContestDetail | None:
        contest = await self.repo.get_contest(contest_id)
        if contest is None:
            return None
        personal = await self.repo.list_personal_leaderboard(contest_id)
        teams = await self.repo.list_team_leaderboard(contest_id)
        summary = to_summary(contest, results_count=len(personal) + len(teams))
        return CompContestDetail(
            **summary.model_dump(),
            duration_seconds=contest.duration_seconds,
            raw_meta=contest.raw_meta,
            results=[
                CompLeaderboardEntry(
                    rank=result.rank,
                    talent_id=talent.talent_id,
                    handle=talent.handle,
                    school=talent.school,
                    country_code=talent.country_code,
                    avatar_url=talent.avatar_url,
                    score=result.score,
                    rating_before=result.rating_before,
                    rating_after=result.rating_after,
                    award=result.award,
                    team_name=result.team_name,
                )
                for result, talent in personal
            ],
            team_results=[
                CompTeamLeaderboardEntry(
                    rank=result.rank,
                    team_id=team.team_id,
                    team_name=team.name,
                    school=team.school,
                    country_code=team.country_code,
                    award=result.award,
                    score=result.score,
                    team_members=result.team_members,
                )
                for result, team in teams
            ],
        )
