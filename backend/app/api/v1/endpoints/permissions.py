"""
User and permission management API endpoints.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import require_admin, require_super_admin, require_user
from app.core.database import get_async_session
from app.models.enums import UserRoleType
from app.repositories.user_repository import UserRepository, UserScopeRepository
from app.schemas.common import SuccessResponse
from app.services.audit_service import AuditService

router = APIRouter(prefix="/users", tags=["User Management"])


# Pydantic models
class UserResponse(BaseModel):
    """User response."""

    user_id: int
    username: str
    email: str
    role: str
    display_name: str | None = None
    department: str | None = None
    is_active: bool
    status: str
    employee_id: str | None = None
    default_view: str = "tech_domain"
    last_login_at: datetime | None = None


class UserListResponse(BaseModel):
    """User list response."""

    items: list[UserResponse]
    total: int
    page: int
    page_size: int


class UserCreateRequest(BaseModel):
    """Create user request."""

    username: str = Field(..., min_length=3, max_length=100)
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=8, max_length=100)
    role: str = Field(default="user")
    display_name: str | None = None
    employee_id: str | None = Field(default=None, pattern=r"^[a-zA-Z]\d{8}$")


class UserUpdateRequest(BaseModel):
    """Update user request."""

    display_name: str | None = None
    department: str | None = None
    role: str | None = None
    is_active: bool | None = None


class ScopeResponse(BaseModel):
    """User scope response."""

    scope_id: int
    user_id: int
    scope_type: str
    scope_value: str
    granted_by: int
    granted_at: datetime
    expires_at: datetime | None = None
    is_active: bool
    notes: str | None = None


class ScopeCreateRequest(BaseModel):
    """Create scope request."""

    user_id: int
    scope_type: str = Field(..., pattern="^(school|country|tech_domain|all)$")
    scope_value: str
    expires_at: datetime | None = None
    notes: str | None = None


class DefaultViewRequest(BaseModel):
    """Update default view request."""

    default_view: str = Field(..., pattern="^(tech_domain|country_school)$")


class SchoolAccessResponse(BaseModel):
    """School access check response."""

    school_id: int
    has_access: bool


class DefaultViewResponse(BaseModel):
    """Default view response."""

    default_view: str


class ScopeListResponse(BaseModel):
    """Scope list response."""

    items: list[ScopeResponse]
    total: int


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
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin),
):
    """List all users (admin only)."""
    repo = UserRepository(session)
    users, total = await repo.list_users(
        role=role,
        is_active=is_active,
        status=status,
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
    current_user: dict = Depends(require_admin),
):
    """List pending approval users (admin only)."""
    repo = UserRepository(session)
    users, total = await repo.list_users(
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
    current_user: dict = Depends(require_admin),
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

    repo = UserRepository(session)

    # Check if username exists
    existing = await repo.get_by_username(data.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    # Check if email exists
    existing = await repo.get_by_email(data.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")

    # Check employee_id uniqueness if provided
    if data.employee_id:
        existing = await repo.get_by_employee_id(data.employee_id)
        if existing:
            raise HTTPException(status_code=400, detail="Employee ID already exists")

    # Create user (admin created users are active by default)
    password_hash = hash_password(data.password)
    user = await repo.create_user_and_commit(
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


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="获取用户详情",
    description="查看用户详情",
)
async def get_user(
    user_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_user),
):
    """Get user details."""
    # Users can only view their own info unless they're admin
    if current_user["user_id"] != user_id and current_user["role"] not in [
        UserRoleType.ADMIN.value,
        UserRoleType.SUPER_ADMIN.value,
    ]:
        raise HTTPException(status_code=403, detail="Access denied")

    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

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


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="更新用户",
    description="更新用户信息",
)
async def update_user(
    request: Request,
    user_id: int,
    data: UserUpdateRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin),
):
    """Update user (admin only)."""
    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update fields
    if data.role is not None:
        # Only super admin can change roles
        if current_user["role"] != UserRoleType.SUPER_ADMIN.value:
            raise HTTPException(status_code=403, detail="Only super admin can change roles")

    user = await repo.update_user_and_commit(
        user_id,
        display_name=data.display_name,
        department=data.department,
        role=data.role,
        is_active=data.is_active,
    )

    await AuditService.log_user_event(
        admin_id=current_user["user_id"],
        operation="update",
        target_user_id=user_id,
        status="success",
        user_ip=client_ip,
        request_id=request_id,
        detail={"updated_fields": [k for k, v in data.model_dump().items() if v is not None]},
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


@router.delete(
    "/{user_id}",
    response_model=SuccessResponse,
    summary="删除/禁用用户",
    description="禁用用户账户",
)
async def deactivate_user(
    request: Request,
    user_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin),
):
    """Deactivate user (admin only)."""
    # Prevent self-deactivation
    if current_user["user_id"] == user_id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")

    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    repo = UserRepository(session)
    success = await repo.deactivate_user_and_commit(user_id)

    if not success:
        raise HTTPException(status_code=404, detail="User not found")

    await AuditService.log_user_event(
        admin_id=current_user["user_id"],
        operation="deactivate",
        target_user_id=user_id,
        status="success",
        user_ip=client_ip,
        request_id=request_id,
    )

    return SuccessResponse(message="User deactivated")


@router.post(
    "/{user_id}/approve",
    response_model=UserResponse,
    summary="审批通过用户注册",
    description="将待审核用户状态设为 active",
)
async def approve_user(
    request: Request,
    user_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_super_admin),
):
    """Approve a pending user registration (admin only)."""
    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    repo = UserRepository(session)
    user = await repo.approve_user_and_commit(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found or not pending approval")

    await AuditService.log_user_event(
        admin_id=current_user["user_id"],
        operation="approve",
        target_user_id=user_id,
        status="success",
        user_ip=client_ip,
        request_id=request_id,
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


@router.post(
    "/{user_id}/reject",
    response_model=UserResponse,
    summary="拒绝用户注册",
    description="将待审核用户状态设为 rejected",
)
async def reject_user(
    request: Request,
    user_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_super_admin),
):
    """Reject a pending user registration (admin only)."""
    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    repo = UserRepository(session)
    user = await repo.reject_user_and_commit(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found or not pending approval")

    await AuditService.log_user_event(
        admin_id=current_user["user_id"],
        operation="reject",
        target_user_id=user_id,
        status="success",
        user_ip=client_ip,
        request_id=request_id,
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


# School Scopes
@router.get(
    "/{user_id}/scopes",
    response_model=ScopeListResponse,
    summary="获取用户权限范围",
    description="查看用户的学校访问权限",
)
async def get_user_scopes(
    user_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin),
):
    """Get user's school scopes (admin only)."""
    scope_repo = UserScopeRepository(session)
    scopes = await scope_repo.get_user_scopes(user_id, active_only=False)

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
    current_user: dict = Depends(require_admin),
):
    """Add school scope to user (admin only)."""
    # Validate user exists
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    scope_repo = UserScopeRepository(session)
    scope = await scope_repo.add_scope_and_commit(
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
    current_user: dict = Depends(require_admin),
):
    """Remove school scope from user (admin only)."""
    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    scope_repo = UserScopeRepository(session)
    success = await scope_repo.remove_scope_and_commit(scope_id)

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


