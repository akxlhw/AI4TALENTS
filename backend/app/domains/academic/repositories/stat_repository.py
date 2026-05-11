"""
Repository for statistics operations.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.academic.models.school import School
from app.domains.academic.models.statistics import OverviewStatSnapshot, SchoolStatSnapshot
from app.domains.academic.models.talent import Talent
from app.domains.academic.models.tech_domain import TechDirection, TechDomain


class StatisticsRepository:
    """Repository for statistics queries."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_active_overview_stats(self) -> OverviewStatSnapshot | None:
        """
        Get the active overview statistics snapshot.

        Returns:
            The active OverviewStatSnapshot or None
        """
        result = await self.session.execute(
            select(OverviewStatSnapshot)
            .where(OverviewStatSnapshot.is_active == 1)
            .order_by(OverviewStatSnapshot.snapshot_id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_overview_stats_by_version(self, version: str) -> OverviewStatSnapshot | None:
        """
        Get overview statistics by version.

        Args:
            version: Statistics version string

        Returns:
            OverviewStatSnapshot or None
        """
        result = await self.session.execute(
            select(OverviewStatSnapshot).where(OverviewStatSnapshot.stat_version == version)
        )
        return result.scalar_one_or_none()

    async def get_school_stats(self, school_id: int) -> SchoolStatSnapshot | None:
        """
        Get the active statistics snapshot for a school.

        Args:
            school_id: School ID

        Returns:
            SchoolStatSnapshot or None
        """
        result = await self.session.execute(
            select(SchoolStatSnapshot)
            .where(
                SchoolStatSnapshot.school_id == school_id,
                SchoolStatSnapshot.is_active == 1,
            )
            .order_by(SchoolStatSnapshot.snapshot_id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_all_school_stats(self) -> list[SchoolStatSnapshot]:
        """
        Get all active school statistics snapshots.

        Returns:
            List of SchoolStatSnapshot
        """
        result = await self.session.execute(
            select(SchoolStatSnapshot)
            .where(SchoolStatSnapshot.is_active == 1)
            .order_by(SchoolStatSnapshot.school_id)
        )
        return list(result.scalars().all())

    async def get_country_count(self) -> int:
        """
        Get count of distinct countries with visible talents.

        Returns:
            Number of countries
        """
        result = await self.session.execute(
            select(func.count(func.distinct(School.country_code)))
            .join(Talent, Talent.school_id == School.school_id)
            .where(Talent.is_visible.is_(True))
            .where(School.country_code.isnot(None))
        )
        return result.scalar() or 0

    async def get_tech_domain_count(self) -> int:
        """
        Get count of enabled tech domains.

        Returns:
            Number of tech domains
        """
        result = await self.session.execute(
            select(func.count(TechDomain.tech_domain_id)).where(TechDomain.is_enabled.is_(True))
        )
        return result.scalar() or 0

    async def get_tech_direction_count(self) -> int:
        """
        Get count of enabled tech directions.

        Returns:
            Number of tech directions
        """
        result = await self.session.execute(
            select(func.count(TechDirection.tech_direction_id)).where(
                TechDirection.is_enabled.is_(True)
            )
        )
        return result.scalar() or 0

    async def check_database_connection(self) -> bool:
        """
        Check database connection by executing a simple query.

        Returns:
            True if connection is healthy, False otherwise
        """
        from sqlalchemy import text

        try:
            result = await self.session.execute(text("SELECT 1"))
            return result.scalar() == 1
        except SQLAlchemyError:
            return False
