"""
User Service - 用户与权限服务层

封装 UserRepository 和 UserScopeRepository 调用，
遵循架构规范：Endpoint -> Service -> Repository
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.shared.models.iam import UserAccount, UserSchoolScope
from app.domains.shared.repositories.user_repository import UserRepository, UserScopeRepository


class UserService:
    """
    用户服务 - 封装用户与权限相关的业务逻辑

    职责：
    - 用户查询（按 ID/用户名/邮箱/工号）
    - 用户创建、更新、删除
    - 密码管理
    - 权限范围（scope）管理
    - 访问权限检查
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.scope_repo = UserScopeRepository(session)

    # ---- User CRUD ----

    async def get_by_id(self, user_id: int) -> UserAccount | None:
        """根据ID获取用户"""
        return await self.user_repo.get_by_id(user_id)

    async def get_by_username(self, username: str) -> UserAccount | None:
        """根据用户名获取用户"""
        return await self.user_repo.get_by_username(username)

    async def get_by_email(self, email: str) -> UserAccount | None:
        """根据邮箱获取用户"""
        return await self.user_repo.get_by_email(email)

    async def get_by_employee_id(self, employee_id: str) -> UserAccount | None:
        """根据工号获取用户"""
        return await self.user_repo.get_by_employee_id(employee_id)

    async def create_user_and_commit(
        self,
        username: str,
        email: str,
        password_hash: str,
        role: str = "user",
        display_name: str | None = None,
        employee_id: str | None = None,
        is_active: bool = True,
        status: str = "active",
    ) -> UserAccount:
        """创建用户并提交"""
        return await self.user_repo.create_user_and_commit(
            username=username,
            email=email,
            password_hash=password_hash,
            role=role,
            display_name=display_name,
            employee_id=employee_id,
            is_active=is_active,
            status=status,
        )

    async def update_user_and_commit(
        self,
        user_id: int,
        display_name: str | None = None,
        department: str | None = None,
        role: str | None = None,
        is_active: bool | None = None,
    ) -> UserAccount | None:
        """更新用户并提交"""
        return await self.user_repo.update_user_and_commit(
            user_id=user_id,
            display_name=display_name,
            department=department,
            role=role,
            is_active=is_active,
        )

    async def deactivate_user_and_commit(self, user_id: int) -> bool:
        """禁用用户并提交"""
        return await self.user_repo.deactivate_user_and_commit(user_id)

    async def approve_user_and_commit(self, user_id: int) -> UserAccount | None:
        """审批通过用户注册并提交"""
        return await self.user_repo.approve_user_and_commit(user_id)

    async def reject_user_and_commit(self, user_id: int) -> UserAccount | None:
        """拒绝用户注册并提交"""
        return await self.user_repo.reject_user_and_commit(user_id)

    async def update_password_and_commit(self, user_id: int, new_password_hash: str) -> bool:
        """更新密码并提交"""
        return await self.user_repo.update_password_and_commit(user_id, new_password_hash)

    async def update_last_login_and_commit(
        self, user_id: int, ip_address: str | None = None
    ) -> None:
        """更新最后登录时间并提交"""
        await self.user_repo.update_last_login_and_commit(user_id, ip_address)

    async def list_users(
        self,
        role: str | None = None,
        is_active: bool | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[UserAccount], int]:
        """获取用户列表"""
        return await self.user_repo.list_users(
            role=role, is_active=is_active, status=status, page=page, page_size=page_size
        )

    # ---- Scope operations ----

    async def get_user_scopes(
        self,
        user_id: int,
        active_only: bool = True,
        scope_type: str | None = None,
    ) -> list[UserSchoolScope]:
        """获取用户权限范围"""
        return await self.scope_repo.get_user_scopes(user_id, active_only, scope_type)

    async def add_scope_and_commit(
        self,
        user_id: int,
        scope_type: str,
        scope_value: str,
        granted_by: int,
        expires_at: datetime | None = None,
        notes: str | None = None,
    ) -> UserSchoolScope:
        """添加权限范围并提交"""
        return await self.scope_repo.add_scope_and_commit(
            user_id=user_id,
            scope_type=scope_type,
            scope_value=scope_value,
            granted_by=granted_by,
            expires_at=expires_at,
            notes=notes,
        )

    async def remove_scope_and_commit(self, scope_id: int) -> bool:
        """移除权限范围并提交"""
        return await self.scope_repo.remove_scope_and_commit(scope_id)

    async def check_user_has_access(self, user_id: int, school_id: int) -> bool:
        """检查用户是否有权访问指定学校"""
        return await self.scope_repo.check_user_has_access(user_id, school_id)

    async def get_accessible_school_ids(self, user_id: int) -> list[int]:
        """获取用户可访问的学校ID列表"""
        return await self.scope_repo.get_accessible_school_ids(user_id)

    async def get_accessible_tech_domain_ids(self, user_id: int) -> list[int]:
        """获取用户可访问的技术领域ID列表"""
        return await self.scope_repo.get_accessible_tech_domain_ids(user_id)

    async def get_accessible_country_codes(self, user_id: int) -> list[str]:
        """获取用户可访问的国家代码列表"""
        return await self.scope_repo.get_accessible_country_codes(user_id)

    async def get_user_default_view(self, user_id: int) -> str:
        """获取用户默认视角"""
        return await self.scope_repo.get_user_default_view(user_id)

    async def update_default_view_and_commit(self, user_id: int, default_view: str) -> bool:
        """更新用户默认视角并提交"""
        return await self.scope_repo.update_default_view_and_commit(user_id, default_view)

    # ---- Privacy consent operations ----

    async def update_privacy_consent_and_commit(
        self,
        user_id: int,
        privacy_policy_accepted_at: datetime | None = None,
        privacy_policy_version: str | None = None,
        terms_of_use_accepted_at: datetime | None = None,
        terms_of_use_version: str | None = None,
        storage_consent_level: str | None = None,
    ) -> bool:
        """更新用户隐私同意记录并提交"""
        return await self.user_repo.update_privacy_consent_and_commit(
            user_id=user_id,
            privacy_policy_accepted_at=privacy_policy_accepted_at,
            privacy_policy_version=privacy_policy_version,
            terms_of_use_accepted_at=terms_of_use_accepted_at,
            terms_of_use_version=terms_of_use_version,
            storage_consent_level=storage_consent_level,
        )

    async def get_privacy_consent_status(self, user_id: int) -> dict | None:
        """获取用户隐私同意状态"""
        return await self.user_repo.get_privacy_consent_status(user_id)
