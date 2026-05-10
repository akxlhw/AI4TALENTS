"""Base talent repository with core CRUD and list operations."""

from __future__ import annotations

import logging

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.academic.models.school import School
from app.domains.academic.models.talent import RoleProfile, SelectedWork, Talent
from app.domains.academic.models.tech_domain import TalentTechTag, TechDirection, TechDomain
from app.domains.academic.schemas.filters import PaginationParams, TalentFilterParams

logger = logging.getLogger(__name__)


class BaseTalentRepository:
    """Repository for core Talent CRUD and list queries."""

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

        This method supports both individual parameters (for backward compatibility)
        and can be called with TalentFilterParams.

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
        # Create filter params from individual args
        filters = TalentFilterParams(
            school_id=school_id,
            country_code=country_code,
            role_type=role_type,
            min_works=min_works,
            min_citations=min_citations,
            keyword=keyword,
            visible_only=visible_only,
        )
        pagination = PaginationParams(page=page, page_size=page_size)

        return await self.get_list_with_params(filters, pagination)

    async def get_list_with_params(
        self,
        filters: TalentFilterParams,
        pagination: PaginationParams,
    ) -> tuple[list[Talent], int]:
        """
        Get paginated list of talents with filter params object.

        Args:
            filters: TalentFilterParams object
            pagination: PaginationParams object

        Returns:
            Tuple of (list of talents, total count)
        """
        query = (
            select(Talent)
            .options(
                selectinload(Talent.school),
                selectinload(Talent.education_school),
                selectinload(Talent.company_school),
            )
            .order_by(Talent.cited_by_count.desc())
        )

        # Apply filters using helper
        query = self._apply_talent_filters(query, filters)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        query = query.offset(pagination.offset).limit(pagination.page_size)

        result = await self.session.execute(query)
        talents = list(result.scalars().all())

        return talents, total

    def _apply_talent_filters(self, query, filters: TalentFilterParams):
        """Apply TalentFilterParams to a query. Reusable across methods."""
        if filters.visible_only:
            query = query.where(Talent.is_visible.is_(True))

        if filters.school_id:
            # Filter by school_id using OR logic (matches education or company institution)
            query = query.where(
                or_(
                    Talent.school_id == filters.school_id,
                    Talent.education_school_id == filters.school_id,
                    Talent.company_school_id == filters.school_id,
                )
            )

        if filters.country_code:
            # Join with explicit condition due to multiple FKs between Talent and School
            query = query.join(School, Talent.school_id == School.school_id).where(
                School.country_code == filters.country_code.upper()
            )

        if filters.role_type:
            query = query.where(Talent.role_type == filters.role_type)

        if filters.min_works is not None:
            query = query.where(Talent.works_count >= filters.min_works)

        if filters.min_citations is not None:
            query = query.where(Talent.cited_by_count >= filters.min_citations)

        if filters.keyword:
            keyword_pattern = f"%{filters.keyword}%"
            query = query.where(
                or_(
                    Talent.name.ilike(keyword_pattern),
                    Talent.name_en.ilike(keyword_pattern),
                    Talent.current_title.ilike(keyword_pattern),
                )
            )

        return query

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
        # Create filter params from args
        filters = TalentFilterParams(
            school_id=school_id,
            country_code=country_code,
            role_type=role_type,
            min_works=min_works,
            min_citations=min_citations,
            keyword=keyword,
            visible_only=visible_only,
        )

        return await self.get_list_by_cursor_with_params(cursor, page_size, filters)

    async def get_list_by_cursor_with_params(
        self,
        cursor: int | None,
        page_size: int,
        filters: TalentFilterParams,
    ) -> tuple[list[Talent], int | None]:
        """Cursor pagination with filter params object."""
        query = (
            select(Talent)
            .options(
                selectinload(Talent.school),
                selectinload(Talent.education_school),
                selectinload(Talent.company_school),
            )
            .order_by(Talent.talent_id.desc())
        )

        # Apply cursor filter
        if cursor is not None:
            query = query.where(Talent.talent_id < cursor)

        # Apply filters using helper
        query = self._apply_talent_filters(query, filters)

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

    async def get_by_id(self, talent_id: int, include_relations: bool = True) -> Talent | None:
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
                selectinload(Talent.education_school),
                selectinload(Talent.company_school),
                selectinload(Talent.role_profile),
                selectinload(Talent.selected_works),
            )

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_talent_tech_tags(self, talent_id: int) -> list[tuple]:
        """
        Get tech tags for a talent with domain and direction info.

        Args:
            talent_id: Talent ID

        Returns:
            List of tuples (TalentTechTag, TechDomain, TechDirection)
        """
        result = await self.session.execute(
            select(TalentTechTag, TechDomain, TechDirection)
            .join(TechDomain, TalentTechTag.tech_domain_id == TechDomain.tech_domain_id)
            .outerjoin(
                TechDirection, TalentTechTag.tech_direction_id == TechDirection.tech_direction_id
            )
            .where(TalentTechTag.talent_id == talent_id)
        )
        return result.fetchall()

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
        result = await self.session.execute(select(Talent).where(Talent.orcid == orcid))
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

    async def get_selected_works(self, talent_id: int, limit: int = 10) -> list[SelectedWork]:
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

    async def get_count_by_role(self, school_id: int | None = None) -> dict[str, int]:
        """
        Get talent counts grouped by role type.

        Args:
            school_id: Optional school to filter by

        Returns:
            Dictionary with counts by role type
        """
        query = select(Talent.role_type, func.count(Talent.talent_id).label("count")).where(
            Talent.is_visible.is_(True)
        )

        if school_id:
            query = query.where(Talent.school_id == school_id)

        query = query.group_by(Talent.role_type)

        result = await self.session.execute(query)
        counts = {"professor": 0, "student": 0, "graduated": 0, "unknown": 0, "total": 0}

        for row in result.all():
            counts[row.role_type] = row.count
            counts["total"] += row.count

        return counts

    async def get_count_by_school(self, country_code: str | None = None) -> dict[int, int]:
        """
        Get talent counts grouped by school.

        Args:
            country_code: Optional country code to filter schools by

        Returns:
            Dictionary mapping school_id to count
        """
        query = select(Talent.school_id, func.count(Talent.talent_id).label("count")).where(
            Talent.is_visible.is_(True),
            Talent.school_id.isnot(None),
        )

        if country_code:
            query = query.join(School).where(School.country_code == country_code.upper())

        query = query.group_by(Talent.school_id)

        result = await self.session.execute(query)
        return {row.school_id: row.count for row in result.all()}
