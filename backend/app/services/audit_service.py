"""
Audit service for logging user operations.
Uses an independent async session to avoid coupling with the main business transaction.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.core.database import async_session_factory
from app.core.logging_config import get_logger
from app.repositories.audit_repository import AuditRepository

logger = get_logger(__name__)


class AuditService:
    """Service for writing audit logs using an independent session."""

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
