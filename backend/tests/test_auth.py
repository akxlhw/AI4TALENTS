"""
Tests for Authentication API endpoints.
认证API测试
"""

import pytest
from httpx import AsyncClient

from app.core.auth import create_access_token, create_refresh_token, hash_password
from app.domains.shared.models.enums import UserRoleType
from app.domains.shared.models.iam import UserAccount


@pytest.fixture
async def test_user(test_session):
    """Create a test user for authentication tests."""
    user = UserAccount(
        username="testuser",
        email="test@example.com",
        password_hash=hash_password("testpassword123"),
        role_type=UserRoleType.USER.value,
        is_active=True,
        display_name="Test User",
    )
    test_session.add(user)
    await test_session.commit()
    return user


@pytest.fixture
async def test_admin(test_session):
    """Create a test admin user."""
    admin = UserAccount(
        username="admin",
        email="admin@example.com",
        password_hash=hash_password("admin123"),
        role_type=UserRoleType.ADMIN.value,
        is_active=True,
        display_name="Admin User",
    )
    test_session.add(admin)
    await test_session.commit()
    return admin


@pytest.fixture
async def inactive_user(test_session):
    """Create an inactive user for testing."""
    user = UserAccount(
        username="inactive",
        email="inactive@example.com",
        password_hash=hash_password("password123"),
        role_type=UserRoleType.USER.value,
        is_active=False,
        status="inactive",
    )
    test_session.add(user)
    await test_session.commit()
    return user


@pytest.fixture
async def pending_user(test_session):
    """Create a pending approval user for testing."""
    user = UserAccount(
        username="pendinguser",
        email="pending@example.com",
        password_hash=hash_password("password123"),
        role_type=UserRoleType.USER.value,
        is_active=False,
        status="pending_approval",
        employee_id="h00123456",
    )
    test_session.add(user)
    await test_session.commit()
    return user


@pytest.fixture
async def rejected_user(test_session):
    """Create a rejected user for testing."""
    user = UserAccount(
        username="rejecteduser",
        email="rejected@example.com",
        password_hash=hash_password("password123"),
        role_type=UserRoleType.USER.value,
        is_active=False,
        status="rejected",
        employee_id="h00987654",
    )
    test_session.add(user)
    await test_session.commit()
    return user


