"""
User scope management endpoints (school/country/tech_domain grants).

Split from permissions.py; routes keep the original /users prefix.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.shared.api.auth import require_super_admin
from app.domains.shared.schemas.common import SuccessResponse
from app.domains.shared.schemas.user_management import (
    ScopeCreateRequest,
    ScopeListResponse,
    ScopeResponse,
)
from app.domains.shared.services.audit_service import AuditService
from app.domains.shared.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["User Management"])


@router.get(
    "/{user_id}/scopes",
    response_model=ScopeListResponse,
    summary="获取用户权限范围",
    description="查看用户的学校访问权限",
)
async def get_user_scopes(
    user_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_super_admin),
):
    """Get user's school scopes (admin only)."""
    service = UserService(session)
    scopes = await service.get_user_scopes(user_id, active_only=False)

    items = [
        ScopeResponse(
            scope_id=s.scope_id,
            user_id=s.user_id,
            scope_type=s.scope_type,
            scope_value=s.scope_value,
            granted_by=s.granted_by,
            granted_at=s.granted_at,
            expires_at=s.expires_at,
            is_active=s.is_active,
            notes=s.notes,
        )
        for s in scopes
    ]

    return ScopeListResponse(items=items, total=len(items))


@router.post(
    "/{user_id}/scopes",
    response_model=ScopeResponse,
    summary="添加用户权限",
    description="为用户添加学校访问权限",
)
async def add_user_scope(
    request: Request,
    user_id: int,
    data: ScopeCreateRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_super_admin),
):
    """Add school scope to user (admin only)."""
    service = UserService(session)

    # Validate user exists
    user = await service.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    scope = await service.add_scope_and_commit(
        user_id=user_id,
        scope_type=data.scope_type,
        scope_value=data.scope_value,
        granted_by=current_user["user_id"],
        expires_at=data.expires_at,
        notes=data.notes,
    )

    await AuditService.log_scope_event(
        admin_id=current_user["user_id"],
        operation="grant_scope",
        target_user_id=user_id,
        scope_type=data.scope_type,
        status="success",
        user_ip=client_ip,
        request_id=request_id,
        detail={"scope_value": data.scope_value},
    )

    return ScopeResponse(
        scope_id=scope.scope_id,
        user_id=scope.user_id,
        scope_type=scope.scope_type,
        scope_value=scope.scope_value,
        granted_by=scope.granted_by,
        granted_at=scope.granted_at,
        expires_at=scope.expires_at,
        is_active=scope.is_active,
        notes=scope.notes,
    )


@router.delete(
    "/{user_id}/scopes/{scope_id}",
    response_model=SuccessResponse,
    summary="移除用户权限",
    description="移除用户的学校访问权限",
)
async def remove_user_scope(
    request: Request,
    user_id: int,
    scope_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_super_admin),
):
    """Remove school scope from user (admin only)."""
    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    service = UserService(session)
    success = await service.remove_scope_and_commit(scope_id)

    if not success:
        raise HTTPException(status_code=404, detail="Scope not found")

    await AuditService.log_scope_event(
        admin_id=current_user["user_id"],
        operation="revoke_scope",
        target_user_id=user_id,
        scope_type=None,
        status="success",
        user_ip=client_ip,
        request_id=request_id,
        detail={"scope_id": scope_id},
    )

    return SuccessResponse(message="Scope removed")
