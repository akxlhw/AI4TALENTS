"""
Tests for Tech Domain API endpoints.
技术领域API测试
"""
import pytest
from httpx import AsyncClient

from app.models.iam import UserAccount
from app.models.tech_domain import TechDomain, TechDirection
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
async def test_tech_domain(test_session):
    """Create a test tech domain with direction."""
    domain = TechDomain(
        domain_code="AI",
        domain_name="人工智能",
        domain_name_en="Artificial Intelligence",
        domain_desc="AI related technologies",
        is_enabled=True,
        sort_order=1,
    )
    test_session.add(domain)
    await test_session.flush()

    direction = TechDirection(
        tech_domain_id=domain.tech_domain_id,
        direction_code="AI-ML",
        direction_name="机器学习",
        direction_name_en="Machine Learning",
        is_enabled=True,
        sort_order=1,
    )
    test_session.add(direction)
    await test_session.commit()

    return {"domain": domain, "direction": direction}


@pytest.fixture
async def test_tech_domain2(test_session):
    """Create a second test tech domain."""
    domain = TechDomain(
        domain_code="NLP",
        domain_name="自然语言处理",
        domain_name_en="Natural Language Processing",
        domain_desc="NLP related technologies",
        is_enabled=True,
        sort_order=2,
    )
    test_session.add(domain)
    await test_session.commit()
    return domain


class TestListTechDomains:
    """Tests for GET /tech-domains endpoint."""

    @pytest.mark.asyncio
    async def test_list_tech_domains_success(
        self, client: AsyncClient, test_tech_domain
    ):
        """Test listing tech domains."""
        response = await client.get("/api/v1/tech-domains")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_list_tech_domains_includes_directions(
        self, client: AsyncClient, test_tech_domain
    ):
        """Test that tech domains include their directions."""
        response = await client.get("/api/v1/tech-domains")

        assert response.status_code == 200
        data = response.json()

        ai_domain = next(
            (d for d in data["items"] if d["domain_code"] == "AI"), None
        )
        assert ai_domain is not None
        assert len(ai_domain["directions"]) >= 1
        assert ai_domain["directions"][0]["direction_name"] == "机器学习"

    @pytest.mark.asyncio
    async def test_list_tech_domains_empty(self, client: AsyncClient):
        """Test listing when no tech domains exist."""
        response = await client.get("/api/v1/tech-domains")

        # Should still return valid response structure
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)


