"""
Repository for audit log operations.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditOperationLog


class AuditRepository:
    """Repository for AuditOperationLog queries."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_logs(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        user_id: int | None = None,
        event_type: str | None = None,
        resource_type: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[AuditOperationLog], int]:
        """
        Get paginated audit logs with filters.

        Args:
            start_time: Filter by start time
            end_time: Filter by end time
            user_id: Filter by user ID
            event_type: Filter by event type
            resource_type: Filter by resource type
            page: Page number
            page_size: Items per page

        Returns:
            Tuple of (list of logs, total count)
        """
        query = select(AuditOperationLog)

        # Apply filters
        filters = []
        if start_time:
            filters.append(AuditOperationLog.event_time >= start_time)
        if end_time:
            filters.append(AuditOperationLog.event_time <= end_time)
        if user_id:
            filters.append(AuditOperationLog.user_id == user_id)
        if event_type:
            filters.append(AuditOperationLog.event_type == event_type)
        if resource_type:
            filters.append(AuditOperationLog.resource_type == resource_type)

        if filters:
            query = query.where(and_(*filters))

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Paginate
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size).order_by(AuditOperationLog.event_time.desc())

        result = await self.session.execute(query)
        logs = list(result.scalars().all())

        return logs, total

    async def get_event_types(self) -> list[str]:
        """
        Get distinct event types.

        Returns:
            List of event types
        """
        result = await self.session.execute(select(AuditOperationLog.event_type).distinct())
        return [row[0] for row in result.fetchall()]

    async def get_resource_types(self) -> list[str]:
        """
        Get distinct resource types.

        Returns:
            List of resource types (excluding None)
        """
        result = await self.session.execute(select(AuditOperationLog.resource_type).distinct())
        return [row[0] for row in result.fetchall() if row[0]]
