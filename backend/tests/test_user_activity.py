"""
Tests for UserActivityService and user activity timeline API.
用户活动记录与审计聚合测试
"""

import pytest
from httpx import AsyncClient

from app.core.auth import hash_password
from app.domains.shared.models.audit import AuditOperationLog
from app.domains.shared.models.enums import UserRoleType
from app.domains.shared.models.iam import UserAccount
from app.domains.shared.services.user_activity_service import UserActivityService


@pytest.fixture
async def test_target_user(test_session):
    """Create a target user for activity tests."""
    user = UserAccount(
        username="activitytarget",
        email="target@example.com",
        password_hash=hash_password("password123"),
        role_type=UserRoleType.USER.value,
        is_active=True,
        display_name="Target User",
    )
    test_session.add(user)
    await test_session.commit()
    return user


@pytest.fixture
async def test_actor_admin(test_session):
    """Create an admin who performs operations on the target user."""
    admin = UserAccount(
        username="activityactor",
        email="actor@example.com",
        password_hash=hash_password("admin123"),
        role_type=UserRoleType.ADMIN.value,
        is_active=True,
        display_name="Actor Admin",
    )
    test_session.add(admin)
    await test_session.commit()
    return admin


@pytest.fixture
async def test_super_admin(test_session):
    """Create a super admin for API access."""
    super_admin = UserAccount(
        username="superactor",
        email="super@example.com",
        password_hash=hash_password("super123"),
        role_type=UserRoleType.SUPER_ADMIN.value,
        is_active=True,
        display_name="Super Admin",
    )
    test_session.add(super_admin)
    await test_session.commit()
    return super_admin


