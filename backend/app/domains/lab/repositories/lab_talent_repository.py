"""Lab talent repository — data access layer."""

from __future__ import annotations

from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.lab.models.lab_talent import LabTalent

# Sortable field → column expression mapping
_SORT_MAP: dict[str, Any] = {
    "name_asc": LabTalent.name.asc(),
    "name_desc": LabTalent.name.desc(),
    "cohort_desc": LabTalent.cohort_year.desc().nullslast(),
    "cohort_asc": LabTalent.cohort_year.asc().nullsfirst(),
    "created_desc": LabTalent.created_at.desc(),
    "created_asc": LabTalent.created_at.asc(),
}


class LabTalentRepository:
    """Repository for lab_talent table CRUD and queries."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, talent_id: int) -> LabTalent | None:
        """Fetch a single talent by id (only visible)."""
        result = await self.session.execute(
            select(LabTalent).where(
                LabTalent.talent_id == talent_id, LabTalent.is_visible.is_(True)
            )
        )
        return result.scalar_one_or_none()

    async def list_talents(
        self,
        *,
        keyword: str | None = None,
        parent_lab: str | None = None,
        lab_name: str | None = None,
        role_type: str | None = None,
        academic_level: str | None = None,
        research_area: str | None = None,
        cohort_year_gte: int | None = None,
        sort_by: str = "created_desc",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[LabTalent], int]:
        """List talents with filters, sorting, pagination. Returns (items, total)."""
        conditions: list[Any] = [LabTalent.is_visible.is_(True)]

        if keyword:
            conditions.append(LabTalent.name.ilike(f"%{keyword}%"))
        if parent_lab:
            conditions.append(LabTalent.parent_lab == parent_lab)
        if lab_name:
            conditions.append(LabTalent.lab_name == lab_name)
        if role_type:
            conditions.append(LabTalent.role_type == role_type)
        if academic_level:
            conditions.append(LabTalent.academic_level == academic_level)
        if cohort_year_gte is not None:
            conditions.append(LabTalent.cohort_year >= cohort_year_gte)
        # research_area: JSON array containment (PostgreSQL @> operator on json)
        if research_area:
            conditions.append(LabTalent.research_areas.op("@>")([research_area]))

        stmt = select(LabTalent).where(*conditions)
        order_expr = _SORT_MAP.get(sort_by, LabTalent.created_at.desc())
        stmt = stmt.order_by(order_expr)

        # Count before pagination
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.session.scalar(count_stmt) or 0

        # Paginate
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        items = list(result.scalars().all())
        return items, total

    async def delete_by_parent_lab(self, parent_lab: str) -> int:
        """Delete all talents belonging to a parent lab. Returns deleted count."""
        result = await self.session.execute(
            delete(LabTalent).where(LabTalent.parent_lab == parent_lab)
        )
        return result.rowcount or 0

    async def bulk_insert(self, talents: list[dict[str, Any]], batch_size: int = 500) -> int:
        """Bulk insert talent dicts (keyed by column name). Returns inserted count.

        Batched to stay under asyncpg's parameter limit. Uses simple INSERT
        (not upsert) because import is preceded by delete_by_parent_lab.
        """
        if not talents:
            return 0

        inserted = 0
        for i in range(0, len(talents), batch_size):
            batch = talents[i : i + batch_size]
            stmt = pg_insert(LabTalent).values(batch)
            await self.session.execute(stmt)
            inserted += len(batch)
        await self.session.flush()
        return inserted

    async def list_labs_with_talents(
        self, *, preview_limit: int = 6
    ) -> list[dict[str, Any]]:
        """Return parent labs ordered by headcount, each with a talent preview."""
        base_filter = LabTalent.is_visible.is_(True)

        lab_result = await self.session.execute(
            select(LabTalent.parent_lab.label("name"), func.count().label("count"))
            .where(base_filter)
            .group_by(LabTalent.parent_lab)
            .order_by(func.count().desc())
        )
        labs = [{"name": row.name, "count": row.count} for row in lab_result.all()]

        for lab in labs:
            talent_result = await self.session.execute(
                select(LabTalent)
                .where(base_filter, LabTalent.parent_lab == lab["name"])
                .order_by(LabTalent.created_at.desc())
                .limit(preview_limit)
            )
            talents = talent_result.scalars().all()
            lab["talents"] = [t.to_summary_dict() for t in talents]
            # Use the first talent's lab_logo_url as the lab's logo.
            for t in talents:
                if t.lab_logo_url:
                    lab["logo_url"] = t.lab_logo_url
                    break

            # Role distribution for the mini composition bar (all members)
            role_result = await self.session.execute(
                select(
                    LabTalent.role_type.label("role"),
                    func.count().label("count"),
                )
                .where(base_filter, LabTalent.parent_lab == lab["name"])
                .group_by(LabTalent.role_type)
            )
            lab["role_distribution"] = {
                row.role: row.count for row in role_result.all()
            }

        return labs

    async def get_stats(self) -> dict[str, Any]:
        """Compute overview statistics."""
        base_filter = LabTalent.is_visible.is_(True)

        # Totals
        total_talents = (
            await self.session.scalar(
                select(func.count()).select_from(select(LabTalent).where(base_filter).subquery())
            )
            or 0
        )

        total_parent_labs = (
            await self.session.scalar(
                select(func.count(func.distinct(LabTalent.parent_lab))).where(base_filter)
            )
            or 0
        )

        total_sub_labs = (
            await self.session.scalar(
                select(func.count(func.distinct(LabTalent.lab_name))).where(base_filter)
            )
            or 0
        )

        # Parent lab distribution
        pl_result = await self.session.execute(
            select(LabTalent.parent_lab.label("name"), func.count().label("count"))
            .where(base_filter)
            .group_by(LabTalent.parent_lab)
            .order_by(func.count().desc())
        )
        parent_lab_distribution = [
            {"name": row.name, "count": row.count} for row in pl_result.all()
        ]

        # Role distribution
        rt_result = await self.session.execute(
            select(LabTalent.role_type.label("name"), func.count().label("count"))
            .where(base_filter)
            .group_by(LabTalent.role_type)
            .order_by(func.count().desc())
        )
        role_distribution = [{"name": row.name, "count": row.count} for row in rt_result.all()]

        # Academic level distribution (students only)
        al_result = await self.session.execute(
            select(LabTalent.academic_level.label("name"), func.count().label("count"))
            .where(base_filter, LabTalent.academic_level.is_not(None))
            .group_by(LabTalent.academic_level)
            .order_by(func.count().desc())
        )
        academic_level_distribution = [
            {"name": row.name, "count": row.count} for row in al_result.all()
        ]

        # Top sub-labs by headcount
        tl_result = await self.session.execute(
            select(LabTalent.lab_name.label("name"), func.count().label("count"))
            .where(base_filter)
            .group_by(LabTalent.lab_name)
            .order_by(func.count().desc())
            .limit(10)
        )
        top_labs = [{"name": row.name, "count": row.count} for row in tl_result.all()]

        return {
            "total_talents": total_talents,
            "total_parent_labs": total_parent_labs,
            "total_sub_labs": total_sub_labs,
            "parent_lab_distribution": parent_lab_distribution,
            "role_distribution": role_distribution,
            "academic_level_distribution": academic_level_distribution,
            "top_labs": top_labs,
        }
