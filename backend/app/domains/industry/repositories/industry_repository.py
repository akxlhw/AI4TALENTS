"""Industry domain repository — data access layer."""

from __future__ import annotations

from typing import Any

from sqlalchemy import Row, cast, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.industry.models.industry import (
    IndustryPosition,
    IndustryPositionTalent,
    IndustryTalent,
)


class IndustryRepository:
    """Repository for the industry_* table family."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ---------------- Position ----------------

    async def create_position(self, data: dict[str, Any]) -> IndustryPosition:
        """Insert a position row and flush."""
        position = IndustryPosition(**data)
        self.session.add(position)
        await self.session.flush()
        return position

    async def get_position(self, position_id: int) -> IndustryPosition | None:
        """Fetch a position by id."""
        return await self.session.get(IndustryPosition, position_id)

    async def list_position_ids(self) -> set[int]:
        """Return all existing position ids (used by import validation)."""
        result = await self.session.execute(select(IndustryPosition.position_id))
        return {row[0] for row in result.all()}

    async def list_positions(
        self, *, status: str | None = None
    ) -> list[Row[tuple[IndustryPosition, int, float | None]]]:
        """List positions with candidate count and average match score.

        Aggregates come from a single GROUP BY subquery over the link table
        (no N+1). Positions without candidates get count=0 / avg=None.
        """
        stats = (
            select(
                IndustryPositionTalent.position_id.label("position_id"),
                func.count().label("candidate_count"),
                func.avg(IndustryPositionTalent.match_score).label("avg_match_score"),
            )
            .group_by(IndustryPositionTalent.position_id)
            .subquery()
        )
        stmt = (
            select(
                IndustryPosition,
                func.coalesce(stats.c.candidate_count, 0).label("candidate_count"),
                stats.c.avg_match_score,
            )
            .outerjoin(stats, stats.c.position_id == IndustryPosition.position_id)
            .order_by(IndustryPosition.created_at.desc())
        )
        if status:
            stmt = stmt.where(IndustryPosition.status == status)
        result = await self.session.execute(stmt)
        return list(result.all())

    async def get_position_stats(self, position_id: int) -> tuple[int, float | None]:
        """Candidate count and average match score for one position."""
        result = await self.session.execute(
            select(
                func.count(),
                func.avg(IndustryPositionTalent.match_score),
            ).where(IndustryPositionTalent.position_id == position_id)
        )
        row = result.one()
        return row[0] or 0, row[1]

    # ---------------- Talent list / detail ----------------

    def _link_exists_condition(
        self,
        *,
        position_id: int | None,
        min_score: float | None,
        status: str | None,
        source_platform: str | None,
        tech_direction: str | None,
    ) -> Any | None:
        """Build an EXISTS condition over the link table for link-level filters.

        All given filters apply to the SAME link row (e.g. position_id +
        min_score means "matched this position with at least this score").
        """
        conds: list[Any] = [
            IndustryPositionTalent.talent_id == IndustryTalent.talent_id,
        ]
        if position_id is not None:
            conds.append(IndustryPositionTalent.position_id == position_id)
        if min_score is not None:
            conds.append(IndustryPositionTalent.match_score >= min_score)
        if status:
            conds.append(IndustryPositionTalent.status == status)
        if source_platform:
            conds.append(IndustryPositionTalent.source_platform == source_platform)

        stmt = select(IndustryPositionTalent.id)
        if tech_direction:
            stmt = stmt.join(
                IndustryPosition,
                IndustryPosition.position_id == IndustryPositionTalent.position_id,
            )
            conds.append(
                IndustryPosition.tech_direction_codes.cast(JSONB).op("@>")(
                    # bind the list with JSONB type so it is encoded exactly once
                    cast([tech_direction], JSONB)
                )
            )
        if len(conds) == 1 and not tech_direction:
            return None  # no link-level filter requested
        return stmt.where(*conds).exists()

    async def list_talents(
        self,
        *,
        keyword: str | None = None,
        position_id: int | None = None,
        min_score: float | None = None,
        status: str | None = None,
        source_platform: str | None = None,
        tech_direction: str | None = None,
        sort_by: str = "match_score_desc",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Row[tuple[IndustryTalent, Any, Any]]], int]:
        """List talents with filters/sort/pagination.

        Each row is (talent, best_match_score, position_hits) where hits are
        aggregated by ONE GROUP BY subquery over the link table joined with
        positions — no per-talent queries (no N+1).
        """
        hits = (
            select(
                IndustryPositionTalent.talent_id.label("talent_id"),
                func.max(IndustryPositionTalent.match_score).label("best_score"),
                func.jsonb_agg(
                    func.jsonb_build_object(
                        "position_id",
                        IndustryPositionTalent.position_id,
                        "title",
                        IndustryPosition.title,
                        "match_score",
                        IndustryPositionTalent.match_score,
                        "status",
                        IndustryPositionTalent.status,
                        "touched",
                        IndustryPositionTalent.touched,
                        "match_tags",
                        IndustryPositionTalent.match_tags,
                    )
                ).label("hits"),
            )
            .join(
                IndustryPosition,
                IndustryPosition.position_id == IndustryPositionTalent.position_id,
            )
            .group_by(IndustryPositionTalent.talent_id)
            .subquery()
        )

        stmt = select(IndustryTalent, hits.c.best_score, hits.c.hits).outerjoin(
            hits, hits.c.talent_id == IndustryTalent.talent_id
        )
        conditions: list[Any] = [IndustryTalent.is_visible.is_(True)]

        if keyword:
            like = f"%{keyword}%"
            conditions.append(
                (IndustryTalent.name.ilike(like))
                | (IndustryTalent.current_org.ilike(like))
                | (IndustryTalent.current_title.ilike(like))
            )
        link_exists = self._link_exists_condition(
            position_id=position_id,
            min_score=min_score,
            status=status,
            source_platform=source_platform,
            tech_direction=tech_direction,
        )
        if link_exists is not None:
            conditions.append(link_exists)

        stmt = stmt.where(*conditions)

        if sort_by == "match_score_asc":
            stmt = stmt.order_by(hits.c.best_score.asc().nullslast())
        elif sort_by == "created_desc":
            stmt = stmt.order_by(IndustryTalent.created_at.desc())
        elif sort_by == "name_asc":
            stmt = stmt.order_by(IndustryTalent.name.asc())
        else:  # match_score_desc (default)
            stmt = stmt.order_by(hits.c.best_score.desc().nullslast())
        stmt = stmt.order_by(IndustryTalent.talent_id)

        count_stmt = select(func.count()).select_from(
            select(IndustryTalent.talent_id).where(*conditions).subquery()
        )
        total = await self.session.scalar(count_stmt) or 0

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        return list(result.all()), total

    async def get_talent(self, talent_id: int) -> IndustryTalent | None:
        """Fetch a single visible talent by id."""
        result = await self.session.execute(
            select(IndustryTalent).where(
                IndustryTalent.talent_id == talent_id,
                IndustryTalent.is_visible.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def get_talent_links(
        self, talent_id: int
    ) -> list[Row[tuple[IndustryPositionTalent, str]]]:
        """All position links of a talent, each with the position title."""
        result = await self.session.execute(
            select(IndustryPositionTalent, IndustryPosition.title)
            .join(
                IndustryPosition,
                IndustryPosition.position_id == IndustryPositionTalent.position_id,
            )
            .where(IndustryPositionTalent.talent_id == talent_id)
            .order_by(IndustryPositionTalent.match_score.desc().nullslast())
        )
        return list(result.all())

    async def get_link(self, talent_id: int, position_id: int) -> IndustryPositionTalent | None:
        """Fetch one position-talent link."""
        result = await self.session.execute(
            select(IndustryPositionTalent).where(
                IndustryPositionTalent.talent_id == talent_id,
                IndustryPositionTalent.position_id == position_id,
            )
        )
        return result.scalar_one_or_none()

    # ---------------- Import upserts ----------------

    async def get_talent_by_hash(self, dedup_hash: str) -> IndustryTalent | None:
        """Fetch a talent by its dedup hash."""
        result = await self.session.execute(
            select(IndustryTalent).where(IndustryTalent.dedup_hash == dedup_hash)
        )
        return result.scalar_one_or_none()

    async def insert_talent(self, data: dict[str, Any]) -> IndustryTalent:
        """Insert a talent row and flush."""
        talent = IndustryTalent(**data)
        self.session.add(talent)
        await self.session.flush()
        return talent

    async def insert_link(self, data: dict[str, Any]) -> IndustryPositionTalent:
        """Insert a position-talent link and flush."""
        link = IndustryPositionTalent(**data)
        self.session.add(link)
        await self.session.flush()
        return link
