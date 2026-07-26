"""Lab talent repository — data access layer."""

from __future__ import annotations

from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.lab.constants.lab_founders import founder_for
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

    async def find_by_name(self, name: str) -> LabTalent | None:
        """Find a visible talent by exact name match (first result)."""
        result = await self.session.execute(
            select(LabTalent).where(LabTalent.name == name, LabTalent.is_visible.is_(True)).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_students(self, advisor_name: str, limit: int = 50) -> list[LabTalent]:
        """Find talents whose advisor matches the given name (reverse lookup)."""
        result = await self.session.execute(
            select(
                LabTalent.talent_id,
                LabTalent.name,
                LabTalent.role_type,
                LabTalent.academic_level,
                LabTalent.cohort_year,
                LabTalent.parent_lab,
            )
            .where(
                LabTalent.is_visible.is_(True),
                (LabTalent.advisor == advisor_name) | (LabTalent.co_advisor == advisor_name),
            )
            .order_by(LabTalent.cohort_year.desc().nullslast())
            .limit(limit)
        )
        return result.all()

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
        # research_area: JSONB containment (@> requires jsonb, not json)
        if research_area:
            conditions.append(LabTalent.research_areas.cast(JSONB).op("@>")(str([research_area])))

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

    async def list_labs_with_talents(self, *, preview_limit: int = 6) -> list[dict[str, Any]]:
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
            lab["role_distribution"] = {row.role: row.count for row in role_result.all()}

            # Lab description from lab_info table
            from app.domains.lab.models.lab_talent import LabInfo

            info_result = await self.session.execute(
                select(LabInfo.description).where(LabInfo.parent_lab == lab["name"])
            )
            info_row = info_result.fetchone()
            lab["description"] = info_row[0] if info_row else None

        return labs

    async def get_lab_profile(self, parent_lab: str) -> dict[str, Any] | None:
        """Aggregate lab profile: metadata from lab_info + stats from lab_talent."""
        from app.domains.lab.models.lab_talent import LabInfo

        base_filter = LabTalent.is_visible.is_(True)

        # Lab metadata
        info_result = await self.session.execute(
            select(LabInfo).where(LabInfo.parent_lab == parent_lab)
        )
        info = info_result.scalar_one_or_none()

        # Role distribution
        role_result = await self.session.execute(
            select(LabTalent.role_type, func.count())
            .where(base_filter, LabTalent.parent_lab == parent_lab)
            .group_by(LabTalent.role_type)
        )
        role_dist = {row[0]: row[1] for row in role_result.all()}

        # Sub-labs
        sub_result = await self.session.execute(
            select(func.distinct(LabTalent.lab_name)).where(
                base_filter, LabTalent.parent_lab == parent_lab
            )
        )
        sub_labs = [row[0] for row in sub_result.all() if row[0]]

        total = sum(role_dist.values())

        return {
            "parent_lab": parent_lab,
            "description": info.description if info else None,
            "research_focus": info.research_focus if info else None,
            "research_directions": (info.research_directions if info else []) or [],
            "homepage": info.homepage if info else None,
            "logo_url": info.logo_url if info else None,
            "total_talents": total,
            "role_distribution": role_dist,
            "sub_labs": sub_labs,
        }

    async def get_advisor_network(self, parent_lab: str) -> dict[str, Any]:
        """Get advisor→student relationship edges for network visualization."""
        result = await self.session.execute(
            select(
                LabTalent.talent_id,
                LabTalent.name,
                LabTalent.role_type,
                LabTalent.photo_url,
                LabTalent.advisor,
                LabTalent.co_advisor,
            ).where(
                LabTalent.is_visible.is_(True),
                LabTalent.parent_lab == parent_lab,
                LabTalent.advisor.isnot(None),
                LabTalent.advisor != "",
            )
        )
        rows = result.all()

        # Index all talents in this lab by name — advisor nodes are enriched
        # from real talent records (photo, talent_id, role) when they exist.
        all_talents = (
            await self.session.execute(
                select(
                    LabTalent.talent_id,
                    LabTalent.name,
                    LabTalent.role_type,
                    LabTalent.photo_url,
                ).where(LabTalent.is_visible.is_(True), LabTalent.parent_lab == parent_lab)
            )
        ).all()
        by_name = {r.name: r for r in all_talents}

        founder = founder_for(parent_lab)
        founder_variants = founder[1] if founder else set()
        canonical_founder = founder[0] if founder else None

        # Build node list (unique names) + edge list (advisor→student)
        nodes: dict[str, dict] = {}
        edges: list[dict] = []
        for row in rows:
            student_key = row.name
            if student_key not in nodes:
                nodes[student_key] = {
                    "name": row.name,
                    "talent_id": row.talent_id,
                    "role_type": row.role_type,
                    "is_student": row.role_type in ("student", "graduate"),
                    "photo_url": row.photo_url,
                    "is_founder": False,
                }
            for advisor_name, is_co in [(row.advisor, False), (row.co_advisor, True)]:
                if not advisor_name:
                    continue
                # Normalize founder name variants (e.g. "Zhi-Hua Zhou" → "周志华")
                normalized = canonical_founder if advisor_name in founder_variants else advisor_name
                if normalized not in nodes:
                    person = by_name.get(normalized)
                    nodes[normalized] = {
                        "name": normalized,
                        "talent_id": person.talent_id if person else None,
                        "role_type": person.role_type if person else "professor",
                        "is_student": False,
                        "photo_url": person.photo_url if person else None,
                        "is_founder": normalized == canonical_founder,
                    }
                edges.append(
                    {
                        "source": normalized,
                        "target": student_key,
                        "type": "co_advisor" if is_co else "advisor",
                    }
                )

        return {
            "nodes": list(nodes.values()),
            "edges": edges,
        }

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
