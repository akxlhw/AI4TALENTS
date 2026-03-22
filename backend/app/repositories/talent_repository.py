"""
Repository for talent operations.
"""
from typing import List, Optional

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.talent import Talent, RoleProfile, SelectedWork
from app.models.school import School


class TalentRepository:
    """Repository for Talent queries."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_list(
        self,
        school_id: Optional[int] = None,
        country_id: Optional[int] = None,
        role_type: Optional[str] = None,
        min_works: Optional[int] = None,
        min_citations: Optional[int] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        visible_only: bool = True,
    ) -> tuple[List[Talent], int]:
        """
        Get paginated list of talents with filters.

        Args:
            school_id: Filter by school ID
            country_id: Filter by country ID (via school)
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
            query = query.where(Talent.is_visible == True)

        if school_id:
            query = query.where(Talent.school_id == school_id)

        if country_id:
            # Join with school to filter by country
            query = query.join(School).where(School.country_id == country_id)

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

    async def get_by_id(
        self, talent_id: int, include_relations: bool = True
    ) -> Optional[Talent]:
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

    async def get_by_source_id(self, source_record_id: str) -> Optional[Talent]:
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

    async def get_by_orcid(self, orcid: str) -> Optional[Talent]:
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

    async def get_role_profile(self, talent_id: int) -> Optional[RoleProfile]:
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
    ) -> List[SelectedWork]:
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
        role_type: Optional[str] = None,
    ) -> List[Talent]:
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
                Talent.is_visible == True,
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
        self, school_id: Optional[int] = None
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
        ).where(Talent.is_visible == True)

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
        self, country_id: Optional[int] = None
    ) -> dict[int, int]:
        """
        Get talent counts grouped by school.

        Args:
            country_id: Optional country to filter schools by

        Returns:
            Dictionary mapping school_id to count
        """
        query = select(
            Talent.school_id,
            func.count(Talent.talent_id).label("count")
        ).where(
            Talent.is_visible == True,
            Talent.school_id.isnot(None),
        )

        if country_id:
            query = query.join(School).where(School.country_id == country_id)

        query = query.group_by(Talent.school_id)

        result = await self.session.execute(query)
        return {row.school_id: row.count for row in result.all()}
