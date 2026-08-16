"""
User administration endpoints (list/pending/create).

Split from user_admin.py; routes keep the original /users prefix.
Registered before user_admin_detail so that /pending precedes /{user_id}.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.shared.api.auth import require_super_admin
from app.domains.shared.models.enums import UserRoleType
from app.domains.shared.schemas.user_management import (
    UserCreateRequest,
    UserListResponse,
    UserResponse,
)
from app.domains.shared.services.audit_service import AuditService
from app.domains.shared.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["User Management"])


@router.get(
    "",
    response_model=UserListResponse,
    summary="获取用户列表",
    description="管理员查看所有用户列表",
)
async def list_users(
    role: str | None = Query(None, description="按角色筛选"),
    is_active: bool | None = Query(None, description="按状态筛选"),
    status: str | None = Query(None, description="按账户状态筛选"),
    created_after: datetime | None = Query(None, description="注册时间起"),
    created_before: datetime | None = Query(None, description="注册时间止"),
    sort_by: str = Query("created_at", description="排序字段: created_at, last_login_at, username"),
    sort_order: str = Query("desc", description="排序方向: asc, desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_super_admin),
):
    """List all users (admin only)."""
    service = UserService(session)
    users, total = await service.list_users(
        role=role,
        is_active=is_active,
        status=status,
        created_after=created_after,
        created_before=created_before,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )

    items = [
        UserResponse(
            user_id=u.user_id,
            username=u.username,
            email=u.email,
            role=u.role_type,
            display_name=u.display_name,
            department=u.department,
            is_active=u.is_active,
            status=u.status,
            employee_id=u.employee_id,
            default_view=u.default_view,
            last_login_at=u.last_login_at,
        )
        for u in users
    ]

    return UserListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/pending",
    response_model=UserListResponse,
    summary="获取待审核用户列表",
    description="获取状态为 pending_approval 的用户列表",
)
async def list_pending_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_super_admin),
):
    """List pending approval users (admin only)."""
    service = UserService(session)
    users, total = await service.list_users(
        status="pending_approval",
        page=page,
        page_size=page_size,
    )

    items = [
        UserResponse(
            user_id=u.user_id,
            username=u.username,
            email=u.email,
            role=u.role_type,
            display_name=u.display_name,
            department=u.department,
            is_active=u.is_active,
            status=u.status,
            employee_id=u.employee_id,
            default_view=u.default_view,
            last_login_at=u.last_login_at,
        )
        for u in users
    ]

    return UserListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "",
    response_model=UserResponse,
    summary="创建用户",
    description="管理员创建新用户",
)
async def create_user(
    request: Request,
    data: UserCreateRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_super_admin),
):
    """Create a new user (admin only)."""
    from app.core.auth import hash_password

    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    # Validate role
    valid_roles = [UserRoleType.USER.value, UserRoleType.ADMIN.value]
    if current_user["role"] == UserRoleType.SUPER_ADMIN.value:
        valid_roles.append(UserRoleType.SUPER_ADMIN.value)

    if data.role not in valid_roles:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Must be one of: {valid_roles}",
        )

    service = UserService(session)

    # Check if username exists
    existing = await service.get_by_username(data.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    # Check if email exists
    existing = await service.get_by_email(data.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")

    # Check employee_id uniqueness if provided
    if data.employee_id:
        existing = await service.get_by_employee_id(data.employee_id)
        if existing:
            raise HTTPException(status_code=400, detail="Employee ID already exists")

    # Create user (admin created users are active by default)
    password_hash = hash_password(data.password)
    user = await service.create_user_and_commit(
        username=data.username,
        email=data.email,
        password_hash=password_hash,
        role=data.role,
        display_name=data.display_name,
        employee_id=data.employee_id,
        is_active=True,
        status="active",
    )

    await AuditService.log_user_event(
        admin_id=current_user["user_id"],
        operation="create",
        target_user_id=user.user_id,
        status="success",
        user_ip=client_ip,
        request_id=request_id,
        detail={"employee_id": data.employee_id, "role": data.role},
    )

    return UserResponse(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        role=user.role_type,
        display_name=user.display_name,
        department=user.department,
        is_active=user.is_active,
        status=user.status,
        employee_id=user.employee_id,
        default_view=user.default_view,
        last_login_at=user.last_login_at,
    )
