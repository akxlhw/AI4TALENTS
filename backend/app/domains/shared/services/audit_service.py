"""
Audit service for logging user operations and querying audit logs.
Uses an independent async session to avoid coupling with the main business transaction.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.core.logging_config import get_logger
from app.domains.shared.repositories.audit_repository import AuditRepository

logger = get_logger(__name__)


class AuditService:
    """Service for writing and reading audit logs."""

    # ---- Write operations (use independent session) ----

    @staticmethod
    async def _write_log(**kwargs: Any) -> None:
        """Internal helper: open a new session and write the log."""
        try:
            async with async_session_factory() as session:
                repo = AuditRepository(session)
                await repo.create_log(**kwargs)
        except Exception as e:
            # Audit failure must not break the main business flow
            logger.warning(f"Failed to write audit log: {e}")

    @classmethod
    async def log_auth_event(
        cls,
        user_id: int | None,
        operation: str,
        status: str,
        user_ip: str | None = None,
        request_id: str | None = None,
        detail: dict | None = None,
        error_message: str | None = None,
    ) -> None:
        """Log an authentication-related event."""
        await cls._write_log(
            event_time=datetime.now(),
            user_id=user_id,
            user_ip=user_ip,
            event_type="authentication",
            event_subtype=None,
            resource_type="user",
            resource_id=str(user_id) if user_id else None,
            operation=operation,
            operation_detail=detail,
            status=status,
            error_message=error_message,
            request_id=request_id,
            user_agent=None,
        )

    @classmethod
    async def log_user_event(
        cls,
        admin_id: int | None,
        operation: str,
        target_user_id: int | None,
        status: str,
        user_ip: str | None = None,
        request_id: str | None = None,
        detail: dict | None = None,
        error_message: str | None = None,
    ) -> None:
        """Log a user-management event (create, update, delete, approve, reject)."""
        await cls._write_log(
            event_time=datetime.now(),
            user_id=admin_id,
            user_ip=user_ip,
            event_type="authorization",
            event_subtype="user_management",
            resource_type="user",
            resource_id=str(target_user_id) if target_user_id else None,
            operation=operation,
            operation_detail=detail,
            status=status,
            error_message=error_message,
            request_id=request_id,
            user_agent=None,
        )

    @classmethod
    async def log_scope_event(
        cls,
        admin_id: int | None,
        operation: str,
        target_user_id: int | None,
        scope_type: str | None,
        status: str,
        user_ip: str | None = None,
        request_id: str | None = None,
        detail: dict | None = None,
        error_message: str | None = None,
    ) -> None:
        """Log a scope grant/revoke event."""
        await cls._write_log(
            event_time=datetime.now(),
            user_id=admin_id,
            user_ip=user_ip,
            event_type="authorization",
            event_subtype="scope_management",
            resource_type="user_scope",
            resource_id=str(target_user_id) if target_user_id else None,
            operation=operation,
            operation_detail=detail,
            status=status,
            error_message=error_message,
            request_id=request_id,
            user_agent=None,
        )

    @classmethod
    async def log_data_operation(
        cls,
        user_id: int | None,
        operation: str,
        resource_type: str,
        resource_id: str | None,
        status: str,
        user_ip: str | None = None,
        request_id: str | None = None,
        detail: dict | None = None,
        error_message: str | None = None,
        event_subtype: str = "export",
    ) -> None:
        """Log a data operation event (export/import/etc.).

        ``event_subtype`` defaults to ``"export"`` for backward compatibility;
        callers performing imports should pass ``event_subtype="import"`` so the
        two flows can be distinguished in the audit log.
        """
        await cls._write_log(
            event_time=datetime.now(),
            user_id=user_id,
            user_ip=user_ip,
            event_type="data_operation",
            event_subtype=event_subtype,
            resource_type=resource_type,
            resource_id=resource_id,
            operation=operation,
            operation_detail=detail,
            status=status,
            error_message=error_message,
            request_id=request_id,
            user_agent=None,
        )

    # ---- Read operations (use caller's session) ----

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AuditRepository(session)

    async def list_logs(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        user_id: int | None = None,
        event_type: str | None = None,
        resource_type: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ):
        """Get paginated audit logs with filters."""
        return await self.repo.list_logs(
            start_time=start_time,
            end_time=end_time,
            user_id=user_id,
            event_type=event_type,
            resource_type=resource_type,
            page=page,
            page_size=page_size,
        )

    async def get_event_types(self) -> list[str]:
        """Get distinct event types."""
        return await self.repo.get_event_types()

    async def get_resource_types(self) -> list[str]:
        """Get distinct resource types."""
        return await self.repo.get_resource_types()
