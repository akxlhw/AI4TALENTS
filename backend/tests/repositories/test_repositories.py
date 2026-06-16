"""
Tests for repository classes.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.academic.models.school import School
from app.domains.academic.models.statistics import OverviewStatSnapshot, SchoolStatSnapshot
from app.domains.academic.models.talent import RoleProfile, Talent
from app.domains.academic.repositories.school_repository import SchoolRepository
from app.domains.academic.repositories.stat_repository import StatisticsRepository
from app.domains.academic.repositories.talent_repository import TalentRepository
from app.domains.shared.models.enums import RoleType


class TestSchoolRepository:
    """Tests for SchoolRepository."""

    @pytest.fixture
    async def setup_data(self, test_session: AsyncSession):
        """Setup test data."""
        school1 = School(
            school_name="MIT",
            country_code="US",
            country_name="美国",
            professor_count=500,
            student_count=2000,
        )
        school2 = School(
            school_name="Stanford University",
            country_code="US",
            country_name="美国",
            professor_count=400,
            student_count=1500,
        )
        school3 = School(
            school_name="Tsinghua",
            country_code="CN",
            country_name="中国",
            professor_count=600,
        )
        test_session.add_all([school1, school2, school3])
        await test_session.commit()

        return school1, school2, school3

    @pytest.mark.asyncio
    async def test_get_list(self, test_session: AsyncSession, setup_data):
        """Test get school list."""
        repo = SchoolRepository(test_session)
        schools, total = await repo.get_list()

        assert total == 3
        assert len(schools) == 3

    @pytest.mark.asyncio
    async def test_get_list_with_country_filter(self, test_session: AsyncSession, setup_data):
        """Test get school list with country filter."""
        repo = SchoolRepository(test_session)
        schools, total = await repo.get_list(country_code="US")

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
        school1, _, _ = setup_data
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
        school = School(
            school_name="MIT",
            country_code="US",
            country_name="美国",
        )
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

        return school, talent1, talent2

    @pytest.mark.asyncio
    async def test_get_list(self, test_session: AsyncSession, setup_data):
        """Test get talent list."""
        repo = TalentRepository(test_session)
        talents, total = await repo.get_list()

        assert total == 2
        assert len(talents) == 2

    @pytest.mark.asyncio
    async def test_get_list_with_role_filter(self, test_session: AsyncSession, setup_data):
        """Test get talent list with role filter."""
        repo = TalentRepository(test_session)
        talents, total = await repo.get_list(role_type=RoleType.PROFESSOR.value)

        assert total == 1
        assert talents[0].role_type == "professor"

    @pytest.mark.asyncio
    async def test_get_by_id(self, test_session: AsyncSession, setup_data):
        """Test get talent by ID."""
        _, talent1, _ = setup_data
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
        _, talent1, _ = setup_data
        repo = TalentRepository(test_session)
        profile = await repo.get_role_profile(talent1.talent_id)

        assert profile is not None
        assert profile.role_reason == "High citations"

    @pytest.mark.asyncio
    async def test_get_by_ids(self, test_session: AsyncSession, setup_data):
        """Test get multiple talents by IDs with batch processing."""
        _, talent1, talent2 = setup_data
        repo = TalentRepository(test_session)

        # Test with multiple IDs
        talents = await repo.get_by_ids([talent1.talent_id, talent2.talent_id])

        assert len(talents) == 2
        names = {t.name for t in talents}
        assert "John Doe" in names
        assert "Jane Smith" in names

    @pytest.mark.asyncio
    async def test_get_by_ids_empty_list(self, test_session: AsyncSession):
        """Test get_by_ids with empty list."""
        repo = TalentRepository(test_session)
        talents = await repo.get_by_ids([])

        assert talents == []

    @pytest.mark.asyncio
    async def test_search_by_json_field(self, test_session: AsyncSession, setup_data):
        """Test search by JSON field (openalex_topics)."""
        _, talent1, _ = setup_data
        # Add openalex_topics to talent
        talent1.openalex_topics = ["Machine Learning", "Computer Vision"]
        await test_session.commit()

        repo = TalentRepository(test_session)
        talents, total = await repo.search_by_json_field(
            field_name="openalex_topics",
            keywords=["Machine Learning"],
            limit=10,
        )

        assert total >= 1
        assert any("Machine Learning" in (t.openalex_topics or []) for t in talents)

    @pytest.mark.asyncio
    async def test_search_by_json_field_any_mode(self, test_session: AsyncSession, setup_data):
        """Test search by JSON field with any match mode."""
        _, talent1, _ = setup_data
        talent1.openalex_topics = ["Machine Learning", "Computer Vision"]
        await test_session.commit()

        repo = TalentRepository(test_session)
        talents, total = await repo.search_by_json_field(
            field_name="openalex_topics",
            keywords=["Machine Learning", "NonExistent"],
            match_mode="any",
            limit=10,
        )

        # Should match because one keyword matches
        assert total >= 1

    @pytest.mark.asyncio
    async def test_get_paper_titles_for_talents(self, test_session: AsyncSession, setup_data):
        """Test batch get paper titles for talents."""
        _, talent1, _ = setup_data
        repo = TalentRepository(test_session)

        # Test with no papers (talent has no std_author_id)
        result = await repo.get_paper_titles_for_talents([talent1.talent_id])

        assert talent1.talent_id in result
        # May be empty if no std_author_id linked
        assert isinstance(result[talent1.talent_id], list)

    @pytest.mark.asyncio
    async def test_get_paper_titles_for_talents_empty_list(self, test_session: AsyncSession):
        """Test get_paper_titles_for_talents with empty list."""
        repo = TalentRepository(test_session)
        result = await repo.get_paper_titles_for_talents([])

        assert result == {}

    @pytest.mark.asyncio
    async def test_search_by_research_keywords(self, test_session: AsyncSession, setup_data):
        """Test comprehensive search for JD matching."""
        _, talent1, _ = setup_data
        talent1.openalex_topics = ["Machine Learning", "Deep Learning"]
        await test_session.commit()

        repo = TalentRepository(test_session)
        candidates = await repo.search_by_research_keywords(
            keywords=["Machine Learning"],
            search_scope=["openalex_topics"],
            limit=10,
        )

        # Should find at least one candidate
        assert len(candidates) >= 1
        # Check result structure
        for candidate in candidates:
            assert "talent" in candidate
            assert "paper_titles" in candidate
            assert "openalex_topics" in candidate
            assert "matched_keywords" in candidate

    @pytest.mark.asyncio
    async def test_search_by_research_keywords_empty(self, test_session: AsyncSession):
        """Test search_by_research_keywords with empty keywords."""
        repo = TalentRepository(test_session)
        candidates = await repo.search_by_research_keywords(
            keywords=[],
            limit=10,
        )

        assert candidates == []

    @pytest.mark.asyncio
    async def test_apply_search_filters(self, test_session: AsyncSession, setup_data):
        """Test filter application in search methods."""
        school, talent1, talent2 = setup_data
        repo = TalentRepository(test_session)

        # Test with school_id filter
        talents, total = await repo.search_by_json_field(
            field_name="openalex_topics",
            keywords=[],
            filters={"school_id": school.school_id},
            limit=10,
        )

        # All returned talents should have the filtered school_id
        for talent in talents:
            assert talent.school_id == school.school_id

    @pytest.mark.asyncio
    async def test_apply_search_filters_country_code(self, test_session: AsyncSession, setup_data):
        """Test country_code filter application."""
        school, talent1, talent2 = setup_data
        repo = TalentRepository(test_session)

        # Add a topic to test talents for keyword search
        talent1.openalex_topics = ["machine learning"]
        talent2.openalex_topics = ["machine learning"]
        await test_session.commit()

        # Test with country_code filter
        talents, total = await repo.search_by_json_field(
            field_name="openalex_topics",
            keywords=["machine learning"],
            filters={"country_code": school.country_code},
            limit=10,
        )

        # All returned talents should be from schools in the filtered country
        for talent in talents:
            # school is already loaded via selectinload
            assert talent.school is not None
            assert talent.school.country_code == school.country_code.upper()

    @pytest.mark.asyncio
    async def test_apply_search_filters_min_works(self, test_session: AsyncSession, setup_data):
        """Test min_works filter application."""
        school, talent1, talent2 = setup_data
        repo = TalentRepository(test_session)

        # Set different works_count
        talent1.works_count = 10
        talent2.works_count = 5
        talent1.openalex_topics = ["deep learning"]
        talent2.openalex_topics = ["deep learning"]
        await test_session.commit()

        # Test with min_works filter
        talents, total = await repo.search_by_json_field(
            field_name="openalex_topics",
            keywords=["deep learning"],
            filters={"min_works": 8},
            limit=10,
        )

        # All returned talents should have works_count >= min_works
        for talent in talents:
            assert talent.works_count >= 8

    @pytest.mark.asyncio
    async def test_get_by_ids_large_batch(self, test_session: AsyncSession, setup_data):
        """Test get_by_ids handles batch processing for large ID lists."""
        _, talent1, talent2 = setup_data
        repo = TalentRepository(test_session)

        # Create a list larger than batch_size to test batch processing
        # Use unique IDs to test that batch processing works
        large_id_list = [talent1.talent_id, talent2.talent_id]

        talents = await repo.get_by_ids(large_id_list, batch_size=1)

        # Should return 2 unique talents (one per batch)
        assert len(talents) == 2
        talent_ids = {t.talent_id for t in talents}
        assert talent1.talent_id in talent_ids
        assert talent2.talent_id in talent_ids


class TestStatisticsRepository:
    """Tests for StatisticsRepository."""

    @pytest.mark.asyncio
    async def test_get_active_overview_stats_empty(self, test_session: AsyncSession):
        """Test get active stats when none exist."""
        repo = StatisticsRepository(test_session)
        stats = await repo.get_active_overview_stats()

        assert stats is None

    @pytest.mark.asyncio
    async def test_get_active_overview_stats(self, test_session: AsyncSession):
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
    async def test_get_school_stats(self, test_session: AsyncSession):
        """Test get school statistics."""
        # Create test data
        school = School(
            school_name="MIT",
            country_code="US",
            country_name="美国",
        )
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