class TestGetTechDomain:
    """Tests for GET /tech-domains/{domain_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_tech_domain_success(
        self, client: AsyncClient, test_tech_domain
    ):
        """Test getting a specific tech domain."""
        domain_id = test_tech_domain["domain"].tech_domain_id

        response = await client.get(f"/api/v1/tech-domains/{domain_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["tech_domain_id"] == domain_id
        assert data["domain_code"] == "AI"
        assert data["domain_name"] == "人工智能"

    @pytest.mark.asyncio
    async def test_get_tech_domain_not_found(self, client: AsyncClient):
        """Test getting a non-existent tech domain."""
        response = await client.get("/api/v1/tech-domains/99999")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestTechDomainSummary:
    """Tests for GET /tech-domains/summary endpoint."""

    @pytest.mark.asyncio
    async def test_get_summary_success(self, client: AsyncClient, test_tech_domain):
        """Test getting tech domain summary."""
        response = await client.get("/api/v1/tech-domains/summary")

        assert response.status_code == 200
        data = response.json()
        assert "domain_count" in data
        assert "direction_count" in data
        assert "talent_count" in data

    @pytest.mark.asyncio
    async def test_get_summary_counts_correct(
        self, client: AsyncClient, test_tech_domain, test_tech_domain2
    ):
        """Test that summary counts are correct."""
        response = await client.get("/api/v1/tech-domains/summary")

        assert response.status_code == 200
        data = response.json()
        # Should have at least 2 domains (AI and NLP)
        assert data["domain_count"] >= 2
        # Should have at least 1 direction (ML under AI)
        assert data["direction_count"] >= 1


class TestOverallStats:
    """Tests for GET /tech-domains/overall-stats endpoint."""

    @pytest.mark.asyncio
    async def test_get_overall_stats_success(self, client: AsyncClient):
        """Test getting overall statistics."""
        response = await client.get("/api/v1/tech-domains/overall-stats")

        assert response.status_code == 200
        data = response.json()
        assert "professor_count" in data
        assert "student_count" in data
        assert "country_count" in data
        assert "school_count" in data


class TestOverallCountries:
    """Tests for GET /tech-domains/overall-countries endpoint."""

    @pytest.mark.asyncio
    async def test_get_overall_countries_success(self, client: AsyncClient):
        """Test getting overall country distribution."""
        response = await client.get("/api/v1/tech-domains/overall-countries")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)


class TestOverallSchools:
    """Tests for GET /tech-domains/overall-schools endpoint."""

    @pytest.mark.asyncio
    async def test_get_overall_schools_success(self, client: AsyncClient):
        """Test getting overall school distribution."""
        response = await client.get("/api/v1/tech-domains/overall-schools")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_get_overall_schools_pagination(self, client: AsyncClient):
        """Test pagination for school distribution."""
        response = await client.get(
            "/api/v1/tech-domains/overall-schools?page=1&page_size=10"
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data


class TestOverallTalents:
    """Tests for GET /tech-domains/overall-talents endpoint."""

    @pytest.mark.asyncio
    async def test_get_overall_talents_success(self, client: AsyncClient):
        """Test getting overall talent list."""
        response = await client.get("/api/v1/tech-domains/overall-talents")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data

    @pytest.mark.asyncio
    async def test_get_overall_talents_with_filters(
        self, client: AsyncClient
    ):
        """Test getting talent list with filters."""
        response = await client.get(
            "/api/v1/tech-domains/overall-talents",
            params={
                "country_code": "US",
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
            "/api/v1/tech-domains/overall-talents?page=1&page_size=10"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10


class TestDomainStats:
    """Tests for GET /tech-domains/{domain_id}/stats endpoint."""

    @pytest.mark.asyncio
    async def test_get_domain_stats_success(
        self, client: AsyncClient, test_tech_domain
    ):
        """Test getting domain statistics."""
        domain_id = test_tech_domain["domain"].tech_domain_id

        response = await client.get(f"/api/v1/tech-domains/{domain_id}/stats")

        assert response.status_code == 200
        data = response.json()
        assert "talent_count" in data
        assert "country_count" in data
        assert "school_count" in data

    @pytest.mark.asyncio
    async def test_get_domain_stats_not_found(self, client: AsyncClient):
        """Test getting stats for non-existent domain."""
        response = await client.get("/api/v1/tech-domains/99999/stats")

        assert response.status_code == 404


class TestDomainCountries:
    """Tests for GET /tech-domains/{domain_id}/countries endpoint."""

    @pytest.mark.asyncio
    async def test_get_domain_countries_success(
        self, client: AsyncClient, test_tech_domain
    ):
        """Test getting domain country distribution."""
        domain_id = test_tech_domain["domain"].tech_domain_id

        response = await client.get(
            f"/api/v1/tech-domains/{domain_id}/countries"
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    @pytest.mark.asyncio
    async def test_get_domain_countries_not_found(self, client: AsyncClient):
        """Test getting countries for non-existent domain."""
        response = await client.get("/api/v1/tech-domains/99999/countries")

        assert response.status_code == 404


class TestDomainSchools:
    """Tests for GET /tech-domains/{domain_id}/schools endpoint."""

    @pytest.mark.asyncio
    async def test_get_domain_schools_success(
        self, client: AsyncClient, test_tech_domain
    ):
        """Test getting domain school distribution."""
        domain_id = test_tech_domain["domain"].tech_domain_id

        response = await client.get(
            f"/api/v1/tech-domains/{domain_id}/schools"
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_get_domain_schools_with_filters(
        self, client: AsyncClient, test_tech_domain
    ):
        """Test getting schools with country filter."""
        domain_id = test_tech_domain["domain"].tech_domain_id

        response = await client.get(
            f"/api/v1/tech-domains/{domain_id}/schools",
            params={"country_code": "US"},
        )

        assert response.status_code == 200


class TestDomainTalents:
    """Tests for GET /tech-domains/{domain_id}/talents endpoint."""

    @pytest.mark.asyncio
    async def test_get_domain_talents_success(
        self, client: AsyncClient, test_tech_domain
    ):
        """Test getting domain talent list."""
        domain_id = test_tech_domain["domain"].tech_domain_id

        response = await client.get(
            f"/api/v1/tech-domains/{domain_id}/talents"
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_get_domain_talents_with_filters(
        self, client: AsyncClient, test_tech_domain
    ):
        """Test getting talents with filters."""
        domain_id = test_tech_domain["domain"].tech_domain_id

        response = await client.get(
            f"/api/v1/tech-domains/{domain_id}/talents",
            params={
                "country_code": "US",
                "role_type": "professor",
                "keyword": "AI",
            },
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_domain_talents_not_found(self, client: AsyncClient):
        """Test getting talents for non-existent domain."""
        response = await client.get("/api/v1/tech-domains/99999/talents")

        assert response.status_code == 404


class TestTechDomainRepository:
    """Tests for TechDomainRepository methods."""

    @pytest.mark.asyncio
    async def test_get_all_domains(self, test_session, test_tech_domain):
        """Test getting all domains."""
        from app.repositories.tech_domain_repository import TechDomainRepository

        repo = TechDomainRepository(test_session)
        domains = await repo.get_all_domains()

        assert len(domains) >= 1
        assert any(d.domain_code == "AI" for d in domains)

    @pytest.mark.asyncio
    async def test_get_domain_by_id(self, test_session, test_tech_domain):
        """Test getting domain by ID."""
        from app.repositories.tech_domain_repository import TechDomainRepository

        repo = TechDomainRepository(test_session)
        domain_id = test_tech_domain["domain"].tech_domain_id

        domain = await repo.get_domain_by_id(domain_id)

        assert domain is not None
        assert domain.domain_code == "AI"

    @pytest.mark.asyncio
    async def test_get_domain_by_id_not_found(self, test_session):
        """Test getting non-existent domain."""
        from app.repositories.tech_domain_repository import TechDomainRepository

        repo = TechDomainRepository(test_session)
        domain = await repo.get_domain_by_id(99999)

        assert domain is None

    @pytest.mark.asyncio
    async def test_get_domain_stats(self, test_session, test_tech_domain):
        """Test getting domain statistics."""
        from app.repositories.tech_domain_repository import TechDomainRepository

        repo = TechDomainRepository(test_session)
        domain_id = test_tech_domain["domain"].tech_domain_id

        stats = await repo.get_domain_stats(domain_id)

        assert "talent_count" in stats
        assert "country_count" in stats
        assert "school_count" in stats
