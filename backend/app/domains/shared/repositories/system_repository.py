"""System-level repository for health checks and cross-cutting concerns.

Encapsulates direct SQL / raw DB operations that do not belong in API routes.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class SystemRepository:
    """Repository for system-level database operations."""

    @staticmethod
    async def health_check_db(session: AsyncSession) -> bool:
        """Check database connectivity by executing ``SELECT 1``.

        Args:
            session: An active async SQLAlchemy session.

        Returns:
            True if the database responds with 1, False otherwise.
        """
        result = await session.execute(text("SELECT 1"))
        return result.scalar() == 1
