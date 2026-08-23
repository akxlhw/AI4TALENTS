"""
Authentication API endpoints.

Schemas live in `app.domains.shared.schemas.auth`; current-user dependencies
live in `app.domains.shared.api.auth_deps`. Both are re-exported here so
existing `from app.domains.shared.api.auth import ...` callers keep working.

Business logic (account status machine, uniqueness checks, audit calls,
token issuance) lives in `services/auth_service.py` (2026-08 cohesion
refactor); endpoints below only parse requests and delegate.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.shared.api.auth_deps import (
    get_current_user,
    require_admin,
    require_super_admin,
    require_user,
    security,
)
from app.domains.shared.schemas.auth import (
    ChangePasswordRequest,
    CurrentUser,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RegisterRequest,
    UserInfo,
)
from app.domains.shared.schemas.common import SuccessResponse
from app.domains.shared.services.audit_service import AuditService
from app.domains.shared.services.auth_service import AuthService
from app.domains.shared.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["Authentication"])

__all__ = [
    "router",
    "security",
    "get_current_user",
    "require_user",
    "require_admin",
    "require_super_admin",
    "LoginRequest",
    "LoginResponse",
    "RefreshRequest",
    "UserInfo",
    "ChangePasswordRequest",
    "RegisterRequest",
    "CurrentUser",
]


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
    message = await AuthService(session).register(data, request)
    return SuccessResponse(message=message)


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
    return await AuthService(session).login(data, request)


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
    return await AuthService(session).refresh(data.refresh_token)


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
        privacy_policy_accepted_at=user.privacy_policy_accepted_at,
        privacy_policy_version=user.privacy_policy_version,
        terms_of_use_accepted_at=user.terms_of_use_accepted_at,
        terms_of_use_version=user.terms_of_use_version,
        storage_consent_level=user.storage_consent_level,
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
    message = await AuthService(session).change_password(
        user_id=current_user["user_id"],
        current_password=data.current_password,
        new_password=data.new_password,
        request=request,
    )
    return SuccessResponse(message=message)


# Export dependencies for use in other routes
__all__ = [
    "get_current_user",
    "require_user",
    "require_admin",
    "require_super_admin",
]
