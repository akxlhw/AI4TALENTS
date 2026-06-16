"""
Tests for Favorites API endpoints.
收藏功能API测试
"""

import pytest
from httpx import AsyncClient

from app.core.auth import hash_password
from app.domains.academic.models.school import School
from app.domains.academic.models.talent import Talent
from app.domains.shared.models.enums import RoleType, UserRoleType, VisibilityStatus
from app.domains.shared.models.iam import UserAccount


@pytest.fixture
async def test_user(test_session):
    """Create a test user for favorites tests."""
    user = UserAccount(
        username="testuser",
        email="test@example.com",
        password_hash=hash_password("testpassword123"),
        role_type=UserRoleType.USER.value,
        is_active=True,
    )
    test_session.add(user)
    await test_session.commit()
    return user


@pytest.fixture
async def test_user_token(client: AsyncClient, test_user):
    """Get auth token for test user."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "testpassword123"},
    )
    return response.json()["access_token"]


@pytest.fixture
async def test_talent(test_session):
    """Create a test talent for favorites tests."""
    school = School(
        school_name="Test University",
        country_code="US",
        country_name="美国",
        is_visible=True,
    )
    test_session.add(school)
    await test_session.flush()

    talent = Talent(
        name="Test Talent",
        name_en="Test Talent",
        school_id=school.school_id,
        role_type=RoleType.PROFESSOR.value,
        works_count=50,
        cited_by_count=1000,
        h_index=20,
        visibility_status=VisibilityStatus.ACTIVE.value,
        is_visible=True,
    )
    test_session.add(talent)
    await test_session.commit()
    return {"talent": talent, "school": school}


@pytest.fixture
async def test_talent2(test_session):
    """Create a second test talent for favorites tests."""
    school = School(
        school_name="Test University 2",
        country_code="US",
        country_name="美国",
        is_visible=True,
    )
    test_session.add(school)
    await test_session.flush()

    talent = Talent(
        name="Test Talent 2",
        name_en="Test Talent 2",
        school_id=school.school_id,
        role_type=RoleType.STUDENT.value,
        works_count=5,
        cited_by_count=50,
        h_index=3,
        visibility_status=VisibilityStatus.ACTIVE.value,
        is_visible=True,
    )
    test_session.add(talent)
    await test_session.commit()
    return talent


class TestAddFavorite:
    """Tests for POST /favorites endpoint."""

    @pytest.mark.asyncio
    async def test_add_favorite_success(self, client: AsyncClient, test_user_token, test_talent):
        """Test successfully adding a talent to favorites."""
        talent_id = test_talent["talent"].talent_id

        response = await client.post(
            "/api/v1/favorites",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={"talent_id": talent_id, "notes": "Great candidate"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["talent_id"] == talent_id
        assert data["name"] == "Test Talent"
        assert data["notes"] == "Great candidate"

    @pytest.mark.asyncio
    async def test_add_favorite_duplicate(self, client: AsyncClient, test_user_token, test_talent):
        """Test adding same talent twice returns error."""
        talent_id = test_talent["talent"].talent_id

        # First add
        await client.post(
            "/api/v1/favorites",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={"talent_id": talent_id},
        )

        # Second add (should fail)
        response = await client.post(
            "/api/v1/favorites",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={"talent_id": talent_id},
        )

        assert response.status_code == 400
        assert "已在收藏列表中" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_add_favorite_unauthenticated(self, client: AsyncClient, test_talent):
        """Test adding favorite without authentication."""
        talent_id = test_talent["talent"].talent_id

        response = await client.post(
            "/api/v1/favorites",
            json={"talent_id": talent_id},
        )

        assert response.status_code == 401


class TestListFavorites:
    """Tests for GET /favorites endpoint."""

    @pytest.mark.asyncio
    async def test_list_favorites_empty(self, client: AsyncClient, test_user_token):
        """Test listing favorites when empty."""
        response = await client.get(
            "/api/v1/favorites",
            headers={"Authorization": f"Bearer {test_user_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_list_favorites_with_data(
        self, client: AsyncClient, test_user_token, test_talent, test_talent2
    ):
        """Test listing favorites with data."""
        # Add two favorites
        await client.post(
            "/api/v1/favorites",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={"talent_id": test_talent["talent"].talent_id},
        )
        await client.post(
            "/api/v1/favorites",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={"talent_id": test_talent2.talent_id},
        )

        response = await client.get(
            "/api/v1/favorites",
            headers={"Authorization": f"Bearer {test_user_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    @pytest.mark.asyncio
    async def test_list_favorites_with_role_filter(
        self, client: AsyncClient, test_user_token, test_talent, test_talent2
    ):
        """Test filtering favorites by role type."""
        # Add two favorites with different roles
        await client.post(
            "/api/v1/favorites",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={"talent_id": test_talent["talent"].talent_id},
        )
        await client.post(
            "/api/v1/favorites",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={"talent_id": test_talent2.talent_id},
        )

        response = await client.get(
            "/api/v1/favorites?role_type=professor",
            headers={"Authorization": f"Bearer {test_user_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["role_type"] == "professor"

    @pytest.mark.asyncio
    async def test_list_favorites_pagination(
        self, client: AsyncClient, test_user_token, test_talent, test_talent2
    ):
        """Test pagination of favorites list."""
        # Add two favorites
        await client.post(
            "/api/v1/favorites",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={"talent_id": test_talent["talent"].talent_id},
        )
        await client.post(
            "/api/v1/favorites",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={"talent_id": test_talent2.talent_id},
        )

        response = await client.get(
            "/api/v1/favorites?page=1&page_size=1",
            headers={"Authorization": f"Bearer {test_user_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 1

    @pytest.mark.asyncio
    async def test_list_favorites_unauthenticated(self, client: AsyncClient):
        """Test listing favorites without authentication."""
        response = await client.get("/api/v1/favorites")
        assert response.status_code == 401


class TestGetFavoriteIds:
    """Tests for GET /favorites/ids endpoint."""

    @pytest.mark.asyncio
    async def test_get_favorite_ids_empty(self, client: AsyncClient, test_user_token):
        """Test getting favorite IDs when empty."""
        response = await client.get(
            "/api/v1/favorites/ids",
            headers={"Authorization": f"Bearer {test_user_token}"},
        )

        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_get_favorite_ids_with_data(
        self, client: AsyncClient, test_user_token, test_talent
    ):
        """Test getting favorite IDs with data."""
        talent_id = test_talent["talent"].talent_id

        await client.post(
            "/api/v1/favorites",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={"talent_id": talent_id},
        )

        response = await client.get(
            "/api/v1/favorites/ids",
            headers={"Authorization": f"Bearer {test_user_token}"},
        )

        assert response.status_code == 200
        assert talent_id in response.json()


class TestCheckFavorite:
    """Tests for GET /favorites/{talent_id}/check endpoint."""

    @pytest.mark.asyncio
    async def test_check_favorite_true(self, client: AsyncClient, test_user_token, test_talent):
        """Test checking a favorited talent returns true."""
        talent_id = test_talent["talent"].talent_id

        await client.post(
            "/api/v1/favorites",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={"talent_id": talent_id, "notes": "Test notes"},
        )

        response = await client.get(
            f"/api/v1/favorites/{talent_id}/check",
            headers={"Authorization": f"Bearer {test_user_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_favorited"] is True
        assert data["favorite_id"] is not None
        assert data["notes"] == "Test notes"

    @pytest.mark.asyncio
    async def test_check_favorite_false(self, client: AsyncClient, test_user_token, test_talent):
        """Test checking a non-favorited talent returns false."""
        talent_id = test_talent["talent"].talent_id

        response = await client.get(
            f"/api/v1/favorites/{talent_id}/check",
            headers={"Authorization": f"Bearer {test_user_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_favorited"] is False
        assert data["favorite_id"] is None


class TestUpdateFavorite:
    """Tests for PUT /favorites/{talent_id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_favorite_notes(self, client: AsyncClient, test_user_token, test_talent):
        """Test updating favorite notes."""
        talent_id = test_talent["talent"].talent_id

        # Add favorite first
        await client.post(
            "/api/v1/favorites",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={"talent_id": talent_id, "notes": "Original notes"},
        )

        # Update notes
        response = await client.put(
            f"/api/v1/favorites/{talent_id}",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={"notes": "Updated notes"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["notes"] == "Updated notes"

    @pytest.mark.asyncio
    async def test_update_favorite_not_found(
        self, client: AsyncClient, test_user_token, test_talent
    ):
        """Test updating a non-existent favorite."""
        talent_id = test_talent["talent"].talent_id

        response = await client.put(
            f"/api/v1/favorites/{talent_id}",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={"notes": "Updated notes"},
        )

        assert response.status_code == 404


class TestRemoveFavorite:
    """Tests for DELETE /favorites/{talent_id} endpoint."""

    @pytest.mark.asyncio
    async def test_remove_favorite_success(self, client: AsyncClient, test_user_token, test_talent):
        """Test successfully removing a favorite."""
        talent_id = test_talent["talent"].talent_id

        # Add favorite first
        await client.post(
            "/api/v1/favorites",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={"talent_id": talent_id},
        )

        # Remove favorite
        response = await client.delete(
            f"/api/v1/favorites/{talent_id}",
            headers={"Authorization": f"Bearer {test_user_token}"},
        )

        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify it's removed
        check_response = await client.get(
            f"/api/v1/favorites/{talent_id}/check",
            headers={"Authorization": f"Bearer {test_user_token}"},
        )
        assert check_response.json()["is_favorited"] is False

    @pytest.mark.asyncio
    async def test_remove_favorite_not_found(
        self, client: AsyncClient, test_user_token, test_talent
    ):
        """Test removing a non-existent favorite."""
        talent_id = test_talent["talent"].talent_id

        response = await client.delete(
            f"/api/v1/favorites/{talent_id}",
            headers={"Authorization": f"Bearer {test_user_token}"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_remove_favorite_unauthenticated(self, client: AsyncClient, test_talent):
        """Test removing favorite without authentication."""
        talent_id = test_talent["talent"].talent_id

        response = await client.delete(f"/api/v1/favorites/{talent_id}")
        assert response.status_code == 401


class TestFavoriteRepository:
    """Tests for FavoriteRepository methods."""

    @pytest.mark.asyncio
    async def test_add_favorite(self, test_session, test_user, test_talent):
        """Test adding favorite via repository."""
        from app.domains.academic.repositories.favorite_repository import FavoriteRepository

        repo = FavoriteRepository(test_session)
        favorite = await repo.add_favorite(
            user_id=test_user.user_id,
            talent_id=test_talent["talent"].talent_id,
            notes="Test notes",
        )

        assert favorite.favorite_id is not None
        assert favorite.user_id == test_user.user_id
        assert favorite.talent_id == test_talent["talent"].talent_id
        assert favorite.notes == "Test notes"

    @pytest.mark.asyncio
    async def test_get_by_user_and_talent(self, test_session, test_user, test_talent):
        """Test getting favorite by user and talent."""
        from app.domains.academic.repositories.favorite_repository import FavoriteRepository

        repo = FavoriteRepository(test_session)

        # Add favorite first
        await repo.add_favorite(
            user_id=test_user.user_id,
            talent_id=test_talent["talent"].talent_id,
        )

        # Get it back
        favorite = await repo.get_by_user_and_talent(
            user_id=test_user.user_id,
            talent_id=test_talent["talent"].talent_id,
        )

        assert favorite is not None
        assert favorite.user_id == test_user.user_id

    @pytest.mark.asyncio
    async def test_get_user_favorite_ids(self, test_session, test_user, test_talent, test_talent2):
        """Test getting all favorite IDs for a user."""
        from app.domains.academic.repositories.favorite_repository import FavoriteRepository

        repo = FavoriteRepository(test_session)

        # Add two favorites
        await repo.add_favorite(
            user_id=test_user.user_id,
            talent_id=test_talent["talent"].talent_id,
        )
        await repo.add_favorite(
            user_id=test_user.user_id,
            talent_id=test_talent2.talent_id,
        )

        # Get IDs
        ids = await repo.get_user_favorite_ids(test_user.user_id)

        assert len(ids) == 2
        assert test_talent["talent"].talent_id in ids
        assert test_talent2.talent_id in ids

    @pytest.mark.asyncio
    async def test_remove_favorite(self, test_session, test_user, test_talent):
        """Test removing favorite via repository."""
        from app.domains.academic.repositories.favorite_repository import FavoriteRepository

        repo = FavoriteRepository(test_session)

        # Add favorite first
        await repo.add_favorite(
            user_id=test_user.user_id,
            talent_id=test_talent["talent"].talent_id,
        )

        # Remove it
        removed = await repo.remove_favorite(
            user_id=test_user.user_id,
            talent_id=test_talent["talent"].talent_id,
        )

        assert removed is True

        # Verify it's soft-deleted
        favorite = await repo.get_by_user_and_talent(
            user_id=test_user.user_id,
            talent_id=test_talent["talent"].talent_id,
        )
        assert favorite is None
