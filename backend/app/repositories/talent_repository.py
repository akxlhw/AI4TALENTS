"""
Repository for talent operations.
"""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.school import School
from app.models.talent import RoleProfile, SelectedWork, Talent


class TalentRepository:
    """Repository for Talent queries."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_list(
        self,
        school_id: int | None = None,
        country_code: str | None = None,
        role_type: str | None = None,
        min_works: int | None = None,
        min_citations: int | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
        visible_only: bool = True,
    ) -> tuple[list[Talent], int]:
        """
        Get paginated list of talents with filters.

        Args:
            school_id: Filter by school ID
            country_code: Filter by country code (via school)
            role_type: Filter by role type
            min_works: Minimum works count
            min_citations: Minimum citation count
            keyword: Search keyword for name/title
            page: Page number (1-based)
            page_size: Items per page
            visible_only: If True, only return visible talents

        Returns:
            Tuple of (list of talents, total count)
        """
        query = (
            select(Talent)
            .options(selectinload(Talent.school))
            .order_by(Talent.cited_by_count.desc())
        )

        # Apply filters
        if visible_only:
            query = query.where(Talent.is_visible.is_(True))

        if school_id:
            query = query.where(Talent.school_id == school_id)

        if country_code:
            # Join with school to filter by country_code
            query = query.join(School).where(School.country_code == country_code.upper())

        if role_type:
            query = query.where(Talent.role_type == role_type)

        if min_works is not None:
            query = query.where(Talent.works_count >= min_works)

        if min_citations is not None:
            query = query.where(Talent.cited_by_count >= min_citations)

        if keyword:
            keyword_pattern = f"%{keyword}%"
            query = query.where(
                or_(
                    Talent.name.ilike(keyword_pattern),
                    Talent.name_en.ilike(keyword_pattern),
                    Talent.current_title.ilike(keyword_pattern),
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
        talents = list(result.scalars().all())

        return talents, total

    async def get_list_by_cursor(
        self,
        cursor: int | None = None,
        page_size: int = 20,
        school_id: int | None = None,
        country_code: str | None = None,
        role_type: str | None = None,
        min_works: int | None = None,
        min_citations: int | None = None,
        keyword: str | None = None,
        visible_only: bool = True,
    ) -> tuple[list[Talent], int | None]:
        """
        Get talents using cursor-based pagination (efficient for deep pagination).

        Cursor-based pagination uses talent_id as the cursor, which is much more
        efficient than OFFSET for large datasets.

        Args:
            cursor: Last talent_id from previous page (None for first page)
            page_size: Items per page
            school_id: Filter by school ID
            country_code: Filter by country code
            role_type: Filter by role type
            min_works: Minimum works count
            min_citations: Minimum citation count
            keyword: Search keyword
            visible_only: If True, only return visible talents

        Returns:
            Tuple of (list of talents, next_cursor or None if no more pages)
        """
        # Use a subquery approach for efficient filtering with cursor
        # Order by talent_id descending for consistent pagination
        query = (
            select(Talent)
            .options(selectinload(Talent.school))
            .order_by(Talent.talent_id.desc())
        )

        # Apply cursor filter (get items with id < cursor)
        if cursor is not None:
            query = query.where(Talent.talent_id < cursor)

        # Apply filters
        if visible_only:
            query = query.where(Talent.is_visible.is_(True))

        if school_id:
            query = query.where(Talent.school_id == school_id)

        if country_code:
            query = query.join(School).where(School.country_code == country_code.upper())

        if role_type:
            query = query.where(Talent.role_type == role_type)

        if min_works is not None:
            query = query.where(Talent.works_count >= min_works)

        if min_citations is not None:
            query = query.where(Talent.cited_by_count >= min_citations)

        if keyword:
            keyword_pattern = f"%{keyword}%"
            query = query.where(
                or_(
                    Talent.name.ilike(keyword_pattern),
                    Talent.name_en.ilike(keyword_pattern),
                    Talent.current_title.ilike(keyword_pattern),
                )
            )

        # Fetch one extra to determine if there's a next page
        query = query.limit(page_size + 1)

        result = await self.session.execute(query)
        talents = list(result.scalars().all())

        # Determine next cursor
        next_cursor = None
        if len(talents) > page_size:
            talents = talents[:page_size]
            next_cursor = talents[-1].talent_id

        return talents, next_cursor

    async def get_by_id(
        self, talent_id: int, include_relations: bool = True
    ) -> Talent | None:
        """
        Get talent by ID.

        Args:
            talent_id: Talent ID
            include_relations: If True, load school and role_profile

        Returns:
            Talent instance or None
        """
        query = select(Talent).where(Talent.talent_id == talent_id)

        if include_relations:
            query = query.options(
                selectinload(Talent.school),
                selectinload(Talent.role_profile),
                selectinload(Talent.selected_works),
            )

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_source_id(self, source_record_id: str) -> Talent | None:
        """
        Get talent by source record ID (e.g., OpenAlex ID).

        Args:
            source_record_id: Source record ID

        Returns:
            Talent instance or None
        """
        result = await self.session.execute(
            select(Talent).where(Talent.source_record_id == source_record_id)
        )
        return result.scalar_one_or_none()

    async def get_by_orcid(self, orcid: str) -> Talent | None:
        """
        Get talent by ORCID.

        Args:
            orcid: ORCID identifier

        Returns:
            Talent instance or None
        """
        result = await self.session.execute(
            select(Talent).where(Talent.orcid == orcid)
        )
        return result.scalar_one_or_none()

    async def get_role_profile(self, talent_id: int) -> RoleProfile | None:
        """
        Get role profile for a talent.

        Args:
            talent_id: Talent ID

        Returns:
            RoleProfile instance or None
        """
        result = await self.session.execute(
            select(RoleProfile).where(RoleProfile.talent_id == talent_id)
        )
        return result.scalar_one_or_none()

    async def get_selected_works(
        self, talent_id: int, limit: int = 10
    ) -> list[SelectedWork]:
        """
        Get selected works for a talent.

        Args:
            talent_id: Talent ID
            limit: Maximum number of works to return

        Returns:
            List of SelectedWork instances
        """
        result = await self.session.execute(
            select(SelectedWork)
            .where(SelectedWork.talent_id == talent_id)
            .order_by(SelectedWork.display_order, SelectedWork.citation_count.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search(
        self,
        keyword: str,
        limit: int = 20,
        role_type: str | None = None,
    ) -> list[Talent]:
        """
        Search talents by keyword.

        Args:
            keyword: Search keyword
            limit: Maximum number of results
            role_type: Optional role type filter

        Returns:
            List of matching talents
        """
        keyword_pattern = f"%{keyword}%"

        query = (
            select(Talent)
            .options(selectinload(Talent.school))
            .where(
                Talent.is_visible.is_(True),
                or_(
                    Talent.name.ilike(keyword_pattern),
                    Talent.name_en.ilike(keyword_pattern),
                    Talent.current_title.ilike(keyword_pattern),
                ),
            )
            .order_by(Talent.cited_by_count.desc())
            .limit(limit)
        )

        if role_type:
            query = query.where(Talent.role_type == role_type)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_count_by_role(
        self, school_id: int | None = None
    ) -> dict[str, int]:
        """
        Get talent counts grouped by role type.

        Args:
            school_id: Optional school to filter by

        Returns:
            Dictionary with counts by role type
        """
        query = select(
            Talent.role_type,
            func.count(Talent.talent_id).label("count")
        ).where(Talent.is_visible.is_(True))

        if school_id:
            query = query.where(Talent.school_id == school_id)

        query = query.group_by(Talent.role_type)

        result = await self.session.execute(query)
        counts = {"professor": 0, "student": 0, "graduated": 0, "unknown": 0, "total": 0}

        for row in result.all():
            counts[row.role_type] = row.count
            counts["total"] += row.count

        return counts

    async def get_count_by_school(
        self, country_code: str | None = None
    ) -> dict[int, int]:
        """
        Get talent counts grouped by school.

        Args:
            country_code: Optional country code to filter schools by

        Returns:
            Dictionary mapping school_id to count
        """
        query = select(
            Talent.school_id,
            func.count(Talent.talent_id).label("count")
        ).where(
            Talent.is_visible.is_(True),
            Talent.school_id.isnot(None),
        )

        if country_code:
            query = query.join(School).where(School.country_code == country_code.upper())

        query = query.group_by(Talent.school_id)

        result = await self.session.execute(query)
        return {row.school_id: row.count for row in result.all()}
