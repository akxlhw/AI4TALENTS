"""
Tests for API endpoints (Overview, Countries, Schools, Talents, Search).
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.country import Country
from app.models.school import School
from app.models.talent import Talent, RoleProfile
from app.models.statistics import OverviewStatSnapshot, SchoolStatSnapshot
from app.models.enums import RoleType


class TestOverviewEndpoint:
    """Tests for Overview API."""

    @pytest.mark.asyncio
    async def test_overview_no_stats(self, client: AsyncClient):
        """Test overview when no statistics available."""
        response = await client.get("/api/v1/overview")

        # Should return 404 when no stats
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_overview_with_stats(
        self, client: AsyncClient, test_session: AsyncSession
    ):
        """Test overview with statistics."""
        # Create test statistics
        stats = OverviewStatSnapshot(
            stat_version="v20240101",
            generated_at="2024-01-01T00:00:00",
            school_count=100,
            professor_count=1000,
            student_count=5000,
            talent_count=6100,
            is_active=1,
        )
        test_session.add(stats)
        await test_session.commit()

        response = await client.get("/api/v1/overview")

        assert response.status_code == 200
        data = response.json()

        assert data["version"] == "v20240101"
        assert data["stats"]["school_count"] == 100
        assert data["stats"]["professor_count"] == 1000
        assert data["stats"]["student_count"] == 5000
        assert data["stats"]["talent_count"] == 6100


class TestCountriesEndpoint:
    """Tests for Countries API."""

    @pytest.mark.asyncio
    async def test_list_countries_empty(self, client: AsyncClient):
        """Test countries list when empty."""
        response = await client.get("/api/v1/countries")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 0
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_list_countries_with_data(
        self, client: AsyncClient, test_session: AsyncSession
    ):
        """Test countries list with data."""
        # Create test countries
        country1 = Country(
            country_code="US",
            country_name_cn="美国",
            country_name_en="United States",
            sort_order=1,
        )
        country2 = Country(
            country_code="CN",
            country_name_cn="中国",
            country_name_en="China",
            sort_order=2,
        )
        test_session.add_all([country1, country2])
        await test_session.commit()

        response = await client.get("/api/v1/countries")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 2
        assert len(data["items"]) == 2
        assert data["items"][0]["country_code"] == "US"


class TestSchoolsEndpoint:
    """Tests for Schools API."""

    @pytest.mark.asyncio
    async def test_list_schools_empty(self, client: AsyncClient):
        """Test schools list when empty."""
        response = await client.get("/api/v1/schools")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 0
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_list_schools_with_data(
        self, client: AsyncClient, test_session: AsyncSession
    ):
        """Test schools list with data."""
        # Create test country
        country = Country(
            country_code="US",
            country_name_cn="美国",
            country_name_en="United States",
        )
        test_session.add(country)
        await test_session.flush()

        # Create test schools
        school1 = School(
            school_name="MIT",
            country_id=country.country_id,
            professor_count=500,
            student_count=2000,
        )
        school2 = School(
            school_name="Stanford University",
            country_id=country.country_id,
            professor_count=400,
            student_count=1500,
        )
        test_session.add_all([school1, school2])
        await test_session.commit()

        response = await client.get("/api/v1/schools")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 2
        assert len(data["items"]) == 2

    @pytest.mark.asyncio
    async def test_get_school_detail(
        self, client: AsyncClient, test_session: AsyncSession
    ):
        """Test get school detail."""
        # Create test data
        country = Country(
            country_code="US",
            country_name_cn="美国",
            country_name_en="United States",
        )
        test_session.add(country)
        await test_session.flush()

        school = School(
            school_name="MIT",
            country_id=country.country_id,
            school_intro="MIT is a research university",
            homepage_url="https://mit.edu",
        )
        test_session.add(school)
        await test_session.commit()

        response = await client.get(f"/api/v1/schools/{school.school_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["school_name"] == "MIT"
        assert data["country_name"] == "美国"
        assert data["homepage_url"] == "https://mit.edu"

    @pytest.mark.asyncio
    async def test_get_school_not_found(self, client: AsyncClient):
        """Test get school that doesn't exist."""
        response = await client.get("/api/v1/schools/99999")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_schools_filter_by_country(
        self, client: AsyncClient, test_session: AsyncSession
    ):
        """Test filtering schools by country."""
        # Create test countries
        us = Country(country_code="US", country_name_cn="美国")
        cn = Country(country_code="CN", country_name_cn="中国")
        test_session.add_all([us, cn])
        await test_session.flush()

        # Create test schools
        school1 = School(school_name="MIT", country_id=us.country_id)
        school2 = School(school_name="Tsinghua", country_id=cn.country_id)
        test_session.add_all([school1, school2])
        await test_session.commit()

        # Filter by US
        response = await client.get(f"/api/v1/schools?country_id={us.country_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1
        assert data["items"][0]["school_name"] == "MIT"


class TestTalentsEndpoint:
    """Tests for Talents API."""

    @pytest.mark.asyncio
    async def test_list_talents_empty(self, client: AsyncClient):
        """Test talents list when empty."""
        response = await client.get("/api/v1/talents")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 0
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_list_talents_with_data(
        self, client: AsyncClient, test_session: AsyncSession
    ):
        """Test talents list with data."""
        # Create test data
        country = Country(country_code="US", country_name_cn="美国")
        test_session.add(country)
        await test_session.flush()

        school = School(school_name="MIT", country_id=country.country_id)
        test_session.add(school)
        await test_session.flush()

        talent1 = Talent(
            name="John Doe",
            name_en="John Doe",
            school_id=school.school_id,
            role_type=RoleType.PROFESSOR.value,
            works_count=50,
            cited_by_count=1000,
            h_index=20,
            topic_tags=["Machine Learning", "AI"],
        )
        talent2 = Talent(
            name="Jane Smith",
            school_id=school.school_id,
            role_type=RoleType.STUDENT.value,
            works_count=2,
            cited_by_count=10,
        )
        test_session.add_all([talent1, talent2])
        await test_session.commit()

        response = await client.get("/api/v1/talents")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 2
        assert len(data["items"]) == 2

    @pytest.mark.asyncio
    async def test_get_talent_detail(
        self, client: AsyncClient, test_session: AsyncSession
    ):
        """Test get talent detail."""
        # Create test data
        country = Country(country_code="US", country_name_cn="美国")
        test_session.add(country)
        await test_session.flush()

        school = School(school_name="MIT", country_id=country.country_id)
        test_session.add(school)
        await test_session.flush()

        talent = Talent(
            name="John Doe",
            school_id=school.school_id,
            role_type=RoleType.PROFESSOR.value,
            works_count=50,
            cited_by_count=1000,
            research_interests="Machine Learning",
        )
        test_session.add(talent)
        await test_session.flush()

        # Add role profile
        profile = RoleProfile(
            talent_id=talent.talent_id,
            role_type=RoleType.PROFESSOR.value,
            role_reason="High citation count",
            academic_age=15,
        )
        test_session.add(profile)
        await test_session.commit()

        response = await client.get(f"/api/v1/talents/{talent.talent_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "John Doe"
        assert data["role_type"] == "professor"
        assert data["school_name"] == "MIT"
        assert data["research_interests"] == "Machine Learning"
        assert data["role_reason"] == "High citation count"
        assert data["academic_age"] == 15

    @pytest.mark.asyncio
    async def test_get_talent_not_found(self, client: AsyncClient):
        """Test get talent that doesn't exist."""
        response = await client.get("/api/v1/talents/99999")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_talents_filter_by_role(
        self, client: AsyncClient, test_session: AsyncSession
    ):
        """Test filtering talents by role type."""
        # Create test data
        country = Country(country_code="US", country_name_cn="美国")
        test_session.add(country)
        await test_session.flush()

        school = School(school_name="MIT", country_id=country.country_id)
        test_session.add(school)
        await test_session.flush()

        professor = Talent(
            name="Prof. Smith",
            school_id=school.school_id,
            role_type=RoleType.PROFESSOR.value,
            works_count=50,
        )
        student = Talent(
            name="Student John",
            school_id=school.school_id,
            role_type=RoleType.STUDENT.value,
            works_count=2,
        )
        test_session.add_all([professor, student])
        await test_session.commit()

        response = await client.get("/api/v1/talents?role_type=professor")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1
        assert data["items"][0]["role_type"] == "professor"


class TestSearchEndpoint:
    """Tests for Search API."""

    @pytest.mark.asyncio
    async def test_search_no_results(self, client: AsyncClient):
        """Test search with no results."""
        response = await client.get("/api/v1/search/talents?q=nonexistent")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 0
        assert data["items"] == []
        assert data["query"] == "nonexistent"

    @pytest.mark.asyncio
    async def test_search_with_results(
        self, client: AsyncClient, test_session: AsyncSession
    ):
        """Test search with results."""
        # Create test data
        country = Country(country_code="US", country_name_cn="美国")
        test_session.add(country)
        await test_session.flush()

        school = School(school_name="MIT", country_id=country.country_id)
        test_session.add(school)
        await test_session.flush()

        talent1 = Talent(
            name="John Smith",
            school_id=school.school_id,
            role_type=RoleType.PROFESSOR.value,
            cited_by_count=1000,
        )
        talent2 = Talent(
            name="Jane Doe",
            school_id=school.school_id,
            role_type=RoleType.STUDENT.value,
            cited_by_count=100,
        )
        test_session.add_all([talent1, talent2])
        await test_session.commit()

        response = await client.get("/api/v1/search/talents?q=John")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1
        assert "John" in data["items"][0]["name"]

    @pytest.mark.asyncio
    async def test_search_with_role_filter(
        self, client: AsyncClient, test_session: AsyncSession
    ):
        """Test search with role filter."""
        # Create test data
        country = Country(country_code="US", country_name_cn="美国")
        test_session.add(country)
        await test_session.flush()

        school = School(school_name="MIT", country_id=country.country_id)
        test_session.add(school)
        await test_session.flush()

        professor = Talent(
            name="John Smith",
            school_id=school.school_id,
            role_type=RoleType.PROFESSOR.value,
            cited_by_count=1000,
        )
        student = Talent(
            name="John Student",
            school_id=school.school_id,
            role_type=RoleType.STUDENT.value,
            cited_by_count=100,
        )
        test_session.add_all([professor, student])
        await test_session.commit()

        response = await client.get("/api/v1/search/talents?q=John&role_type=professor")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1
        assert data["items"][0]["role_type"] == "professor"

    @pytest.mark.asyncio
    async def test_search_missing_query(self, client: AsyncClient):
        """Test search without query parameter."""
        response = await client.get("/api/v1/search/talents")

        # Should return 422 (validation error)
        assert response.status_code == 422
