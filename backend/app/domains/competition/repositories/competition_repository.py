"""Repository for the competition domain (single class, lab-domain style)."""

from __future__ import annotations

from typing import Any, cast

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.competition.models.competition import (
    CompContest,
    CompResult,
    CompSeries,
    CompTalent,
    CompTeam,
)


class CompetitionRepository:
    """Data access for comp_* tables."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ---------- Series ----------
    async def upsert_series(self, data: dict[str, Any]) -> CompSeries:
        series = await self.session.scalar(
            select(CompSeries).where(CompSeries.code == data["code"])
        )
        if series is None:
            series = CompSeries(code=data["code"], name=data["name"])
            self.session.add(series)
        # Merge non-null profile fields only
        for field in ("name", "name_en", "homepage", "description", "logo_url"):
            value = data.get(field)
            if value:
                setattr(series, field, value)
        await self.session.flush()
        return series

    # ---------- Contest ----------
    async def upsert_contest(self, series_id: int, data: dict[str, Any]) -> CompContest:
        contest = await self.session.scalar(
            select(CompContest).where(
                CompContest.source_code == data["source_code"],
                CompContest.external_id == data["external_id"],
            )
        )
        if contest is None:
            contest = CompContest(
                series_id=series_id,
                source_code=data["source_code"],
                external_id=data["external_id"],
                name=data["name"],
            )
            self.session.add(contest)
        contest.series_id = series_id
        for field in (
            "name",
            "start_time",
            "duration_seconds",
            "season",
            "status",
            "source_url",
            "raw_meta",
        ):
            value = data.get(field)
            if value is not None:
                setattr(contest, field, value)
        await self.session.flush()
        return contest

    # ---------- Talent ----------
    async def upsert_talent(self, data: dict[str, Any]) -> CompTalent:
        talent = await self.session.scalar(
            select(CompTalent).where(
                CompTalent.source_code == data["source_code"],
                CompTalent.handle_lower == data["handle_lower"],
            )
        )
        if talent is None:
            talent = CompTalent(
                source_code=data["source_code"],
                handle=data["handle"],
                handle_lower=data["handle_lower"],
                dedup_hash=data["dedup_hash"],
            )
            self.session.add(talent)
        # Merge non-null profile fields only (never overwrite with null)
        for field in (
            "real_name",
            "school",
            "country_code",
            "avatar_url",
            "profile_url",
            "rank_title",
            "global_rank",
            "specialties",
        ):
            value = data.get(field)
            if value:
                setattr(talent, field, value)
        # max_rating only ever increases
        if data.get("max_rating"):
            talent.max_rating = max(talent.max_rating or 0, data["max_rating"])
        if data.get("current_rating"):
            talent.current_rating = data["current_rating"]
        await self.session.flush()
        return talent

    # ---------- Team ----------
    async def upsert_team(self, data: dict[str, Any]) -> CompTeam:
        team = await self.session.scalar(
            select(CompTeam).where(
                CompTeam.source_code == data["source_code"],
                CompTeam.name_lower == data["name_lower"],
                CompTeam.school == data.get("school"),
            )
        )
        if team is None:
            team = CompTeam(
                source_code=data["source_code"],
                name=data["name"],
                name_lower=data["name_lower"],
                school=data.get("school"),
                dedup_hash=data["dedup_hash"],
            )
            self.session.add(team)
        for field in ("country_code", "logo_url"):
            value = data.get(field)
            if value:
                setattr(team, field, value)
        await self.session.flush()
        return team

    # ---------- Result ----------
    async def delete_results_by_contest(self, contest_id: int) -> int:
        result = await self.session.execute(
            delete(CompResult).where(CompResult.contest_id == contest_id)
        )
        return result.rowcount or 0  # type: ignore[attr-defined]

    async def insert_result(self, fields: dict[str, Any]) -> None:
        self.session.add(CompResult(**fields))

    # ---------- Aggregate helpers ----------
    async def count_results(self, talent_id: int) -> int:
        return (
            await self.session.scalar(
                select(func.count(CompResult.result_id)).where(CompResult.talent_id == talent_id)
            )
        ) or 0

    async def count_awards(self, talent_id: int, award: str) -> int:
        return (
            await self.session.scalar(
                select(func.count(CompResult.result_id)).where(
                    CompResult.talent_id == talent_id,
                    CompResult.award == award,
                )
            )
        ) or 0

    async def latest_talent_result(self, talent_id: int) -> CompResult | None:
        """Latest result by contest start_time (falls back to contest_id order)."""
        result = await self.session.scalar(
            select(CompResult)
            .join(CompContest, CompResult.contest_id == CompContest.contest_id)
            .where(CompResult.talent_id == talent_id)
            .order_by(CompContest.start_time.desc().nulls_last(), CompContest.contest_id.desc())
            .limit(1)
        )
        return cast(CompResult | None, result)

    async def max_rating_after(self, talent_id: int) -> int | None:
        result = await self.session.scalar(
            select(func.max(CompResult.rating_after)).where(CompResult.talent_id == talent_id)
        )
        return cast(int | None, result)

    async def latest_contest_time(self, talent_id: int) -> Any:
        return await self.session.scalar(
            select(func.max(CompContest.start_time))
            .select_from(CompResult)
            .join(CompContest, CompResult.contest_id == CompContest.contest_id)
            .where(CompResult.talent_id == talent_id)
        )

    # ---------- Query (read) ----------
    async def list_talents(
        self,
        *,
        keyword: str | None = None,
        country_code: str | None = None,
        school: str | None = None,
        min_rating: int | None = None,
        rank_title: str | None = None,
        sort_by: str = "rating_desc",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[CompTalent], int]:
        conditions: list[Any] = [CompTalent.is_visible.is_(True)]
        if keyword:
            pattern = f"%{keyword.lower()}%"
            conditions.append(
                or_(
                    CompTalent.handle_lower.like(pattern),
                    func.lower(func.coalesce(CompTalent.real_name, "")).like(pattern),
                )
            )
        if country_code:
            conditions.append(CompTalent.country_code == country_code)
        if school:
            conditions.append(CompTalent.school.ilike(f"%{school}%"))
        if min_rating is not None:
            conditions.append(CompTalent.current_rating >= min_rating)
        if rank_title:
            conditions.append(CompTalent.rank_title == rank_title)

        total = (
            await self.session.scalar(select(func.count(CompTalent.talent_id)).where(*conditions))
        ) or 0

        order_column: Any = {
            "rating_desc": CompTalent.current_rating.desc().nulls_last(),
            "rating_asc": CompTalent.current_rating.asc().nulls_last(),
            "contests_desc": CompTalent.contests_count.desc(),
            "medals_desc": CompTalent.medals_gold.desc(),
            "recent_desc": CompTalent.last_contest_at.desc().nulls_last(),
        }.get(sort_by, CompTalent.current_rating.desc().nulls_last())

        items = (
            await self.session.scalars(
                select(CompTalent)
                .where(*conditions)
                .order_by(order_column, CompTalent.talent_id)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
        return list(items), total

    async def get_talent(self, talent_id: int) -> CompTalent | None:
        result = await self.session.scalar(
            select(CompTalent).where(
                CompTalent.talent_id == talent_id, CompTalent.is_visible.is_(True)
            )
        )
        return cast(CompTalent | None, result)

    async def get_talent_history(self, talent_id: int) -> list[tuple[CompResult, CompContest]]:
        rows = (
            await self.session.execute(
                select(CompResult, CompContest)
                .join(CompContest, CompResult.contest_id == CompContest.contest_id)
                .where(CompResult.talent_id == talent_id)
                .order_by(CompContest.start_time.desc().nulls_last(), CompContest.contest_id.desc())
            )
        ).all()
        return [(row[0], row[1]) for row in rows]

    async def list_contests(
        self,
        *,
        series_code: str | None = None,
        season: str | None = None,
        keyword: str | None = None,
        year_gte: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[tuple[CompContest, int]], int]:
        conditions = []
        if series_code:
            conditions.append(CompContest.source_code == series_code)
        if season:
            conditions.append(CompContest.season == season)
        if keyword:
            conditions.append(CompContest.name.ilike(f"%{keyword}%"))
        if year_gte is not None:
            conditions.append(func.extract("year", CompContest.start_time) >= year_gte)

        total = (
            await self.session.scalar(select(func.count(CompContest.contest_id)).where(*conditions))
        ) or 0

        results_count = (
            select(func.count(CompResult.result_id))
            .where(CompResult.contest_id == CompContest.contest_id)
            .correlate(CompContest)
            .scalar_subquery()
        )
        rows = (
            await self.session.execute(
                select(CompContest, results_count.label("results_count"))
                .where(*conditions)
                .order_by(CompContest.start_time.desc().nulls_last(), CompContest.contest_id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
        return [(c, int(rc or 0)) for c, rc in rows], total

    async def get_contest(self, contest_id: int) -> CompContest | None:
        return await self.session.get(CompContest, contest_id)

    async def list_personal_leaderboard(
        self, contest_id: int
    ) -> list[tuple[CompResult, CompTalent]]:
        rows = (
            await self.session.execute(
                select(CompResult, CompTalent)
                .join(CompTalent, CompResult.talent_id == CompTalent.talent_id)
                .where(CompResult.contest_id == contest_id, CompResult.talent_id.isnot(None))
                .order_by(CompResult.rank.asc().nulls_last(), CompResult.score.desc().nulls_last())
            )
        ).all()
        return [(row[0], row[1]) for row in rows]

    async def list_team_leaderboard(self, contest_id: int) -> list[tuple[CompResult, CompTeam]]:
        rows = (
            await self.session.execute(
                select(CompResult, CompTeam)
                .join(CompTeam, CompResult.team_id == CompTeam.team_id)
                .where(
                    CompResult.contest_id == contest_id,
                    CompResult.team_id.isnot(None),
                    CompResult.talent_id.is_(None),
                )
                .order_by(CompResult.rank.asc().nulls_last())
            )
        ).all()
        return [(row[0], row[1]) for row in rows]

    # ---------- Stats ----------
    async def count_visible_talents(self) -> int:
        return (
            await self.session.scalar(
                select(func.count(CompTalent.talent_id)).where(CompTalent.is_visible.is_(True))
            )
        ) or 0

    async def count_contests(self) -> int:
        return (await self.session.scalar(select(func.count(CompContest.contest_id)))) or 0

    async def count_medalists(self) -> int:
        return (
            await self.session.scalar(
                select(func.count(CompTalent.talent_id)).where(
                    CompTalent.is_visible.is_(True), CompTalent.medals_gold > 0
                )
            )
        ) or 0

    async def count_countries(self) -> int:
        return (
            await self.session.scalar(
                select(func.count(func.distinct(CompTalent.country_code))).where(
                    CompTalent.is_visible.is_(True), CompTalent.country_code.isnot(None)
                )
            )
        ) or 0

    async def top_rated_talents(self, limit: int = 10) -> list[CompTalent]:
        items = (
            await self.session.scalars(
                select(CompTalent)
                .where(CompTalent.is_visible.is_(True), CompTalent.current_rating.isnot(None))
                .order_by(CompTalent.current_rating.desc())
                .limit(limit)
            )
        ).all()
        return list(items)

    async def list_series_with_counts(self) -> list[tuple[CompSeries, int, int]]:
        talents_count = (
            select(func.count(CompTalent.talent_id))
            .where(CompTalent.source_code == CompSeries.code, CompTalent.is_visible.is_(True))
            .correlate(CompSeries)
            .scalar_subquery()
        )
        contests_count = (
            select(func.count(CompContest.contest_id))
            .where(CompContest.series_id == CompSeries.series_id)
            .correlate(CompSeries)
            .scalar_subquery()
        )
        rows = (
            await self.session.execute(
                select(CompSeries, talents_count, contests_count).order_by(CompSeries.series_id)
            )
        ).all()
        return [(s, int(tc or 0), int(cc or 0)) for s, tc, cc in rows]
