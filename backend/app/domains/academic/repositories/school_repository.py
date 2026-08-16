"""
Repository for school operations.
"""

from __future__ import annotations

import logging

from sqlalchemy import (
    BigInteger,
    Column,
    Integer,
    MetaData,
    Table,
    case,
    func,
    or_,
    select,
    text,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.academic.models.school import School
from app.domains.academic.models.talent import Talent

logger = logging.getLogger(__name__)

# Materialized view for affiliation-based school talent counts
mv_school_talent_count = Table(
    "mv_school_talent_count",
    MetaData(),
    Column("school_id", Integer, primary_key=True),
    Column("talent_count", BigInteger),
    Column("professor_count", BigInteger),
    Column("student_count", BigInteger),
)


class SchoolRepository:
    """Repository for School queries."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_list(
        self,
        country_code: str | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
        visible_only: bool = True,
        is_top_school: bool | None = None,
    ) -> tuple[list[School], int]:
        """
        Get paginated list of schools with filters.

        Args:
            country_code: Filter by country code (ISO 3166-1 alpha-2)
            keyword: Search keyword for school name/alias
            page: Page number (1-based)
            page_size: Items per page
            visible_only: If True, only return visible schools
            is_top_school: Filter by top school status (None = all)

        Returns:
            Tuple of (list of schools, total count)
        """
        query = select(School).order_by(School.school_id)

        # Apply filters
        if visible_only:
            query = query.where(School.is_visible.is_(True))

        if country_code:
            query = query.where(School.country_code == country_code.upper())

        if is_top_school is not None:
            query = query.where(School.is_top_school == is_top_school)

        if keyword:
            keyword_pattern = f"%{keyword}%"
            query = query.where(
                or_(
                    School.school_name.ilike(keyword_pattern),
                    School.school_alias.ilike(keyword_pattern),
                )
            )

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.session.execute(query)
        schools = list(result.scalars().all())

        return schools, total

    async def get_by_id(self, school_id: int) -> School | None:
        """
        Get school by ID.

        Args:
            school_id: School ID

        Returns:
            School instance or None
        """
        result = await self.session.execute(select(School).where(School.school_id == school_id))
        return result.scalar_one_or_none()

    async def get_by_source_id(self, source_record_id: str) -> School | None:
        """
        Get school by source record ID (e.g., OpenAlex ID).

        Args:
            source_record_id: Source record ID

        Returns:
            School instance or None
        """
        result = await self.session.execute(
            select(School).where(School.source_record_id == source_record_id)
        )
        return result.scalar_one_or_none()

    async def search(
        self,
        keyword: str,
        limit: int = 10,
    ) -> list[School]:
        """
        Search schools by keyword.

        Args:
            keyword: Search keyword
            limit: Maximum number of results

        Returns:
            List of matching schools
        """
        keyword_pattern = f"%{keyword}%"

        query = (
            select(School)
            .where(
                School.is_visible.is_(True),
                or_(
                    School.school_name.ilike(keyword_pattern),
                    School.school_alias.ilike(keyword_pattern),
                ),
            )
            .order_by(School.school_name)
            .limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_talent_counts(self, school_id: int) -> dict[str, int]:
        """
        Get talent counts by role type for a school.

        Counts talents associated with the school via ANY affiliation field:
        school_id, education_school_id, or company_school_id.
        This aligns with the list/search OR filter logic.

        Args:
            school_id: School ID

        Returns:
            Dictionary with counts by role type
        """
        result = await self.session.execute(
            select(Talent.role_type, func.count(Talent.talent_id).label("count"))
            .where(
                or_(
                    Talent.school_id == school_id,
                    Talent.education_school_id == school_id,
                    Talent.company_school_id == school_id,
                ),
                Talent.is_visible.is_(True),
            )
            .group_by(Talent.role_type)
        )

        counts = {
            "professor": 0,
            "student": 0,
            "graduate": 0,
            "unknown": 0,
            "total": 0,
        }

        for row in result.all():
            counts[row.role_type] = row.count
            counts["total"] += row.count

        return counts

    async def set_top_school_and_commit(self, school_id: int) -> bool:
        """
        Set a school as top school.

        Args:
            school_id: School ID

        Returns:
            True if successful, False if school not found
        """
        school = await self.get_by_id(school_id)
        if not school:
            return False

        school.is_top_school = True
        await self.session.commit()
        return True

    async def unset_top_school_and_commit(self, school_id: int) -> bool:
        """
        Unset a school as top school.

        Args:
            school_id: School ID

        Returns:
            True if successful, False if school not found
        """
        school = await self.get_by_id(school_id)
        if not school:
            return False

        school.is_top_school = False
        await self.session.commit()
        return True

    async def batch_set_top_schools_and_commit(self, school_ids: list[int]) -> int:
        """
        Batch set schools as top schools.

        Args:
            school_ids: List of school IDs

        Returns:
            Number of schools updated
        """
        result = await self.session.execute(
            update(School).where(School.school_id.in_(school_ids)).values(is_top_school=True)
        )
        await self.session.commit()
        return result.rowcount

    async def batch_unset_top_schools_and_commit(self, school_ids: list[int]) -> int:
        """
        Batch unset schools as top schools.

        Args:
            school_ids: List of school IDs

        Returns:
            Number of schools updated
        """
        result = await self.session.execute(
            update(School).where(School.school_id.in_(school_ids)).values(is_top_school=False)
        )
        await self.session.commit()
        return result.rowcount

    async def _mv_exists(self) -> bool:
        """Check whether the materialized view exists in the current database."""
        result = await self.session.execute(text("""
                SELECT 1 FROM pg_matviews
                WHERE matviewname = 'mv_school_talent_count'
                LIMIT 1
                """))
        return result.scalar() is not None

    async def get_mv_stats_batch(self, school_ids: list[int]) -> dict[int, dict]:
        """
        Get affiliation-based talent counts from materialized view for a batch of schools.

        Falls back to a real-time COUNT query when the materialized view
        is unavailable (e.g. missing or locked).

        Args:
            school_ids: List of school IDs

        Returns:
            Dictionary mapping school_id to {"talent_count", "professor_count", "student_count"}
        """
        if not school_ids:
            return {}

        if await self._mv_exists():
            result = await self.session.execute(
                select(
                    mv_school_talent_count.c.school_id,
                    mv_school_talent_count.c.talent_count,
                    mv_school_talent_count.c.professor_count,
                    mv_school_talent_count.c.student_count,
                ).where(mv_school_talent_count.c.school_id.in_(school_ids))
            )
            rows = result.all()
        else:
            logger.warning(
                "Materialized view mv_school_talent_count missing; "
                "falling back to real-time COUNT for get_mv_stats_batch"
            )
            # Fallback: real-time affiliation-based counts
            primary_school = func.coalesce(
                Talent.education_school_id, Talent.company_school_id, Talent.school_id
            )
            result = await self.session.execute(
                select(
                    primary_school.label("school_id"),
                    func.count().label("talent_count"),
                    func.count(case((Talent.role_type == "professor", 1))).label("professor_count"),
                    func.count(case((Talent.role_type.in_(["student", "graduate"]), 1))).label(
                        "student_count"
                    ),
                )
                .where(
                    primary_school.in_(school_ids),
                    Talent.is_visible.is_(True),
                )
                .group_by(primary_school)
            )
            rows = result.all()

        return {
            row.school_id: {
                "talent_count": int(row.talent_count or 0),
                "professor_count": int(row.professor_count or 0),
                "student_count": int(row.student_count or 0),
            }
            for row in rows
        }

    async def get_country_stats(self) -> list[tuple]:
        """
        Get school and professor counts grouped by country.

        Uses mv_school_talent_count for consistent affiliation-based counting.

        Falls back to a real-time COUNT query when the materialized view
        is unavailable (e.g. missing or locked).

        Returns:
            List of tuples (country_code, school_count, professor_count)
        """
        if await self._mv_exists():
            result = await self.session.execute(
                select(
                    School.country_code,
                    func.count(School.school_id).label("school_count"),
                    func.sum(mv_school_talent_count.c.professor_count).label("professor_count"),
                )
                .select_from(School)
                .join(
                    mv_school_talent_count,
                    School.school_id == mv_school_talent_count.c.school_id,
                )
                .where(
                    School.is_visible.is_(True),
                    School.country_code.isnot(None),
                )
                .group_by(School.country_code)
                .order_by(func.sum(mv_school_talent_count.c.professor_count).desc())
            )
            return result.all()

        logger.warning(
            "Materialized view mv_school_talent_count missing; "
            "falling back to real-time COUNT for get_country_stats"
        )
        # Fallback: real-time affiliation-based professor counts per country.
        # Uses an outer join so countries with zero professors are still returned.
        school_subq = (
            select(
                School.country_code,
                func.count(School.school_id).label("school_count"),
            )
            .where(
                School.is_visible.is_(True),
                School.country_code.isnot(None),
            )
            .group_by(School.country_code)
            .subquery()
        )

        prof_subq = (
            select(
                School.country_code,
                func.count(func.distinct(Talent.talent_id)).label("professor_count"),
            )
            .select_from(School)
            .join(
                Talent,
                (
                    (Talent.school_id == School.school_id)
                    | (Talent.education_school_id == School.school_id)
                    | (Talent.company_school_id == School.school_id)
                ),
            )
            .where(
                School.is_visible.is_(True),
                School.country_code.isnot(None),
                Talent.is_visible.is_(True),
                Talent.role_type == "professor",
            )
            .group_by(School.country_code)
            .subquery()
        )

        fallback_query = (
            select(
                school_subq.c.country_code,
                school_subq.c.school_count,
                func.coalesce(prof_subq.c.professor_count, 0).label("professor_count"),
            )
            .select_from(school_subq)
            .outerjoin(prof_subq, school_subq.c.country_code == prof_subq.c.country_code)
            .order_by(func.coalesce(prof_subq.c.professor_count, 0).desc())
        )
        result = await self.session.execute(fallback_query)
        return result.all()
