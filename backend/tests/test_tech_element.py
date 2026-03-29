"""
Tests for Tech Element API endpoints.
技术要素API测试
"""
import pytest
from httpx import AsyncClient

from app.models.iam import UserAccount
from app.models.tech_element import TechElement, TechDirection
from app.models.enums import UserRoleType
from app.core.auth import hash_password


@pytest.fixture
async def test_user(test_session):
    """Create a test user."""
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
async def test_tech_element(test_session):
    """Create a test tech element with direction."""
    element = TechElement(
        element_code="AI",
        element_name="人工智能",
        element_name_en="Artificial Intelligence",
        element_desc="AI related technologies",
        is_enabled=True,
        sort_order=1,
    )
    test_session.add(element)
    await test_session.flush()

    direction = TechDirection(
        tech_element_id=element.tech_element_id,
        direction_code="AI-ML",
        direction_name="机器学习",
        direction_name_en="Machine Learning",
        is_enabled=True,
        sort_order=1,
    )
    test_session.add(direction)
    await test_session.commit()

    return {"element": element, "direction": direction}


@pytest.fixture
async def test_tech_element2(test_session):
    """Create a second test tech element."""
    element = TechElement(
        element_code="NLP",
        element_name="自然语言处理",
        element_name_en="Natural Language Processing",
        element_desc="NLP related technologies",
        is_enabled=True,
        sort_order=2,
    )
    test_session.add(element)
    await test_session.commit()
    return element


class TestListTechElements:
    """Tests for GET /tech-elements endpoint."""

    @pytest.mark.asyncio
    async def test_list_tech_elements_success(
        self, client: AsyncClient, test_tech_element
    ):
        """Test listing tech elements."""
        response = await client.get("/api/v1/tech-elements")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_list_tech_elements_includes_directions(
        self, client: AsyncClient, test_tech_element
    ):
        """Test that tech elements include their directions."""
        response = await client.get("/api/v1/tech-elements")

        assert response.status_code == 200
        data = response.json()

        ai_element = next(
            (e for e in data["items"] if e["element_code"] == "AI"), None
        )
        assert ai_element is not None
        assert len(ai_element["directions"]) >= 1
        assert ai_element["directions"][0]["direction_name"] == "机器学习"

    @pytest.mark.asyncio
    async def test_list_tech_elements_empty(self, client: AsyncClient):
        """Test listing when no tech elements exist."""
        response = await client.get("/api/v1/tech-elements")

        # Should still return valid response structure
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)


