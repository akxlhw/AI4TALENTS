"""
Tests for repository classes.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.country_repository import CountryRepository
from app.repositories.school_repository import SchoolRepository
from app.repositories.talent_repository import TalentRepository
from app.repositories.stat_repository import StatisticsRepository
from app.models.country import Country
from app.models.school import School
from app.models.talent import Talent, RoleProfile
from app.models.statistics import OverviewStatSnapshot, SchoolStatSnapshot
from app.models.enums import RoleType


class TestCountryRepository:
    """Tests for CountryRepository."""

    @pytest.fixture
    async def setup_data(self, test_session: AsyncSession):
        """Setup test data."""
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
        await test_session.flush()

        school1 = School(
            school_name="MIT",
            country_id=country1.country_id,
            professor_count=500,
        )
        school2 = School(
            school_name="Stanford",
            country_id=country1.school_id if hasattr(country1, 'school_id') else country1.country_id,
            professor_count=400,
        )
        school3 = School(
            school_name="Tsinghua",
            country_id=country2.country_id,
            professor_count=600,
        )
        test_session.add_all([school1, school2, school3])
        await test_session.commit()

        return country1, country2

    @pytest.mark.asyncio
    async def test_get_all(self, test_session: AsyncSession, setup_data):
        """Test get all countries."""
        repo = CountryRepository(test_session)
        countries = await repo.get_all()

        assert len(countries) == 2
        assert countries[0].country_code == "US"

    @pytest.mark.asyncio
    async def test_get_by_id(self, test_session: AsyncSession, setup_data):
        """Test get country by ID."""
        repo = CountryRepository(test_session)
        country = await repo.get_by_id(1)

        assert country is not None
        assert country.country_code == "US"

    @pytest.mark.asyncio
    async def test_get_by_code(self, test_session: AsyncSession, setup_data):
        """Test get country by code."""
        repo = CountryRepository(test_session)
        country = await repo.get_by_code("us")  # lowercase should work

        assert country is not None
        assert country.country_code == "US"

    @pytest.mark.asyncio
    async def test_get_with_school_counts(self, test_session: AsyncSession, setup_data):
        """Test get countries with school counts."""
        repo = CountryRepository(test_session)
        result = await repo.get_with_school_counts()

        assert len(result) == 2
        # Check that school counts are included
        us_data = next((r for r in result if r["country_code"] == "US"), None)
        assert us_data is not None
        assert us_data["school_count"] >= 1


class TestSchoolRepository:
    """Tests for SchoolRepository."""

    @pytest.fixture
    async def setup_data(self, test_session: AsyncSession):
        """Setup test data."""
        country = Country(
            country_code="US",
            country_name_cn="美国",
            country_name_en="United States",
        )
        test_session.add(country)
        await test_session.flush()

        school1 = School(
            school_name="MIT",
            country_id=country.country_id,
            professor_count=500,
            student_count=2000,
        )
        school2 = School(
            school_name="Stanford University",
            country_id=country.school_id if hasattr(country, 'school_id') else country.country_id,
            professor_count=400,
            student_count=1500,
        )
        test_session.add_all([school1, school2])
        await test_session.commit()

        return country, school1, school2

    @pytest.mark.asyncio
    async def test_get_list(self, test_session: AsyncSession, setup_data):
        """Test get school list."""
        repo = SchoolRepository(test_session)
        schools, total = await repo.get_list()

        assert total == 2
        assert len(schools) == 2

    @pytest.mark.asyncio
    async def test_get_list_with_country_filter(
        self, test_session: AsyncSession, setup_data
    ):
        """Test get school list with country filter."""
        country, _, _ = setup_data
        repo = SchoolRepository(test_session)
        schools, total = await repo.get_list(country_id=country.country_id)

        assert total == 2

    @pytest.mark.asyncio
    async def test_get_list_with_keyword(self, test_session: AsyncSession, setup_data):
        """Test get school list with keyword search."""
        repo = SchoolRepository(test_session)
        schools, total = await repo.get_list(keyword="MIT")

        assert total == 1
        assert schools[0].school_name == "MIT"

    @pytest.mark.asyncio
    async def test_get_by_id(self, test_session: AsyncSession, setup_data):
        """Test get school by ID."""
        _, school1, _ = setup_data
        repo = SchoolRepository(test_session)
        school = await repo.get_by_id(school1.school_id)

        assert school is not None
        assert school.school_name == "MIT"

    @pytest.mark.asyncio
    async def test_search(self, test_session: AsyncSession, setup_data):
        """Test school search."""
        repo = SchoolRepository(test_session)
        results = await repo.search("Stanford")

        assert len(results) == 1
        assert "Stanford" in results[0].school_name


class TestTalentRepository:
    """Tests for TalentRepository."""

    @pytest.fixture
    async def setup_data(self, test_session: AsyncSession):
        """Setup test data."""
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
        )
        talent2 = Talent(
            name="Jane Smith",
            school_id=school.school_id,
            role_type=RoleType.STUDENT.value,
            works_count=2,
            cited_by_count=10,
        )
        test_session.add_all([talent1, talent2])
        await test_session.flush()

        profile = RoleProfile(
            talent_id=talent1.talent_id,
            role_type=RoleType.PROFESSOR.value,
            role_reason="High citations",
        )
        test_session.add(profile)
        await test_session.commit()

        return country, school, talent1, talent2

    @pytest.mark.asyncio
    async def test_get_list(self, test_session: AsyncSession, setup_data):
        """Test get talent list."""
        repo = TalentRepository(test_session)
        talents, total = await repo.get_list()

        assert total == 2
        assert len(talents) == 2

    @pytest.mark.asyncio
    async def test_get_list_with_role_filter(
        self, test_session: AsyncSession, setup_data
    ):
        """Test get talent list with role filter."""
        repo = TalentRepository(test_session)
        talents, total = await repo.get_list(role_type=RoleType.PROFESSOR.value)

        assert total == 1
        assert talents[0].role_type == "professor"

    @pytest.mark.asyncio
    async def test_get_by_id(self, test_session: AsyncSession, setup_data):
        """Test get talent by ID."""
        _, _, talent1, _ = setup_data
        repo = TalentRepository(test_session)
        talent = await repo.get_by_id(talent1.talent_id)

        assert talent is not None
        assert talent.name == "John Doe"

    @pytest.mark.asyncio
    async def test_search(self, test_session: AsyncSession, setup_data):
        """Test talent search."""
        repo = TalentRepository(test_session)
        results = await repo.search("John")

        assert len(results) == 1
        assert results[0].name == "John Doe"

    @pytest.mark.asyncio
    async def test_get_role_profile(self, test_session: AsyncSession, setup_data):
        """Test get role profile."""
        _, _, talent1, _ = setup_data
        repo = TalentRepository(test_session)
        profile = await repo.get_role_profile(talent1.talent_id)

        assert profile is not None
        assert profile.role_reason == "High citations"


class TestStatisticsRepository:
    """Tests for StatisticsRepository."""

    @pytest.mark.asyncio
    async def test_get_active_overview_stats_empty(
        self, test_session: AsyncSession
    ):
        """Test get active stats when none exist."""
        repo = StatisticsRepository(test_session)
        stats = await repo.get_active_overview_stats()

        assert stats is None

    @pytest.mark.asyncio
    async def test_get_active_overview_stats(
        self, test_session: AsyncSession
    ):
        """Test get active overview stats."""
        # Create test stats
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

        repo = StatisticsRepository(test_session)
        result = await repo.get_active_overview_stats()

        assert result is not None
        assert result.stat_version == "v20240101"
        assert result.school_count == 100

    @pytest.mark.asyncio
    async def test_get_school_stats(
        self, test_session: AsyncSession
    ):
        """Test get school statistics."""
        # Create test data
        country = Country(country_code="US", country_name_cn="美国")
        test_session.add(country)
        await test_session.flush()

        school = School(school_name="MIT", country_id=country.country_id)
        test_session.add(school)
        await test_session.flush()

        stats = SchoolStatSnapshot(
            school_id=school.school_id,
            stat_version="v20240101",
            generated_at="2024-01-01T00:00:00",
            professor_count=500,
            student_count=2000,
            talent_count=2500,
            is_active=1,
        )
        test_session.add(stats)
        await test_session.commit()

        repo = StatisticsRepository(test_session)
        result = await repo.get_school_stats(school.school_id)

        assert result is not None
        assert result.professor_count == 500
        assert result.talent_count == 2500
