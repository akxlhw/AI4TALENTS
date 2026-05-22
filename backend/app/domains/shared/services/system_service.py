"""System-level service for health checks and infrastructure concerns.

Thin service layer that wraps SystemRepository to satisfy the
API -> Service -> Repository architecture rule.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.shared.repositories.system_repository import SystemRepository


class SystemService:
    """Service for system-level operations."""

    @staticmethod
    async def health_check_db(session: AsyncSession) -> bool:
        """Check database connectivity.

        Args:
            session: An active async SQLAlchemy session.

        Returns:
            True if the database responds correctly.
        """
        return await SystemRepository.health_check_db(session)