@router.get(
    "/me/scopes/schools",
    response_model=list[int],
    summary="获取当前用户可访问的学校",
    description="返回当前用户有权访问的学校ID列表",
)
async def get_my_accessible_schools(
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_user),
):
    """Get current user's accessible school IDs."""
    scope_repo = UserScopeRepository(session)
    school_ids = await scope_repo.get_accessible_school_ids(current_user["user_id"])
    return school_ids


@router.get(
    "/me/scopes/check/{school_id}",
    response_model=SchoolAccessResponse,
    summary="检查学校访问权限",
    description="检查当前用户是否有权访问指定学校",
)
async def check_school_access(
    school_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_user),
):
    """Check if current user can access a specific school."""
    scope_repo = UserScopeRepository(session)
    has_access = await scope_repo.check_user_has_access(
        current_user["user_id"],
        school_id,
    )

    return SchoolAccessResponse(
        school_id=school_id,
        has_access=has_access,
    )


@router.get(
    "/me/scopes/tech-domains",
    response_model=list[int],
    summary="获取当前用户可访问的技术领域",
    description="返回当前用户有权访问的技术领域ID列表",
)
async def get_my_accessible_tech_domains(
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_user),
):
    """Get current user's accessible tech domain IDs."""
    scope_repo = UserScopeRepository(session)
    tech_domain_ids = await scope_repo.get_accessible_tech_domain_ids(current_user["user_id"])
    return tech_domain_ids


@router.get(
    "/me/scopes/countries",
    response_model=list[str],
    summary="获取当前用户可访问的国家",
    description="返回当前用户有权访问的国家代码列表",
)
async def get_my_accessible_countries(
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_user),
):
    """Get current user's accessible country codes."""
    scope_repo = UserScopeRepository(session)
    country_codes = await scope_repo.get_accessible_country_codes(current_user["user_id"])
    return country_codes


@router.get(
    "/me/default-view",
    response_model=DefaultViewResponse,
    summary="获取当前用户默认视角",
    description="返回用户的默认视角配置",
)
async def get_my_default_view(
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_user),
):
    """Get current user's default view preference."""
    scope_repo = UserScopeRepository(session)
    default_view = await scope_repo.get_user_default_view(current_user["user_id"])
    return DefaultViewResponse(default_view=default_view)


@router.put(
    "/me/default-view",
    response_model=DefaultViewResponse,
    summary="更新当前用户默认视角",
    description="更新用户的默认视角配置",
)
async def update_my_default_view(
    data: DefaultViewRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_user),
):
    """Update current user's default view preference."""
    scope_repo = UserScopeRepository(session)
    success = await scope_repo.update_default_view_and_commit(
        current_user["user_id"],
        data.default_view,
    )

    if not success:
        raise HTTPException(status_code=404, detail="User not found")

    return DefaultViewResponse(default_view=data.default_view)