class TestLogin:
    """Tests for /auth/login endpoint."""

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user):
        """Test successful login with valid credentials."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "testpassword123"},
        )

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["username"] == "testuser"
        assert data["user"]["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_login_with_email(self, client: AsyncClient, test_user):
        """Test login using email instead of username."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "test@example.com", "password": "testpassword123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user"]["username"] == "testuser"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, test_user):
        """Test login with wrong password."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "wrongpassword"},
        )

        assert response.status_code == 401
        assert "用户名或密码错误" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login with non-existent user."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "nonexistent", "password": "password123"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_inactive_user(self, client: AsyncClient, inactive_user):
        """Test login with inactive user."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "inactive", "password": "password123"},
        )

        assert response.status_code == 401
        assert "账户已被禁用" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_empty_credentials(self, client: AsyncClient):
        """Test login with empty credentials."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "", "password": ""},
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_login_pending_approval_user(self, client: AsyncClient, pending_user):
        """Test login with pending approval user."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "pendinguser", "password": "password123"},
        )

        assert response.status_code == 401
        assert "待审核" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_rejected_user(self, client: AsyncClient, rejected_user):
        """Test login with rejected user."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "rejecteduser", "password": "password123"},
        )

        assert response.status_code == 401
        assert "拒绝" in response.json()["detail"]


class TestRegistration:
    """Tests for /auth/register endpoint."""

    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient):
        """Test successful user registration."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "newregister",
                "email": "newregister@example.com",
                "password": "Str0ng!Pw",
                "employee_id": "h00111111",
            },
        )

        assert response.status_code == 200
        assert "等待管理员审核" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, client: AsyncClient, test_user):
        """Test registration with duplicate username."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "email": "unique@example.com",
                "password": "Str0ng!Pw",
                "employee_id": "h00222222",
            },
        )

        assert response.status_code == 400
        assert "用户名已存在" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient, test_user):
        """Test registration with duplicate email."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "uniqueuser",
                "email": "test@example.com",
                "password": "Str0ng!Pw",
                "employee_id": "h00333333",
            },
        )

        assert response.status_code == 400
        assert "邮箱已存在" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_register_duplicate_employee_id(self, client: AsyncClient, pending_user):
        """Test registration with duplicate employee_id."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "uniqueuser2",
                "email": "unique2@example.com",
                "password": "Str0ng!Pw",
                "employee_id": "h00123456",
            },
        )

        assert response.status_code == 400
        assert "工号已注册" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_register_invalid_employee_id_format(self, client: AsyncClient):
        """Test registration with invalid employee_id format."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "badiduser",
                "email": "badid@example.com",
                "password": "Str0ng!Pw",
                "employee_id": "123456789",  # missing letter prefix
            },
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_register_short_employee_id(self, client: AsyncClient):
        """Test registration with too short employee_id."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "shortiduser",
                "email": "shortid@example.com",
                "password": "Str0ng!Pw",
                "employee_id": "h1234567",  # 7 digits instead of 8
            },
        )

        assert response.status_code == 422  # Validation error


class TestLogout:
    """Tests for /auth/logout endpoint."""

    @pytest.mark.asyncio
    async def test_logout_success(self, client: AsyncClient, test_user):
        """Test successful logout."""
        # First login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "testpassword123"},
        )
        token = login_response.json()["access_token"]

        # Then logout
        response = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert "已成功登出" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_logout_without_token(self, client: AsyncClient):
        """Test logout without authentication token."""
        response = await client.post("/api/v1/auth/logout")

        assert response.status_code == 401


class TestRefreshToken:
    """Tests for /auth/refresh endpoint."""

    @pytest.mark.asyncio
    async def test_refresh_success(self, client: AsyncClient, test_user):
        """Test successful token refresh."""
        # First login to get refresh token
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "testpassword123"},
        )
        refresh_token = login_response.json()["refresh_token"]

        # Refresh token
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["username"] == "testuser"

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self, client: AsyncClient):
        """Test refresh with invalid token."""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid_token"},
        )

        assert response.status_code == 401


class TestGetCurrentUser:
    """Tests for /auth/me endpoint."""

    @pytest.mark.asyncio
    async def test_get_current_user_success(self, client: AsyncClient, test_user):
        """Test getting current user info."""
        # Login first
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "testpassword123"},
        )
        token = login_response.json()["access_token"]

        # Get current user
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_get_current_user_unauthenticated(self, client: AsyncClient):
        """Test getting current user without authentication."""
        response = await client.get("/api/v1/auth/me")

        assert response.status_code == 401


class TestChangePassword:
    """Tests for /auth/change-password endpoint."""

    @pytest.mark.asyncio
    async def test_change_password_success(self, client: AsyncClient, test_user):
        """Test successful password change."""
        # Login first
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "testpassword123"},
        )
        token = login_response.json()["access_token"]

        # Change password
        response = await client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": "testpassword123",
                "new_password": "N3wP@ssw0rd",
            },
        )

        assert response.status_code == 200
        assert "密码修改成功" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, client: AsyncClient, test_user):
        """Test password change with wrong current password."""
        # Login first
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "testpassword123"},
        )
        token = login_response.json()["access_token"]

        # Try to change password with wrong current password
        response = await client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": "wrongpassword",
                "new_password": "N3wP@ssw0rd",
            },
        )

        assert response.status_code == 400
        assert "当前密码错误" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_change_password_too_short(self, client: AsyncClient, test_user):
        """Test password change with too short new password."""
        # Login first
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "testpassword123"},
        )
        token = login_response.json()["access_token"]

        # Try to change password with short new password
        response = await client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": "testpassword123",
                "new_password": "short",
            },
        )

        assert response.status_code == 422  # Pydantic min_length validation
    """Tests for authentication utility functions."""

    def test_hash_password(self):
        """Test password hashing."""
        password = "testpassword123"
        hashed = hash_password(password)

        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt format

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        from app.core.auth import verify_password

        password = "testpassword123"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        from app.core.auth import verify_password

        password = "testpassword123"
        hashed = hash_password(password)

        assert verify_password("wrongpassword", hashed) is False

    def test_create_access_token(self):
        """Test access token creation."""
        token = create_access_token(
            user_id=1,
            username="testuser",
            role="user",
        )

        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token(self):
        """Test refresh token creation."""
        token = create_refresh_token(user_id=1)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_access_token(self):
        """Test access token verification."""
        from app.core.auth import verify_access_token

        token = create_access_token(
            user_id=1,
            username="testuser",
            role="user",
        )

        payload = verify_access_token(token)

        assert payload is not None
        assert payload["sub"] == "1"
        assert payload["username"] == "testuser"
        assert payload["type"] == "access"

    def test_verify_refresh_token(self):
        """Test refresh token verification."""
        from app.core.auth import verify_refresh_token

        token = create_refresh_token(user_id=1)
        payload = verify_refresh_token(token)

        assert payload is not None
        assert payload["sub"] == "1"
        assert payload["type"] == "refresh"
