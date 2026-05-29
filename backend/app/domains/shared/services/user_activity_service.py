"""
User Activity Service — Projection layer over audit logs.

Transforms generic audit_operation_log records into user-friendly ActivityItem
timeline for user detail pages.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.shared.repositories.audit_repository import AuditRepository
from app.domains.shared.repositories.user_repository import UserRepository
from app.domains.shared.schemas.user_activity import ActivityItem


class UserActivityService:
    """Service for building user activity timelines from audit logs."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.audit_repo = AuditRepository(session)
        self.user_repo = UserRepository(session)

    async def get_user_activity_timeline(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ActivityItem], int]:
        """
        Get paginated activity timeline for a user.

        Combines authentication, authorization, and scope events
        from audit_operation_log into a unified timeline.
        """
        logs, total = await self.audit_repo.list_logs_by_user_context(
            user_id=user_id,
            page=page,
            page_size=page_size,
        )

        # Batch fetch actor usernames to avoid N+1
        actor_ids = {log.user_id for log in logs if log.user_id}
        actor_map: dict[int, str] = {}
        if actor_ids:
            for aid in actor_ids:
                user = await self.user_repo.get_by_id(aid)
                if user:
                    actor_map[aid] = user.username

        items = [self._map_audit_to_activity(log, actor_map) for log in logs]
        return items, total

    def _map_audit_to_activity(
        self,
        log,
        actor_map: dict[int, str],
    ) -> ActivityItem:
        """Map an AuditOperationLog record to a user-friendly ActivityItem."""
        actor = None
        if log.user_id:
            actor = {
                "user_id": log.user_id,
                "username": actor_map.get(log.user_id, f"用户#{log.user_id}"),
            }

        activity_type, description = self._build_description(log)

        target_user_id = (
            int(log.resource_id)
            if log.resource_id and log.resource_id.isdigit()
            else log.user_id or 0
        )

        return ActivityItem(
            activity_id=log.log_id,
            activity_time=log.event_time,
            activity_type=activity_type,
            actor=actor,
            target_user_id=target_user_id,
            description=description,
            detail=log.operation_detail or {},
            ip=log.user_ip,
            status=log.status,
        )

    def _build_description(self, log) -> tuple[str, str]:
        """Build (activity_type, description) from audit log fields."""
        event_type = log.event_type or ""
        operation = log.operation or ""
        status = log.status or ""
        detail = log.operation_detail or {}

        # Authentication events
        if event_type == "authentication":
            if operation == "login":
                if status == "success":
                    return "login", "登录成功"
                return "login_failure", f"登录失败：{log.error_message or '未知原因'}"
            if operation == "register":
                return "account_created", "注册账号"
            if operation == "logout":
                return "other", "退出登录"
            return "other", f"认证操作：{operation}"

        # Authorization / user_management events
        if event_type == "authorization" and log.event_subtype == "user_management":
            if operation == "create":
                return "account_created", "管理员创建账号"
            if operation == "update":
                updated = detail.get("updated_fields", [])
                if "role" in updated:
                    new_role = detail.get("role", "")
                    return "role_change", f"角色被修改为 {new_role}"
                if "is_active" in updated:
                    active_val = detail.get("is_active", True)
                    if active_val:
                        return "account_activated", "账号被启用"
                    return "account_deactivated", "账号被禁用"
                return "profile_update", "账号信息被更新"
            if operation == "delete":
                return "account_deactivated", "账号被禁用"
            if operation == "approve":
                return "account_approved", "注册申请被通过"
            if operation == "reject":
                return "account_rejected", "注册申请被拒绝"
            if operation == "change_password":
                return "password_change", "密码被重置"
            return "other", f"账号管理：{operation}"

        # Scope management events
        if event_type == "authorization" and log.event_subtype == "scope_management":
            scope_type = detail.get("scope_type", "")
            scope_value = detail.get("scope_value", "")
            if operation == "grant":
                return "scope_grant", f"被授予 {scope_type} 权限：{scope_value}"
            if operation == "revoke":
                return "scope_revoke", f"被移除 {scope_type} 权限：{scope_value}"
            return "other", f"权限变更：{operation} {scope_type}"

        # Data operations (e.g. export)
        if event_type == "data_operation":
            return "other", f"数据操作：{operation}"

        return "other", f"系统操作：{operation}"
