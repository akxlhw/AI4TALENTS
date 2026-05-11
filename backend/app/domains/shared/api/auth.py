"""
Authentication API endpoints.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_access_token,
    verify_password,
    verify_refresh_token,
)
from app.core.database import get_async_session
from app.domains.shared.models.enums import UserRoleType
from app.domains.shared.schemas.common import SuccessResponse
from app.domains.shared.services.audit_service import AuditService
from app.domains.shared.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer(auto_error=False)


# Pydantic models
class LoginRequest(BaseModel):
    """Login request body."""

    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=100)


class LoginResponse(BaseModel):
    """Login response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 8 * 3600  # 8 hours in seconds
    user: UserInfo


class RefreshRequest(BaseModel):
    """Refresh token request."""

    refresh_token: str


class UserInfo(BaseModel):
    """User information."""

    user_id: int
    username: str
    email: str
    role: str
    display_name: str | None = None
    department: str | None = None


class ChangePasswordRequest(BaseModel):
    """Change password request."""

    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)


class RegisterRequest(BaseModel):
    """User registration request."""

    username: str = Field(..., min_length=3, max_length=100)
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=8, max_length=100)
    employee_id: str = Field(..., pattern=r"^[a-zA-Z]\d{8}$")
    display_name: str | None = Field(default=None, max_length=100)


class CurrentUser(BaseModel):
    """Current user response."""

    user_id: int
    username: str
    email: str
    role: str
    display_name: str | None = None
    department: str | None = None
    is_active: bool
    last_login_at: datetime | None = None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    session: AsyncSession = Depends(get_async_session),
) -> dict | None:
    """
    Get current user from JWT token.
    Returns None if no valid token provided.
    """
    if not credentials:
        return None

    token = credentials.credentials
    payload = verify_access_token(token)

    if not payload:
        return None

    user_id = int(payload.get("sub", 0))

    # Verify user exists and is active
    service = UserService(session)
    user = await service.get_by_id(user_id)

    if not user or not user.is_active:
        return None

    return {
        "user_id": user.user_id,
        "username": user.username,
        "email": user.email,
        "role": user.role_type,
        "display_name": user.display_name,
    }


async def require_user(
    current_user: dict | None = Depends(get_current_user),
) -> dict:
    """
    Require a valid authenticated user.
    Raises 401 if not authenticated.
    """
    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


async def require_admin(
    current_user: dict = Depends(require_user),
) -> dict:
    """
    Require admin or super_admin role.
    Raises 403 if not authorized.
    """
    if current_user["role"] not in [UserRoleType.ADMIN.value, UserRoleType.SUPER_ADMIN.value]:
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )
    return current_user


async def require_super_admin(
    current_user: dict = Depends(require_user),
) -> dict:
    """
    Require super_admin role.
    Raises 403 if not authorized.
    """
    if current_user["role"] != UserRoleType.SUPER_ADMIN.value:
        raise HTTPException(
            status_code=403,
            detail="Super admin access required",
        )
    return current_user


@router.post(
    "/register",
    response_model=SuccessResponse,
    summary="用户注册",
    description="公开注册，注册后需等待管理员审核",
)
async def register(
    request: Request,
    data: RegisterRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Register a new user account.
    The account will be in 'pending_approval' status until an admin approves it.
    """
    service = UserService(session)
    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    # Check username uniqueness
    if await service.get_by_username(data.username):
        await AuditService.log_auth_event(
            user_id=None,
            operation="register",
            status="failure",
            user_ip=client_ip,
            request_id=request_id,
            error_message="用户名已存在",
        )
        raise HTTPException(status_code=400, detail="用户名已存在")

    # Check email uniqueness
    if await service.get_by_email(data.email):
        await AuditService.log_auth_event(
            user_id=None,
            operation="register",
            status="failure",
            user_ip=client_ip,
            request_id=request_id,
            error_message="邮箱已存在",
        )
        raise HTTPException(status_code=400, detail="邮箱已存在")

    # Check employee_id uniqueness
    if await service.get_by_employee_id(data.employee_id):
        await AuditService.log_auth_event(
            user_id=None,
            operation="register",
            status="failure",
            user_ip=client_ip,
            request_id=request_id,
            error_message="该工号已注册",
        )
        raise HTTPException(status_code=400, detail="该工号已注册")

    # Create user with pending approval status
    password_hash = hash_password(data.password)
    user = await service.create_user_and_commit(
        username=data.username,
        email=data.email,
        password_hash=password_hash,
        role=UserRoleType.USER.value,
        display_name=data.display_name,
        employee_id=data.employee_id,
        is_active=False,
        status="pending_approval",
    )

    await AuditService.log_auth_event(
        user_id=user.user_id,
        operation="register",
        status="success",
        user_ip=client_ip,
        request_id=request_id,
        detail={"employee_id": data.employee_id},
    )

    return SuccessResponse(message="注册成功，等待管理员审核")


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="用户登录",
    description="使用用户名和密码登录，返回访问令牌",
)
async def login(
    request: Request,
    data: LoginRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Login with username and password.

    Returns access token and refresh token.
    """
    service = UserService(session)
    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    # Find user by username or email
    user = await service.get_by_username(data.username)
    if not user:
        user = await service.get_by_email(data.username)

    if not user:
        await AuditService.log_auth_event(
            user_id=None,
            operation="login",
            status="failure",
            user_ip=client_ip,
            request_id=request_id,
            error_message="用户名或密码错误",
        )
        raise HTTPException(
            status_code=401,
            detail="用户名或密码错误",
        )

    # Check account status and give precise messages
    if user.status == "pending_approval":
        await AuditService.log_auth_event(
            user_id=user.user_id,
            operation="login",
            status="failure",
            user_ip=client_ip,
            request_id=request_id,
            error_message="账户待审核",
        )
        raise HTTPException(
            status_code=401,
            detail="账户待审核，请联系管理员",
        )

    if user.status == "rejected":
        await AuditService.log_auth_event(
            user_id=user.user_id,
            operation="login",
            status="failure",
            user_ip=client_ip,
            request_id=request_id,
            error_message="注册申请已被拒绝",
        )
        raise HTTPException(
            status_code=401,
            detail="注册申请已被拒绝",
        )

    if not user.is_active:
        await AuditService.log_auth_event(
            user_id=user.user_id,
            operation="login",
            status="failure",
            user_ip=client_ip,
            request_id=request_id,
            error_message="账户已被禁用",
        )
        raise HTTPException(
            status_code=401,
            detail="账户已被禁用",
        )

    # Verify password
    if not verify_password(data.password, user.password_hash):
        await AuditService.log_auth_event(
            user_id=user.user_id,
            operation="login",
            status="failure",
            user_ip=client_ip,
            request_id=request_id,
            error_message="用户名或密码错误",
        )
        raise HTTPException(
            status_code=401,
            detail="用户名或密码错误",
        )

    # Update last login
    await service.update_last_login_and_commit(user.user_id, client_ip)

    await AuditService.log_auth_event(
        user_id=user.user_id,
        operation="login",
        status="success",
        user_ip=client_ip,
        request_id=request_id,
    )

    # Create tokens
    access_token = create_access_token(
        user_id=user.user_id,
        username=user.username,
        role=user.role_type,
    )
    refresh_token = create_refresh_token(user_id=user.user_id)

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserInfo(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            role=user.role_type,
            display_name=user.display_name,
            department=user.department,
        ),
    )


