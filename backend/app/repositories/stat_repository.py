"""
Repository for statistics operations.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.statistics import OverviewStatSnapshot, SchoolStatSnapshot


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

    async def get_overview_stats_by_version(
        self, version: str
    ) -> OverviewStatSnapshot | None:
        """
        Get overview statistics by version.

        Args:
            version: Statistics version string

        Returns:
            OverviewStatSnapshot or None
        """
        result = await self.session.execute(
            select(OverviewStatSnapshot).where(
                OverviewStatSnapshot.stat_version == version
            )
        )
        return result.scalar_one_or_none()

    async def get_school_stats(
        self, school_id: int
    ) -> SchoolStatSnapshot | None:
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
