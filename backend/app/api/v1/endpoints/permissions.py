"""
User and permission management API endpoints.
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.core.database import get_async_session
from app.api.v1.endpoints.auth import require_user, require_admin, require_super_admin
from app.repositories.user_repository import UserRepository, UserScopeRepository
from app.models.enums import UserRoleType


router = APIRouter(prefix="/users", tags=["User Management"])


# Pydantic models
class UserResponse(BaseModel):
    """User response."""
    user_id: int
    username: str
    email: str
    role: str
    display_name: Optional[str] = None
    department: Optional[str] = None
    is_active: bool
    last_login_at: Optional[datetime] = None


class UserListResponse(BaseModel):
    """User list response."""
    items: List[UserResponse]
    total: int
    page: int
    page_size: int


class UserCreateRequest(BaseModel):
    """Create user request."""
    username: str = Field(..., min_length=3, max_length=100)
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=8, max_length=100)
    role: str = Field(default="user")
    display_name: Optional[str] = None


class UserUpdateRequest(BaseModel):
    """Update user request."""
    display_name: Optional[str] = None
    department: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class ScopeResponse(BaseModel):
    """User scope response."""
    scope_id: int
    user_id: int
    scope_type: str
    scope_value: str
    granted_by: int
    granted_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool
    notes: Optional[str] = None


class ScopeCreateRequest(BaseModel):
    """Create scope request."""
    user_id: int
    scope_type: str = Field(..., pattern="^(school|country|all)$")
    scope_value: str
    expires_at: Optional[datetime] = None
    notes: Optional[str] = None


class ScopeListResponse(BaseModel):
    """Scope list response."""
    items: List[ScopeResponse]
    total: int


@router.get(
    "",
    response_model=UserListResponse,
    summary="获取用户列表",
    description="管理员查看所有用户列表",
)
async def list_users(
    role: Optional[str] = Query(None, description="按角色筛选"),
    is_active: Optional[bool] = Query(None, description="按状态筛选"),
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
    data: UserCreateRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin),
):
    """Create a new user (admin only)."""
    from app.core.auth import hash_password

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

    # Create user
    password_hash = hash_password(data.password)
    user = await repo.create_user(
        username=data.username,
        email=data.email,
        password_hash=password_hash,
        role=data.role,
        display_name=data.display_name,
    )

    await session.commit()

    return UserResponse(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        role=user.role_type,
        display_name=user.display_name,
        department=user.department,
        is_active=user.is_active,
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
        last_login_at=user.last_login_at,
    )


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="更新用户",
    description="更新用户信息",
)
async def update_user(
    user_id: int,
    data: UserUpdateRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin),
):
    """Update user (admin only)."""
    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update fields
    if data.display_name is not None:
        user.display_name = data.display_name
    if data.department is not None:
        user.department = data.department
    if data.role is not None:
        # Only super admin can change roles
        if current_user["role"] != UserRoleType.SUPER_ADMIN.value:
            raise HTTPException(status_code=403, detail="Only super admin can change roles")
        user.role_type = data.role
    if data.is_active is not None:
        user.is_active = data.is_active
        user.status = "active" if data.is_active else "inactive"

    await session.commit()

    return UserResponse(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        role=user.role_type,
        display_name=user.display_name,
        department=user.department,
        is_active=user.is_active,
        last_login_at=user.last_login_at,
    )


@router.delete(
    "/{user_id}",
    summary="删除/禁用用户",
    description="禁用用户账户",
)
async def deactivate_user(
    user_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin),
):
    """Deactivate user (admin only)."""
    # Prevent self-deactivation
    if current_user["user_id"] == user_id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")

    repo = UserRepository(session)
    success = await repo.deactivate_user(user_id)

    if not success:
        raise HTTPException(status_code=404, detail="User not found")

    await session.commit()

    return {"message": "User deactivated"}


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

    scope_repo = UserScopeRepository(session)
    scope = await scope_repo.add_scope(
        user_id=user_id,
        scope_type=data.scope_type,
        scope_value=data.scope_value,
        granted_by=current_user["user_id"],
        expires_at=data.expires_at,
        notes=data.notes,
    )

    await session.commit()

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
    summary="移除用户权限",
    description="移除用户的学校访问权限",
)
async def remove_user_scope(
    user_id: int,
    scope_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin),
):
    """Remove school scope from user (admin only)."""
    scope_repo = UserScopeRepository(session)
    success = await scope_repo.remove_scope(scope_id)

    if not success:
        raise HTTPException(status_code=404, detail="Scope not found")

    await session.commit()

    return {"message": "Scope removed"}


@router.get(
    "/me/scopes/schools",
    response_model=List[int],
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

    return {
        "school_id": school_id,
        "has_access": has_access,
    }
