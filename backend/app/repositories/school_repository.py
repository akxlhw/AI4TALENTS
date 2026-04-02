"""
Repository for school operations.
"""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.school import School, SchoolAlias
from app.models.talent import Talent


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
        result = await self.session.execute(
            select(School).where(School.school_id == school_id)
        )
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

    async def get_aliases(self, school_id: int) -> list[SchoolAlias]:
        """
        Get all aliases for a school.

        Args:
            school_id: School ID

        Returns:
            List of SchoolAlias instances
        """
        result = await self.session.execute(
            select(SchoolAlias)
            .where(SchoolAlias.school_id == school_id)
            .order_by(SchoolAlias.alias_id)
        )
        return list(result.scalars().all())

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

    async def get_count_by_country(self) -> dict[str, int]:
        """
        Get school counts grouped by country code.

        Returns:
            Dictionary mapping country_code to count
        """
        query = select(
            School.country_code,
            func.count(School.school_id).label("count")
        ).where(
            School.is_visible.is_(True),
            School.country_code.isnot(None),
        ).group_by(School.country_code)

        result = await self.session.execute(query)
        return {row.country_code: row.count for row in result.all()}

    async def get_talent_counts(
        self, school_id: int
    ) -> dict[str, int]:
        """
        Get talent counts by role type for a school.

        Args:
            school_id: School ID

        Returns:
            Dictionary with counts by role type
        """
        result = await self.session.execute(
            select(
                Talent.role_type,
                func.count(Talent.talent_id).label("count")
            )
            .where(
                Talent.school_id == school_id,
                Talent.is_visible.is_(True),
            )
            .group_by(Talent.role_type)
        )

        counts = {
            "professor": 0,
            "student": 0,
            "graduated": 0,
            "unknown": 0,
            "total": 0,
        }

        for row in result.all():
            counts[row.role_type] = row.count
            counts["total"] += row.count

        return counts
