"""
Tests for Audit log writing.
审计日志写入测试
"""

import pytest
from httpx import AsyncClient

from app.core.auth import hash_password
from app.models.audit import AuditOperationLog
from app.models.enums import UserRoleType
from app.models.iam import UserAccount


@pytest.fixture
async def test_admin(test_session):
    """Create a test admin user."""
    admin = UserAccount(
        username="admin",
        email="admin@example.com",
        password_hash=hash_password("admin123"),
        role_type=UserRoleType.ADMIN.value,
        is_active=True,
        status="active",
        display_name="Admin User",
    )
    test_session.add(admin)
    await test_session.commit()
    return admin


@pytest.fixture
async def admin_token(client: AsyncClient, test_admin):
    """Get auth token for admin user."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    return response.json()["access_token"]


class TestAuditLogWriting:
    """Tests that audit logs are written for key operations."""

    @pytest.mark.asyncio
    async def test_register_creates_audit_log(self, client: AsyncClient, test_session):
        """Test that successful registration creates an audit log."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "auditregister",
                "email": "auditregister@example.com",
                "password": "password123",
                "employee_id": "h00999999",
            },
        )

        assert response.status_code == 200

        # Query audit log directly from the same session
        result = await test_session.execute(
            AuditOperationLog.__table__.select().where(
                AuditOperationLog.operation == "register",
                AuditOperationLog.event_type == "authentication",
            )
        )
        logs = result.fetchall()
        assert len(logs) >= 1
        log = logs[-1]
        assert log.status == "success"
        assert log.operation_detail is not None
        assert log.operation_detail.get("employee_id") == "h00999999"

    @pytest.mark.asyncio
    async def test_login_failure_creates_audit_log(self, client: AsyncClient, test_session):
        """Test that failed login creates an audit log."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "nonexistent", "password": "wrongpassword"},
        )

        assert response.status_code == 401

        result = await test_session.execute(
            AuditOperationLog.__table__.select().where(
                AuditOperationLog.operation == "login",
                AuditOperationLog.status == "failure",
            )
        )
        logs = result.fetchall()
        assert len(logs) >= 1

    @pytest.mark.asyncio
    async def test_user_approval_creates_audit_log(
        self, client: AsyncClient, test_session, admin_token
    ):
        """Test that user approval creates an audit log."""
        # Create pending user
        user = UserAccount(
            username="approvetest",
            email="approvetest@example.com",
            password_hash=hash_password("password123"),
            role_type=UserRoleType.USER.value,
            is_active=False,
            status="pending_approval",
            employee_id="h00888888",
        )
        test_session.add(user)
        await test_session.commit()

        response = await client.post(
            f"/api/v1/users/{user.user_id}/approve",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200

        result = await test_session.execute(
            AuditOperationLog.__table__.select().where(
                AuditOperationLog.operation == "approve",
                AuditOperationLog.event_type == "authorization",
            )
        )
        logs = result.fetchall()
        assert len(logs) >= 1
        log = logs[-1]
        assert log.status == "success"
        assert str(user.user_id) == log.resource_id
