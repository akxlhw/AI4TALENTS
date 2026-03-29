"""
Tests for Permissions API endpoints.
权限隔离API测试
"""
import pytest
from httpx import AsyncClient
from datetime import datetime

from app.models.iam import UserAccount, UserSchoolScope
from app.models.school import School
from app.models.enums import UserRoleType
from app.core.auth import hash_password


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
async def test_super_admin(test_session):
    """Create a test super admin user."""
    super_admin = UserAccount(
        username="superadmin",
        email="superadmin@example.com",
        password_hash=hash_password("superadmin123"),
        role_type=UserRoleType.SUPER_ADMIN.value,
        is_active=True,
        display_name="Super Admin",
    )
    test_session.add(super_admin)
    await test_session.commit()
    return super_admin


@pytest.fixture
async def test_normal_user(test_session):
    """Create a normal test user."""
    user = UserAccount(
        username="normaluser",
        email="normal@example.com",
        password_hash=hash_password("password123"),
        role_type=UserRoleType.USER.value,
        is_active=True,
        display_name="Normal User",
    )
    test_session.add(user)
    await test_session.commit()
    return user


@pytest.fixture
async def admin_token(client: AsyncClient, test_admin):
    """Get auth token for admin user."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    return response.json()["access_token"]


@pytest.fixture
async def super_admin_token(client: AsyncClient, test_super_admin):
    """Get auth token for super admin user."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "superadmin", "password": "superadmin123"},
    )
    return response.json()["access_token"]