@pytest.fixture
async def super_admin_token(client: AsyncClient, test_super_admin):
    """Get auth token for super admin."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "superactor", "password": "super123"},
    )
    return response.json()["access_token"]


@pytest.fixture
async def login_audit_logs(test_session, test_target_user):
    """Create sample login audit logs for the target user."""
    from datetime import datetime

    logs = [
        AuditOperationLog(
            event_time=datetime(2026, 5, 1, 10, 0, 0),
            user_id=test_target_user.user_id,
            user_ip="192.168.1.1",
            event_type="authentication",
            event_subtype=None,
            resource_type="user",
            resource_id=str(test_target_user.user_id),
            operation="login",
            operation_detail={},
            status="success",
            error_message=None,
            request_id="req-1",
            user_agent="Mozilla/5.0",
        ),
        AuditOperationLog(
            event_time=datetime(2026, 5, 2, 10, 0, 0),
            user_id=test_target_user.user_id,
            user_ip="192.168.1.2",
            event_type="authentication",
            event_subtype=None,
            resource_type="user",
            resource_id=str(test_target_user.user_id),
            operation="login",
            operation_detail={},
            status="failure",
            error_message="用户名或密码错误",
            request_id="req-2",
            user_agent="Mozilla/5.0",
        ),
    ]
    for log in logs:
        test_session.add(log)
    await test_session.commit()
    return logs


@pytest.fixture
async def management_audit_logs(test_session, test_target_user, test_actor_admin):
    """Create sample user management audit logs."""
    from datetime import datetime

    logs = [
        AuditOperationLog(
            event_time=datetime(2026, 5, 3, 10, 0, 0),
            user_id=test_actor_admin.user_id,
            user_ip="192.168.1.3",
            event_type="authorization",
            event_subtype="user_management",
            resource_type="user",
            resource_id=str(test_target_user.user_id),
            operation="update",
            operation_detail={"updated_fields": ["role"], "role": "admin"},
            status="success",
            error_message=None,
            request_id="req-3",
            user_agent="Mozilla/5.0",
        ),
        AuditOperationLog(
            event_time=datetime(2026, 5, 4, 10, 0, 0),
            user_id=test_actor_admin.user_id,
            user_ip="192.168.1.4",
            event_type="authorization",
            event_subtype="scope_management",
            resource_type="user_scope",
            resource_id=str(test_target_user.user_id),
            operation="grant",
            operation_detail={"scope_type": "school", "scope_value": "1"},
            status="success",
            error_message=None,
            request_id="req-4",
            user_agent="Mozilla/5.0",
        ),
    ]
    for log in logs:
        test_session.add(log)
    await test_session.commit()
    return logs


class TestUserActivityService:
    """Tests for UserActivityService projection logic."""

    @pytest.mark.asyncio
    async def test_get_user_activity_timeline(
        self,
        test_session,
        test_target_user,
        login_audit_logs,
        management_audit_logs,
    ):
        """Test that activity timeline aggregates all relevant audit events."""
        service = UserActivityService(test_session)
        items, total = await service.get_user_activity_timeline(
            test_target_user.user_id, page=1, page_size=20
        )

        assert total == 4
        assert len(items) == 4

        # Should be ordered by time desc
        types = [item.activity_type for item in items]
        assert types == [
            "scope_grant",
            "role_change",
            "login_failure",
            "login",
        ]

    @pytest.mark.asyncio
    async def test_login_success_description(
        self, test_session, test_target_user, login_audit_logs
    ):
        """Test description mapping for successful login."""
        service = UserActivityService(test_session)
        items, _ = await service.get_user_activity_timeline(
            test_target_user.user_id, page=1, page_size=20
        )

        login_item = [i for i in items if i.activity_type == "login"][0]
        assert login_item.description == "登录成功"
        assert login_item.ip == "192.168.1.1"
        assert login_item.status == "success"

    @pytest.mark.asyncio
    async def test_login_failure_description(
        self, test_session, test_target_user, login_audit_logs
    ):
        """Test description mapping for failed login."""
        service = UserActivityService(test_session)
        items, _ = await service.get_user_activity_timeline(
            test_target_user.user_id, page=1, page_size=20
        )

        failure_item = [i for i in items if i.activity_type == "login_failure"][0]
        assert "登录失败" in failure_item.description
        assert failure_item.status == "failure"

    @pytest.mark.asyncio
    async def test_role_change_description(
        self,
        test_session,
        test_target_user,
        management_audit_logs,
    ):
        """Test description mapping for role change."""
        service = UserActivityService(test_session)
        items, _ = await service.get_user_activity_timeline(
            test_target_user.user_id, page=1, page_size=20
        )

        role_item = [i for i in items if i.activity_type == "role_change"][0]
        assert "角色被修改为 admin" == role_item.description
        assert role_item.actor is not None
        assert role_item.actor["username"] == "activityactor"

    @pytest.mark.asyncio
    async def test_scope_grant_description(
        self,
        test_session,
        test_target_user,
        management_audit_logs,
    ):
        """Test description mapping for scope grant."""
        service = UserActivityService(test_session)
        items, _ = await service.get_user_activity_timeline(
            test_target_user.user_id, page=1, page_size=20
        )

        scope_item = [i for i in items if i.activity_type == "scope_grant"][0]
        assert "被授予 school 权限：1" == scope_item.description

    @pytest.mark.asyncio
    async def test_pagination(
        self,
        test_session,
        test_target_user,
        login_audit_logs,
        management_audit_logs,
    ):
        """Test pagination returns correct slices."""
        service = UserActivityService(test_session)
        items, total = await service.get_user_activity_timeline(
            test_target_user.user_id, page=1, page_size=2
        )

        assert total == 4
        assert len(items) == 2
        # Most recent first
        assert items[0].activity_type == "scope_grant"
        assert items[1].activity_type == "role_change"


class TestUserActivityAPI:
    """Tests for GET /users/{user_id}/activities endpoint."""

    @pytest.mark.asyncio
    async def test_get_activities_as_super_admin(
        self,
        client: AsyncClient,
        test_target_user,
        login_audit_logs,
        management_audit_logs,
        super_admin_token,
    ):
        """Test that super admin can retrieve user activity timeline."""
        response = await client.get(
            f"/api/v1/users/{test_target_user.user_id}/activities",
            headers={"Authorization": f"Bearer {super_admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 4
        assert len(data["items"]) == 4

        # Verify schema fields
        item = data["items"][0]
        assert "activity_id" in item
        assert "activity_time" in item
        assert "activity_type" in item
        assert "description" in item
        assert "actor" in item
        assert "ip" in item
        assert "status" in item

    @pytest.mark.asyncio
    async def test_get_activities_forbidden_for_normal_user(
        self,
        client: AsyncClient,
        test_target_user,
        normal_user_token,
    ):
        """Test that normal users cannot access activity timeline."""
        response = await client.get(
            f"/api/v1/users/{test_target_user.user_id}/activities",
            headers={"Authorization": f"Bearer {normal_user_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_activities_pagination(
        self,
        client: AsyncClient,
        test_target_user,
        login_audit_logs,
        management_audit_logs,
        super_admin_token,
    ):
        """Test pagination query params."""
        response = await client.get(
            f"/api/v1/users/{test_target_user.user_id}/activities",
            params={"page": 1, "page_size": 2},
            headers={"Authorization": f"Bearer {super_admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 4
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2


class TestUserListFiltering:
    """Tests for enhanced user list filtering and sorting."""

    @pytest.mark.asyncio
    async def test_list_users_sort_by_created_at_desc(
        self,
        client: AsyncClient,
        super_admin_token,
        test_target_user,
        test_actor_admin,
    ):
        """Test sorting users by created_at desc (default)."""
        response = await client.get(
            "/api/v1/users",
            params={"sort_by": "created_at", "sort_order": "desc"},
            headers={"Authorization": f"Bearer {super_admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) >= 2

    @pytest.mark.asyncio
    async def test_list_users_filter_by_role(
        self,
        client: AsyncClient,
        super_admin_token,
        test_target_user,
        test_actor_admin,
    ):
        """Test filtering users by role."""
        response = await client.get(
            "/api/v1/users",
            params={"role": "admin"},
            headers={"Authorization": f"Bearer {super_admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert all(u["role"] == "admin" for u in data["items"])

    @pytest.mark.asyncio
    async def test_list_users_filter_by_status(
        self,
        client: AsyncClient,
        super_admin_token,
        test_target_user,
    ):
        """Test filtering users by status."""
        response = await client.get(
            "/api/v1/users",
            params={"status": "active"},
            headers={"Authorization": f"Bearer {super_admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert all(u["status"] == "active" for u in data["items"])