class TestGetTechElement:
    """Tests for GET /tech-elements/{element_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_tech_element_success(
        self, client: AsyncClient, test_tech_element
    ):
        """Test getting a specific tech element."""
        element_id = test_tech_element["element"].tech_element_id

        response = await client.get(f"/api/v1/tech-elements/{element_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["tech_element_id"] == element_id
        assert data["element_code"] == "AI"
        assert data["element_name"] == "人工智能"

    @pytest.mark.asyncio
    async def test_get_tech_element_not_found(self, client: AsyncClient):
        """Test getting a non-existent tech element."""
        response = await client.get("/api/v1/tech-elements/99999")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestTechElementSummary:
    """Tests for GET /tech-elements/summary endpoint."""

    @pytest.mark.asyncio
    async def test_get_summary_success(self, client: AsyncClient, test_tech_element):
        """Test getting tech element summary."""
        response = await client.get("/api/v1/tech-elements/summary")

        assert response.status_code == 200
        data = response.json()
        assert "element_count" in data
        assert "direction_count" in data
        assert "talent_count" in data

    @pytest.mark.asyncio
    async def test_get_summary_counts_correct(
        self, client: AsyncClient, test_tech_element, test_tech_element2
    ):
        """Test that summary counts are correct."""
        response = await client.get("/api/v1/tech-elements/summary")

        assert response.status_code == 200
        data = response.json()
        # Should have at least 2 elements (AI and NLP)
        assert data["element_count"] >= 2
        # Should have at least 1 direction (ML under AI)
        assert data["direction_count"] >= 1


class TestOverallStats:
    """Tests for GET /tech-elements/overall-stats endpoint."""

    @pytest.mark.asyncio
    async def test_get_overall_stats_success(self, client: AsyncClient):
        """Test getting overall statistics."""
        response = await client.get("/api/v1/tech-elements/overall-stats")

        assert response.status_code == 200
        data = response.json()
        assert "professor_count" in data
        assert "student_count" in data
        assert "country_count" in data
        assert "school_count" in data


class TestOverallCountries:
    """Tests for GET /tech-elements/overall-countries endpoint."""

    @pytest.mark.asyncio
    async def test_get_overall_countries_success(self, client: AsyncClient):
        """Test getting overall country distribution."""
        response = await client.get("/api/v1/tech-elements/overall-countries")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)


class TestOverallSchools:
    """Tests for GET /tech-elements/overall-schools endpoint."""

    @pytest.mark.asyncio
    async def test_get_overall_schools_success(self, client: AsyncClient):
        """Test getting overall school distribution."""
        response = await client.get("/api/v1/tech-elements/overall-schools")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_get_overall_schools_pagination(self, client: AsyncClient):
        """Test pagination for school distribution."""
        response = await client.get(
            "/api/v1/tech-elements/overall-schools?page=1&page_size=10"
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data


class TestOverallTalents:
    """Tests for GET /tech-elements/overall-talents endpoint."""

    @pytest.mark.asyncio
    async def test_get_overall_talents_success(self, client: AsyncClient):
        """Test getting overall talent list."""
        response = await client.get("/api/v1/tech-elements/overall-talents")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data

    @pytest.mark.asyncio
    async def test_get_overall_talents_with_filters(
        self, client: AsyncClient, sample_country
    ):
        """Test getting talent list with filters."""
        response = await client.get(
            "/api/v1/tech-elements/overall-talents",
            params={
                "country_id": sample_country.country_id,
                "role_type": "professor",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    @pytest.mark.asyncio
    async def test_get_overall_talents_pagination(self, client: AsyncClient):
        """Test pagination for talent list."""
        response = await client.get(
            "/api/v1/tech-elements/overall-talents?page=1&page_size=10"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10


class TestElementStats:
    """Tests for GET /tech-elements/{element_id}/stats endpoint."""

    @pytest.mark.asyncio
    async def test_get_element_stats_success(
        self, client: AsyncClient, test_tech_element
    ):
        """Test getting element statistics."""
        element_id = test_tech_element["element"].tech_element_id

        response = await client.get(f"/api/v1/tech-elements/{element_id}/stats")

        assert response.status_code == 200
        data = response.json()
        assert "talent_count" in data
        assert "country_count" in data
        assert "school_count" in data

    @pytest.mark.asyncio
    async def test_get_element_stats_not_found(self, client: AsyncClient):
        """Test getting stats for non-existent element."""
        response = await client.get("/api/v1/tech-elements/99999/stats")

        assert response.status_code == 404


class TestElementCountries:
    """Tests for GET /tech-elements/{element_id}/countries endpoint."""

    @pytest.mark.asyncio
    async def test_get_element_countries_success(
        self, client: AsyncClient, test_tech_element
    ):
        """Test getting element country distribution."""
        element_id = test_tech_element["element"].tech_element_id

        response = await client.get(
            f"/api/v1/tech-elements/{element_id}/countries"
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    @pytest.mark.asyncio
    async def test_get_element_countries_not_found(self, client: AsyncClient):
        """Test getting countries for non-existent element."""
        response = await client.get("/api/v1/tech-elements/99999/countries")

        assert response.status_code == 404


class TestElementSchools:
    """Tests for GET /tech-elements/{element_id}/schools endpoint."""

    @pytest.mark.asyncio
    async def test_get_element_schools_success(
        self, client: AsyncClient, test_tech_element
    ):
        """Test getting element school distribution."""
        element_id = test_tech_element["element"].tech_element_id

        response = await client.get(
            f"/api/v1/tech-elements/{element_id}/schools"
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_get_element_schools_with_filters(
        self, client: AsyncClient, test_tech_element, sample_country
    ):
        """Test getting schools with country filter."""
        element_id = test_tech_element["element"].tech_element_id

        response = await client.get(
            f"/api/v1/tech-elements/{element_id}/schools",
            params={"country_id": sample_country.country_id},
        )

        assert response.status_code == 200


class TestElementTalents:
    """Tests for GET /tech-elements/{element_id}/talents endpoint."""

    @pytest.mark.asyncio
    async def test_get_element_talents_success(
        self, client: AsyncClient, test_tech_element
    ):
        """Test getting element talent list."""
        element_id = test_tech_element["element"].tech_element_id

        response = await client.get(
            f"/api/v1/tech-elements/{element_id}/talents"
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_get_element_talents_with_filters(
        self, client: AsyncClient, test_tech_element, sample_country
    ):
        """Test getting talents with filters."""
        element_id = test_tech_element["element"].tech_element_id

        response = await client.get(
            f"/api/v1/tech-elements/{element_id}/talents",
            params={
                "country_id": sample_country.country_id,
                "role_type": "professor",
                "keyword": "AI",
            },
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_element_talents_not_found(self, client: AsyncClient):
        """Test getting talents for non-existent element."""
        response = await client.get("/api/v1/tech-elements/99999/talents")

        assert response.status_code == 404


class TestTechElementRepository:
    """Tests for TechElementRepository methods."""

    @pytest.mark.asyncio
    async def test_get_all_elements(self, test_session, test_tech_element):
        """Test getting all elements."""
        from app.repositories.tech_element_repository import TechElementRepository

        repo = TechElementRepository(test_session)
        elements = await repo.get_all_elements()

        assert len(elements) >= 1
        assert any(e.element_code == "AI" for e in elements)

    @pytest.mark.asyncio
    async def test_get_element_by_id(self, test_session, test_tech_element):
        """Test getting element by ID."""
        from app.repositories.tech_element_repository import TechElementRepository

        repo = TechElementRepository(test_session)
        element_id = test_tech_element["element"].tech_element_id

        element = await repo.get_element_by_id(element_id)

        assert element is not None
        assert element.element_code == "AI"

    @pytest.mark.asyncio
    async def test_get_element_by_id_not_found(self, test_session):
        """Test getting non-existent element."""
        from app.repositories.tech_element_repository import TechElementRepository

        repo = TechElementRepository(test_session)
        element = await repo.get_element_by_id(99999)

        assert element is None

    @pytest.mark.asyncio
    async def test_get_element_stats(self, test_session, test_tech_element):
        """Test getting element statistics."""
        from app.repositories.tech_element_repository import TechElementRepository

        repo = TechElementRepository(test_session)
        element_id = test_tech_element["element"].tech_element_id

        stats = await repo.get_element_stats(element_id)

        assert "talent_count" in stats
        assert "country_count" in stats
        assert "school_count" in stats
