"""
Audit log API endpoints.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.shared.api.auth import require_super_admin
from app.domains.shared.services.audit_service import AuditService

router = APIRouter(prefix="/audit", tags=["Audit Logs"])


# Pydantic models
class AuditLogResponse(BaseModel):
    """Audit log response."""

    log_id: int
    event_time: datetime
    user_id: int | None
    user_ip: str | None
    event_type: str
    event_subtype: str | None
    resource_type: str | None
    resource_id: str | None
    operation: str
    status: str
    error_message: str | None


class AuditLogListResponse(BaseModel):
    """Audit log list response."""

    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int


class EventTypesResponse(BaseModel):
    """Event types response."""

    event_types: list[str]


class ResourceTypesResponse(BaseModel):
    """Resource types response."""

    resource_types: list[str]


@router.get(
    "/logs",
    response_model=AuditLogListResponse,
    summary="获取审计日志",
    description="管理员查看系统操作日志",
)
async def get_audit_logs(
    start_time: datetime | None = Query(None, description="开始时间"),
    end_time: datetime | None = Query(None, description="结束时间"),
    user_id: int | None = Query(None, description="用户ID"),
    event_type: str | None = Query(None, description="事件类型"),
    resource_type: str | None = Query(None, description="资源类型"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_super_admin),
):
    """
    Get audit logs (admin only).

    Supports filtering by:
    - start_time / end_time: Time range
    - user_id: Filter by user
    - event_type: Filter by event type (authentication, authorization, data_operation)
    - resource_type: Filter by resource type (user, talent, school)
    """
    service = AuditService(session)
    logs, total = await service.list_logs(
        start_time=start_time,
        end_time=end_time,
        user_id=user_id,
        event_type=event_type,
        resource_type=resource_type,
        page=page,
        page_size=page_size,
    )

    items = [
        AuditLogResponse(
            log_id=log.log_id,
            event_time=log.event_time,
            user_id=log.user_id,
            user_ip=log.user_ip,
            event_type=log.event_type,
            event_subtype=log.event_subtype,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            operation=log.operation,
            status=log.status,
            error_message=log.error_message,
        )
        for log in logs
    ]

    return AuditLogListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/event-types",
    response_model=EventTypesResponse,
    summary="获取事件类型列表",
    description="获取所有事件类型",
)
async def get_event_types(
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_super_admin),
):
    """Get distinct event types."""
    service = AuditService(session)
    types = await service.get_event_types()
    return EventTypesResponse(event_types=types)


@router.get(
    "/resource-types",
    response_model=ResourceTypesResponse,
    summary="获取资源类型列表",
    description="获取所有资源类型",
)
async def get_resource_types(
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_super_admin),
):
    """Get distinct resource types."""
    service = AuditService(session)
    types = await service.get_resource_types()
    return ResourceTypesResponse(resource_types=types)
