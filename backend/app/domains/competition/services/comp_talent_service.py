"""Competition talent query service."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.competition.models.competition import CompTalent
from app.domains.competition.repositories.competition_repository import CompetitionRepository
from app.domains.competition.schemas.competition import (
    CompResultItem,
    CompTalentDetail,
    CompTalentSummary,
)


def to_summary(talent: CompTalent) -> CompTalentSummary:
    return CompTalentSummary(
        talent_id=talent.talent_id,
        handle=talent.handle,
        source_code=talent.source_code,
        real_name=talent.real_name,
        school=talent.school,
        country_code=talent.country_code,
        avatar_url=talent.avatar_url,
        current_rating=talent.current_rating,
        max_rating=talent.max_rating,
        rank_title=talent.rank_title,
        contests_count=talent.contests_count,
        medals_gold=talent.medals_gold,
        medals_silver=talent.medals_silver,
        medals_bronze=talent.medals_bronze,
        last_contest_at=talent.last_contest_at,
    )


class CompTalentService:
    """Talent list/detail assembly for the competition domain."""

    def __init__(self, session: AsyncSession):
        self.repo = CompetitionRepository(session)

    async def list_talents(
        self,
        *,
        keyword: str | None,
        country_code: str | None,
        school: str | None,
        min_rating: int | None,
        rank_title: str | None,
        sort_by: str,
        page: int,
        page_size: int,
    ) -> tuple[list[CompTalentSummary], int]:
        items, total = await self.repo.list_talents(
            keyword=keyword,
            country_code=country_code,
            school=school,
            min_rating=min_rating,
            rank_title=rank_title,
            sort_by=sort_by,
            page=page,
            page_size=page_size,
        )
        return [to_summary(t) for t in items], total

    async def get_detail(self, talent_id: int) -> CompTalentDetail | None:
        talent = await self.repo.get_talent(talent_id)
        if talent is None:
            return None
        history = await self.repo.get_talent_history(talent_id)
        summary = to_summary(talent)
        return CompTalentDetail(
            **summary.model_dump(),
            profile_url=talent.profile_url,
            global_rank=talent.global_rank,
            specialties=talent.specialties,
            results=[
                CompResultItem(
                    contest_id=contest.contest_id,
                    contest_name=contest.name,
                    start_time=contest.start_time,
                    rank=result.rank,
                    score=result.score,
                    rating_before=result.rating_before,
                    rating_after=result.rating_after,
                    award=result.award,
                    team_name=result.team_name,
                    source_url=result.source_url,
                )
                for result, contest in history
            ],
        )