@router.post(
    "/logout",
    response_model=SuccessResponse,
    summary="用户登出",
    description="登出当前用户（客户端应删除令牌）",
)
async def logout(
    request: Request,
    current_user: dict = Depends(require_user),
):
    """
    Logout current user.

    Note: JWT tokens are stateless, so actual logout happens on client side.
    In production, you may want to implement token blacklisting.
    """
    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)
    await AuditService.log_auth_event(
        user_id=current_user["user_id"],
        operation="logout",
        status="success",
        user_ip=client_ip,
        request_id=request_id,
    )
    return SuccessResponse(message="已成功登出")


@router.post(
    "/refresh",
    response_model=LoginResponse,
    summary="刷新令牌",
    description="使用刷新令牌获取新的访问令牌",
)
async def refresh_token(
    data: RefreshRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Refresh access token using refresh token.

    Returns new access token and refresh token.
    """
    payload = verify_refresh_token(data.refresh_token)
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="无效或过期的刷新令牌",
        )

    user_id = int(payload.get("sub", 0))

    # Verify user exists and is active
    service = UserService(session)
    user = await service.get_by_id(user_id)

    if not user or not user.is_active:
        raise HTTPException(
            status_code=401,
            detail="用户不存在或已被禁用",
        )

    # Create new tokens
    access_token = create_access_token(
        user_id=user.user_id,
        username=user.username,
        role=user.role_type,
    )
    new_refresh_token = create_refresh_token(user_id=user.user_id)

    return LoginResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        user=UserInfo(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            role=user.role_type,
            display_name=user.display_name,
            department=user.department,
        ),
    )


@router.get(
    "/me",
    response_model=CurrentUser,
    summary="获取当前用户信息",
    description="返回当前登录用户的详细信息",
)
async def get_current_user_info(
    current_user: dict = Depends(require_user),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get current user information.
    """
    service = UserService(session)
    user = await service.get_by_id(current_user["user_id"])

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    return CurrentUser(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        role=user.role_type,
        display_name=user.display_name,
        department=user.department,
        is_active=user.is_active,
        last_login_at=user.last_login_at,
    )


@router.post(
    "/change-password",
    response_model=SuccessResponse,
    summary="修改密码",
    description="修改当前用户密码",
)
async def change_password(
    request: Request,
    data: ChangePasswordRequest,
    current_user: dict = Depends(require_user),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Change current user's password.
    """
    service = UserService(session)
    user = await service.get_by_id(current_user["user_id"])
    client_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)

    if not user:
        await AuditService.log_auth_event(
            user_id=current_user["user_id"],
            operation="change_password",
            status="failure",
            user_ip=client_ip,
            request_id=request_id,
            error_message="用户不存在",
        )
        raise HTTPException(status_code=404, detail="用户不存在")

    # Verify current password
    if not verify_password(data.current_password, user.password_hash):
        await AuditService.log_auth_event(
            user_id=current_user["user_id"],
            operation="change_password",
            status="failure",
            user_ip=client_ip,
            request_id=request_id,
            error_message="当前密码错误",
        )
        raise HTTPException(
            status_code=400,
            detail="当前密码错误",
        )

    # Update password
    new_hash = hash_password(data.new_password)
    await service.update_password_and_commit(user.user_id, new_hash)

    await AuditService.log_auth_event(
        user_id=current_user["user_id"],
        operation="change_password",
        status="success",
        user_ip=client_ip,
        request_id=request_id,
    )

    return SuccessResponse(message="密码修改成功")


# Export dependencies for use in other routes
__all__ = [
    "get_current_user",
    "require_user",
    "require_admin",
    "require_super_admin",
]
