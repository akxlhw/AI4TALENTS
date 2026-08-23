"""Authentication business logic - registration, login, token refresh,
password change.

Extracted from ``api/auth.py`` (2026-08 cohesion refactor): the account
status machine, uniqueness checks, audit logging and token issuance live
here; the API layer shrinks to request parsing and delegation.

Error contract: raises ``HTTPException`` so the wire responses stay
byte-compatible with the pre-refactor behavior (tests assert on the
``detail`` body shape).
"""

from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import (
    create_access_token,
    create_refresh_token,
    hash_password,
    validate_password_strength,
    verify_password,
    verify_refresh_token,
)
from app.domains.shared.models.enums import UserRoleType
from app.domains.shared.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    UserInfo,
)
from app.domains.shared.services.audit_service import AuditService
from app.domains.shared.services.user_service import UserService


class AuthService:
    """Account lifecycle operations shared by the auth endpoints."""

    def __init__(self, session: AsyncSession) -> None:
        self.users = UserService(session)

    @staticmethod
    def _context(request: Request | None) -> tuple[str | None, str | None]:
        if request is None:
            return None, None
        client_ip = request.client.host if request.client else None
        request_id = getattr(request.state, "request_id", None)
        return client_ip, request_id

    # ============= Register =============

    async def register(self, data: RegisterRequest, request: Request) -> str:
        """Register a new user account pending admin approval.

        Returns the human-facing success message.
        """
        client_ip, request_id = self._context(request)

        # Check username uniqueness
        if await self.users.get_by_username(data.username):
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
        if await self.users.get_by_email(data.email):
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
        if await self.users.get_by_employee_id(data.employee_id):
            await AuditService.log_auth_event(
                user_id=None,
                operation="register",
                status="failure",
                user_ip=client_ip,
                request_id=request_id,
                error_message="该工号已注册",
            )
            raise HTTPException(status_code=400, detail="该工号已注册")

        # Validate password strength
        is_valid, error_msg = validate_password_strength(data.password)
        if not is_valid:
            await AuditService.log_auth_event(
                user_id=None,
                operation="register",
                status="failure",
                user_ip=client_ip,
                request_id=request_id,
                error_message=f"密码强度不足: {error_msg}",
            )
            raise HTTPException(status_code=400, detail=f"密码强度不足: {error_msg}")

        # Validate privacy policy and terms of use acceptance
        if not data.privacy_policy_accepted:
            raise HTTPException(status_code=400, detail="必须同意隐私政策才能注册")
        if not data.terms_of_use_accepted:
            raise HTTPException(status_code=400, detail="必须同意用户协议才能注册")

        # Create user with pending approval status
        password_hash = hash_password(data.password)

        from app.core.config import settings

        now = datetime.now()
        user = await self.users.create_user_and_commit(
            username=data.username,
            email=data.email,
            password_hash=password_hash,
            role=UserRoleType.USER.value,
            display_name=data.display_name,
            employee_id=data.employee_id,
            is_active=False,
            status="pending_approval",
        )
        # Update consent fields after creation
        await self.users.update_privacy_consent_and_commit(
            user_id=user.user_id,
            privacy_policy_accepted_at=now,
            privacy_policy_version=settings.APP_VERSION,
            terms_of_use_accepted_at=now,
            terms_of_use_version=settings.APP_VERSION,
            storage_consent_level=data.storage_consent_level,
        )

        await AuditService.log_auth_event(
            user_id=user.user_id,
            operation="register",
            status="success",
            user_ip=client_ip,
            request_id=request_id,
            detail={"employee_id": data.employee_id},
        )

        return "注册成功，等待管理员审核"

    # ============= Login =============

    async def login(self, data: LoginRequest, request: Request) -> LoginResponse:
        """Login with username/email and password.

        Gives precise per-status rejection messages and audits every outcome.
        """
        client_ip, request_id = self._context(request)

        # Find user by username or email
        user = await self.users.get_by_username(data.username)
        if not user:
            user = await self.users.get_by_email(data.username)

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
        await self.users.update_last_login_and_commit(user.user_id, client_ip)

        await AuditService.log_auth_event(
            user_id=user.user_id,
            operation="login",
            status="success",
            user_ip=client_ip,
            request_id=request_id,
        )

        return self._build_login_response(user)

    # ============= Token refresh =============

    async def refresh(self, refresh_token: str) -> LoginResponse:
        """Issue a fresh access/refresh token pair from a refresh token."""
        payload = verify_refresh_token(refresh_token)
        if not payload:
            raise HTTPException(
                status_code=401,
                detail="无效或过期的刷新令牌",
            )

        user_id = int(payload.get("sub", 0))

        # Verify user exists and is active
        user = await self.users.get_by_id(user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=401,
                detail="用户不存在或已被禁用",
            )

        return self._build_login_response(user)

    # ============= Change password =============

    async def change_password(
        self,
        user_id: int,
        current_password: str,
        new_password: str,
        request: Request | None,
    ) -> str:
        """Verify the current password, validate strength, rotate the hash."""
        client_ip, request_id = self._context(request)
        user = await self.users.get_by_id(user_id)

        if not user:
            await AuditService.log_auth_event(
                user_id=user_id,
                operation="change_password",
                status="failure",
                user_ip=client_ip,
                request_id=request_id,
                error_message="用户不存在",
            )
            raise HTTPException(status_code=404, detail="用户不存在")

        # Verify current password
        if not verify_password(current_password, user.password_hash):
            await AuditService.log_auth_event(
                user_id=user_id,
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

        # Validate new password strength
        is_valid, error_msg = validate_password_strength(new_password)
        if not is_valid:
            await AuditService.log_auth_event(
                user_id=user_id,
                operation="change_password",
                status="failure",
                user_ip=client_ip,
                request_id=request_id,
                error_message=f"新密码强度不足: {error_msg}",
            )
            raise HTTPException(status_code=400, detail=f"新密码强度不足: {error_msg}")

        # Update password
        new_hash = hash_password(new_password)
        await self.users.update_password_and_commit(user.user_id, new_hash)

        await AuditService.log_auth_event(
            user_id=user_id,
            operation="change_password",
            status="success",
            user_ip=client_ip,
            request_id=request_id,
        )

        return "密码修改成功"

    # ============= Helpers =============

    @staticmethod
    def _build_login_response(user) -> LoginResponse:
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
