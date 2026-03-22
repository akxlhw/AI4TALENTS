"""
Repository for country operations.
"""
from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.country import Country
from app.models.school import School
from app.models.talent import Talent


class CountryRepository:
    """Repository for Country queries."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self, active_only: bool = True) -> List[Country]:
        """
        Get all countries.

        Args:
            active_only: If True, only return active countries

        Returns:
            List of Country instances
        """
        query = select(Country).order_by(Country.sort_order, Country.country_id)

        if active_only:
            query = query.where(Country.is_active == True)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, country_id: int) -> Optional[Country]:
        """
        Get country by ID.

        Args:
            country_id: Country ID

        Returns:
            Country instance or None
        """
        result = await self.session.execute(
            select(Country).where(Country.country_id == country_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, country_code: str) -> Optional[Country]:
        """
        Get country by code.

        Args:
            country_code: Country code (e.g., 'US', 'CN')

        Returns:
            Country instance or None
        """
        result = await self.session.execute(
            select(Country).where(Country.country_code == country_code.upper())
        )
        return result.scalar_one_or_none()

    async def get_with_school_counts(self) -> List[dict]:
        """
        Get all countries with school counts.

        Returns:
            List of dictionaries with country info and school count
        """
        # Query to get countries with school counts
        query = (
            select(
                Country.country_id,
                Country.country_code,
                Country.country_name_cn,
                Country.country_name_en,
                func.count(School.school_id).label("school_count"),
            )
            .outerjoin(School, Country.country_id == School.country_id)
            .where(Country.is_active == True)
            .group_by(Country.country_id)
            .order_by(Country.sort_order, Country.country_id)
        )

        result = await self.session.execute(query)
        rows = result.all()

        return [
            {
                "country_id": row.country_id,
                "country_code": row.country_code,
                "country_name_cn": row.country_name_cn,
                "country_name_en": row.country_name_en,
                "school_count": row.school_count,
            }
            for row in rows
        ]

    async def get_professor_count_by_country(self, country_id: int) -> int:
        """
        Get total professor count for a country.

        Args:
            country_id: Country ID

        Returns:
            Total professor count
        """
        # Sum professor counts from all schools in this country
        result = await self.session.execute(
            select(func.sum(School.professor_count)).where(
                School.country_id == country_id
            )
        )
        count = result.scalar()
        return count or 0