@pytest.fixture
async def normal_user_token(client: AsyncClient, test_normal_user):
    """Get auth token for normal user."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "normaluser", "password": "password123"},
    )
    return response.json()["access_token"]


@pytest.fixture
async def test_school(test_session, sample_country):
    """Create a test school."""
    school = School(
        school_name="Test University",
        country_id=sample_country.country_id,
        is_visible=True,
    )
    test_session.add(school)
    await test_session.commit()
    return school


class TestRoleBasedAccess:
    """Tests for role-based access control."""

    @pytest.mark.asyncio
    async def test_admin_can_list_users(self, client: AsyncClient, admin_token):
        """Test that admin can list users."""
        response = await client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_normal_user_cannot_list_users(
        self, client: AsyncClient, normal_user_token
    ):
        """Test that normal user cannot list users."""
        response = await client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {normal_user_token}"},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_unauthenticated_cannot_list_users(self, client: AsyncClient):
        """Test that unauthenticated user cannot list users."""
        response = await client.get("/api/v1/users")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_admin_can_create_user(self, client: AsyncClient, admin_token):
        """Test that admin can create a new user."""
        response = await client.post(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "newpassword123",
                "role": "user",
                "display_name": "New User",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "newuser"
        assert data["role"] == "user"

    @pytest.mark.asyncio
    async def test_normal_user_cannot_create_user(
        self, client: AsyncClient, normal_user_token
    ):
        """Test that normal user cannot create users."""
        response = await client.post(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {normal_user_token}"},
            json={
                "username": "anotheruser",
                "email": "another@example.com",
                "password": "password123",
                "role": "user",
            },
        )

        assert response.status_code == 403


class TestUserSelfAccess:
    """Tests for users accessing their own data."""

    @pytest.mark.asyncio
    async def test_user_can_view_own_info(
        self, client: AsyncClient, normal_user_token, test_normal_user
    ):
        """Test that user can view their own info."""
        response = await client.get(
            f"/api/v1/users/{test_normal_user.user_id}",
            headers={"Authorization": f"Bearer {normal_user_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == test_normal_user.user_id
        assert data["username"] == "normaluser"

    @pytest.mark.asyncio
    async def test_user_cannot_view_other_user_info(
        self, client: AsyncClient, normal_user_token, test_admin
    ):
        """Test that normal user cannot view other user's info."""
        response = await client.get(
            f"/api/v1/users/{test_admin.user_id}",
            headers={"Authorization": f"Bearer {normal_user_token}"},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_can_view_other_user_info(
        self, client: AsyncClient, admin_token, test_normal_user
    ):
        """Test that admin can view other user's info."""
        response = await client.get(
            f"/api/v1/users/{test_normal_user.user_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200


class TestUserScopes:
    """Tests for user scope management."""

    @pytest.mark.asyncio
    async def test_admin_can_add_scope(
        self, client: AsyncClient, admin_token, test_normal_user, test_school
    ):
        """Test that admin can add scope to user."""
        response = await client.post(
            f"/api/v1/users/{test_normal_user.user_id}/scopes",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "user_id": test_normal_user.user_id,
                "scope_type": "school",
                "scope_value": str(test_school.school_id),
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["scope_type"] == "school"
        assert data["scope_value"] == str(test_school.school_id)

    @pytest.mark.asyncio
    async def test_admin_can_list_user_scopes(
        self, client: AsyncClient, admin_token, test_normal_user
    ):
        """Test that admin can list user scopes."""
        response = await client.get(
            f"/api/v1/users/{test_normal_user.user_id}/scopes",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_normal_user_cannot_add_scope(
        self, client: AsyncClient, normal_user_token, test_admin, test_school
    ):
        """Test that normal user cannot add scopes."""
        response = await client.post(
            f"/api/v1/users/{test_admin.user_id}/scopes",
            headers={"Authorization": f"Bearer {normal_user_token}"},
            json={
                "user_id": test_admin.user_id,
                "scope_type": "school",
                "scope_value": str(test_school.school_id),
            },
        )

        assert response.status_code == 403


class TestThreeDimensionalScopes:
    """Tests for three-dimensional permission scopes."""

    @pytest.mark.asyncio
    async def test_get_accessible_schools(
        self, client: AsyncClient, normal_user_token
    ):
        """Test getting accessible schools."""
        response = await client.get(
            "/api/v1/users/me/scopes/schools",
            headers={"Authorization": f"Bearer {normal_user_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_accessible_countries(
        self, client: AsyncClient, normal_user_token
    ):
        """Test getting accessible countries."""
        response = await client.get(
            "/api/v1/users/me/scopes/countries",
            headers={"Authorization": f"Bearer {normal_user_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_accessible_tech_elements(
        self, client: AsyncClient, normal_user_token
    ):
        """Test getting accessible tech elements."""
        response = await client.get(
            "/api/v1/users/me/scopes/tech-elements",
            headers={"Authorization": f"Bearer {normal_user_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_check_school_access(
        self, client: AsyncClient, normal_user_token, test_school
    ):
        """Test checking school access."""
        response = await client.get(
            f"/api/v1/users/me/scopes/check/{test_school.school_id}",
            headers={"Authorization": f"Bearer {normal_user_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "school_id" in data
        assert "has_access" in data


class TestDefaultView:
    """Tests for default view preference."""

    @pytest.mark.asyncio
    async def test_get_default_view(self, client: AsyncClient, normal_user_token):
        """Test getting default view preference."""
        response = await client.get(
            "/api/v1/users/me/default-view",
            headers={"Authorization": f"Bearer {normal_user_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "default_view" in data
        assert data["default_view"] in ["tech_element", "country_school"]

    @pytest.mark.asyncio
    async def test_update_default_view(self, client: AsyncClient, normal_user_token):
        """Test updating default view preference."""
        response = await client.put(
            "/api/v1/users/me/default-view",
            headers={"Authorization": f"Bearer {normal_user_token}"},
            json={"default_view": "country_school"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["default_view"] == "country_school"

    @pytest.mark.asyncio
    async def test_update_default_view_invalid(
        self, client: AsyncClient, normal_user_token
    ):
        """Test updating with invalid view value."""
        response = await client.put(
            "/api/v1/users/me/default-view",
            headers={"Authorization": f"Bearer {normal_user_token}"},
            json={"default_view": "invalid_view"},
        )

        assert response.status_code == 422  # Validation error


class TestSuperAdminPrivileges:
    """Tests for super admin specific privileges."""

    @pytest.mark.asyncio
    async def test_super_admin_can_create_admin(
        self, client: AsyncClient, super_admin_token
    ):
        """Test that super admin can create admin users."""
        response = await client.post(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {super_admin_token}"},
            json={
                "username": "newadmin",
                "email": "newadmin@example.com",
                "password": "adminpassword123",
                "role": "admin",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "admin"

    @pytest.mark.asyncio
    async def test_admin_cannot_create_super_admin(
        self, client: AsyncClient, admin_token
    ):
        """Test that regular admin cannot create super admin."""
        response = await client.post(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "username": "newsuperadmin",
                "email": "newsuperadmin@example.com",
                "password": "superpassword123",
                "role": "super_admin",
            },
        )

        assert response.status_code == 400  # Invalid role


class TestUserDeactivation:
    """Tests for user deactivation."""

    @pytest.mark.asyncio
    async def test_admin_can_deactivate_user(
        self, client: AsyncClient, admin_token, test_normal_user
    ):
        """Test that admin can deactivate a user."""
        response = await client.delete(
            f"/api/v1/users/{test_normal_user.user_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_cannot_deactivate_self(
        self, client: AsyncClient, admin_token, test_admin
    ):
        """Test that admin cannot deactivate themselves."""
        response = await client.delete(
            f"/api/v1/users/{test_admin.user_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 400


class TestScopeRepository:
    """Tests for UserScopeRepository methods."""

    @pytest.mark.asyncio
    async def test_add_scope(self, test_session, test_normal_user, test_school):
        """Test adding a scope via repository."""
        from app.repositories.user_repository import UserScopeRepository

        repo = UserScopeRepository(test_session)
        scope = await repo.add_scope(
            user_id=test_normal_user.user_id,
            scope_type="school",
            scope_value=str(test_school.school_id),
            granted_by=1,
        )

        assert scope.scope_id is not None
        assert scope.scope_type == "school"

    @pytest.mark.asyncio
    async def test_get_user_scopes(self, test_session, test_normal_user, test_school):
        """Test getting user scopes."""
        from app.repositories.user_repository import UserScopeRepository

        repo = UserScopeRepository(test_session)

        # Add a scope first
        await repo.add_scope(
            user_id=test_normal_user.user_id,
            scope_type="school",
            scope_value=str(test_school.school_id),
            granted_by=1,
        )

        # Get scopes
        scopes = await repo.get_user_scopes(test_normal_user.user_id)

        assert len(scopes) >= 1

    @pytest.mark.asyncio
    async def test_remove_scope(self, test_session, test_normal_user, test_school):
        """Test removing a scope."""
        from app.repositories.user_repository import UserScopeRepository

        repo = UserScopeRepository(test_session)

        # Add a scope first
        scope = await repo.add_scope(
            user_id=test_normal_user.user_id,
            scope_type="school",
            scope_value=str(test_school.school_id),
            granted_by=1,
        )

        # Remove it
        success = await repo.remove_scope(scope.scope_id)
        assert success is True

        # Verify removal
        scopes = await repo.get_user_scopes(test_normal_user.user_id, active_only=True)
        active_scope_ids = [s.scope_id for s in scopes]
        assert scope.scope_id not in active_scope_ids
