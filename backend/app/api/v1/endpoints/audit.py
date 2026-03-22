"""
Audit log API endpoints.
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from pydantic import BaseModel

from app.core.database import get_async_session
from app.api.v1.endpoints.auth import require_admin
from app.models.audit import AuditOperationLog


router = APIRouter(prefix="/audit", tags=["Audit Logs"])


# Pydantic models
class AuditLogResponse(BaseModel):
    """Audit log response."""
    log_id: int
    event_time: datetime
    user_id: Optional[int]
    user_ip: Optional[str]
    event_type: str
    event_subtype: Optional[str]
    resource_type: Optional[str]
    resource_id: Optional[str]
    operation: str
    status: str
    error_message: Optional[str]


class AuditLogListResponse(BaseModel):
    """Audit log list response."""
    items: List[AuditLogResponse]
    total: int
    page: int
    page_size: int


@router.get(
    "/logs",
    response_model=AuditLogListResponse,
    summary="获取审计日志",
    description="管理员查看系统操作日志",
)
async def get_audit_logs(
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    user_id: Optional[int] = Query(None, description="用户ID"),
    event_type: Optional[str] = Query(None, description="事件类型"),
    resource_type: Optional[str] = Query(None, description="资源类型"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin),
):
    """
    Get audit logs (admin only).

    Supports filtering by:
    - start_time / end_time: Time range
    - user_id: Filter by user
    - event_type: Filter by event type (authentication, authorization, data_operation)
    - resource_type: Filter by resource type (user, talent, school)
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
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(AuditOperationLog.event_time.desc())

    result = await session.execute(query)
    logs = list(result.scalars().all())

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
    summary="获取事件类型列表",
    description="获取所有事件类型",
)
async def get_event_types(
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin),
):
    """Get distinct event types."""
    result = await session.execute(
        select(AuditOperationLog.event_type).distinct()
    )
    types = [row[0] for row in result.fetchall()]
    return {"event_types": types}


@router.get(
    "/resource-types",
    summary="获取资源类型列表",
    description="获取所有资源类型",
)
async def get_resource_types(
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin),
):
    """Get distinct resource types."""
    result = await session.execute(
        select(AuditOperationLog.resource_type).distinct()
    )
    types = [row[0] for row in result.fetchall() if row[0]]
    return {"resource_types": types}
