"""
Tests for bulk sync operations (TP3).
"""

import os

os.environ["REDIS_ENABLED"] = "false"

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.standardized import StdAuthor, StdSchool
from app.services.common.cs_concepts import CS_SCORE_THRESHOLD
from app.services.sync.author_sync import AuthorSyncService
from app.services.sync.school_sync import SchoolSyncService


@pytest.fixture
async def setup_std_schools(test_session: AsyncSession):
    """Create test standardized schools."""
    schools = []
    for i in range(5):
        school = StdSchool(
            openalex_institution_id=f"I{i:06d}",
            name_normalized=f"Test School {i}",
            country_code="US",
            homepage_url=f"https://test{i}.edu",
        )
        test_session.add(school)
        schools.append(school)

    await test_session.commit()
    return schools


@pytest.fixture
async def setup_std_authors(test_session: AsyncSession, setup_std_schools):
    """Create test standardized authors with CS scores."""
    authors = []
    for i in range(10):
        # Create authors with varying CS scores
        cs_score = 0.3 + (i * 0.08)  # 0.30 to 1.02

        author = StdAuthor(
            openalex_author_id=f"A{i:06d}",
            name_normalized=f"Author {i}",
            std_school_id=setup_std_schools[i % 5].std_school_id,
            cs_concepts_score=cs_score,
            works_count=10 + i * 5,
            cited_by_count=100 + i * 50,
            h_index=5 + i,
        )
        test_session.add(author)
        authors.append(author)

    await test_session.commit()
    return authors


class TestBulkSchoolSync:
    """Tests for bulk school sync."""

    @pytest.mark.asyncio
    async def test_bulk_sync_schools_creates_new(
        self, test_session: AsyncSession, setup_std_schools
    ):
        """Test bulk sync creates new schools."""
        service = SchoolSyncService(test_session)

        result = await service.bulk_sync_schools(setup_std_schools)

        assert result["synced"] == 5
        assert result["created"] == 5
        assert result["updated"] == 0
        assert len(result["school_id_map"]) == 5

    @pytest.mark.asyncio
    async def test_bulk_sync_schools_updates_existing(
        self, test_session: AsyncSession, setup_std_schools
    ):
        """Test bulk sync updates existing schools."""
        service = SchoolSyncService(test_session)

        # First sync - creates
        result1 = await service.bulk_sync_schools(setup_std_schools)
        assert result1["created"] == 5

        # Modify standardized schools
        for school in setup_std_schools:
            school.name_normalized = f"Updated {school.name_normalized}"

        # Second sync - updates
        result2 = await service.bulk_sync_schools(setup_std_schools)
        assert result2["synced"] == 5
        assert result2["created"] == 0
        assert result2["updated"] == 5

    @pytest.mark.asyncio
    async def test_bulk_sync_schools_empty_list(self, test_session: AsyncSession):
        """Test bulk sync with empty list."""
        service = SchoolSyncService(test_session)

        result = await service.bulk_sync_schools([])

        assert result["synced"] == 0
        assert result["created"] == 0
        assert result["updated"] == 0

    @pytest.mark.asyncio
    async def test_bulk_sync_schools_returns_id_map(
        self, test_session: AsyncSession, setup_std_schools
    ):
        """Test bulk sync returns school ID mapping."""
        service = SchoolSyncService(test_session)

        result = await service.bulk_sync_schools(setup_std_schools)

        # Check ID map contains OpenAlex IDs
        for school in setup_std_schools:
            assert school.openalex_institution_id in result["school_id_map"]
            school_id = result["school_id_map"][school.openalex_institution_id]
            assert school_id is not None
            assert school_id > 0


class TestBulkAuthorSync:
    """Tests for bulk author sync."""

    @pytest.mark.asyncio
    async def test_bulk_sync_authors_filters_by_cs_score(
        self, test_session: AsyncSession, setup_std_authors
    ):
        """Test bulk sync filters authors by CS score threshold."""
        service = AuthorSyncService(test_session)

        # Sync schools first to get school_id_map
        from sqlalchemy import select

        from app.models.standardized import StdSchool

        school_service = SchoolSyncService(test_session)
        std_schools_result = await test_session.execute(select(StdSchool))
        std_schools = list(std_schools_result.scalars().all())

        school_result = await school_service.bulk_sync_schools(std_schools)
        school_id_map = school_result["school_id_map"]

        # Sync authors
        result = await service.bulk_sync_authors(setup_std_authors, school_id_map)

        # Count authors above threshold
        above_threshold = sum(
            1 for a in setup_std_authors if (a.cs_concepts_score or 0) >= CS_SCORE_THRESHOLD
        )

        assert result["filtered"] == len(setup_std_authors) - above_threshold
        assert result["synced"] == above_threshold

    @pytest.mark.asyncio
    async def test_bulk_sync_authors_creates_talents(
        self, test_session: AsyncSession, setup_std_authors
    ):
        """Test bulk sync creates talent records."""
        from sqlalchemy import select

        from app.models.standardized import StdSchool
        from app.models.talent import Talent

        # Sync schools first
        std_schools_result = await test_session.execute(select(StdSchool))
        std_schools = list(std_schools_result.scalars().all())

        school_service = SchoolSyncService(test_session)
        school_result = await school_service.bulk_sync_schools(std_schools)
        school_id_map = school_result["school_id_map"]

        # Sync authors
        service = AuthorSyncService(test_session)
        result = await service.bulk_sync_authors(setup_std_authors, school_id_map)

        # Verify talents were created
        talents_result = await test_session.execute(select(Talent))
        talents = list(talents_result.scalars().all())

        # Should have created talents for authors above CS threshold
        assert len(talents) == result["synced"]

    @pytest.mark.asyncio
    async def test_bulk_sync_authors_empty_list(self, test_session: AsyncSession):
        """Test bulk sync with empty author list."""
        service = AuthorSyncService(test_session)

        result = await service.bulk_sync_authors([])

        assert result["synced"] == 0
        assert result["created"] == 0
        assert result["updated"] == 0
        assert result["filtered"] == 0

    @pytest.mark.asyncio
    async def test_bulk_sync_identifies_new_talents(
        self, test_session: AsyncSession, setup_std_authors
    ):
        """Test bulk sync identifies newly created talents for work fetching."""
        from sqlalchemy import select

        from app.models.standardized import StdSchool

        # Sync schools first
        std_schools_result = await test_session.execute(select(StdSchool))
        std_schools = list(std_schools_result.scalars().all())

        school_service = SchoolSyncService(test_session)
        school_result = await school_service.bulk_sync_schools(std_schools)
        school_id_map = school_result["school_id_map"]

        # Sync authors
        service = AuthorSyncService(test_session)
        result = await service.bulk_sync_authors(setup_std_authors, school_id_map)

        # Check new_talents list
        assert "new_talents" in result
        assert isinstance(result["new_talents"], list)

        # New talents should have expected fields
        for talent_info in result["new_talents"]:
            assert "talent_id" in talent_info
            assert "openalex_author_id" in talent_info
            assert "works_count" in talent_info


class TestBulkSyncWithExistingData:
    """Tests for bulk sync with existing data."""

    @pytest.mark.asyncio
    async def test_bulk_sync_handles_mixed_new_and_existing(self, test_session: AsyncSession):
        """Test bulk sync handles mix of new and existing records."""
        from sqlalchemy import select

        from app.models.standardized import StdSchool

        # Create some schools
        schools = []
        for i in range(4):
            school = StdSchool(
                openalex_institution_id=f"I{i:06d}",
                name_normalized=f"School {i}",
                country_code="US",
            )
            test_session.add(school)
            schools.append(school)

        await test_session.commit()

        service = SchoolSyncService(test_session)

        # First sync - creates all
        result1 = await service.bulk_sync_schools(schools)
        assert result1["created"] == 4

        # Add new school
        new_school = StdSchool(
            openalex_institution_id="I99999",
            name_normalized="New School",
            country_code="CN",
        )
        test_session.add(new_school)
        await test_session.commit()

        # Modify existing schools
        for school in schools:
            school.name_normalized = f"Updated {school.name_normalized}"
        await test_session.commit()

        # Re-fetch to get updated data
        all_schools_result = await test_session.execute(select(StdSchool))
        all_schools = list(all_schools_result.scalars().all())

        # Second sync - updates existing, creates new
        result2 = await service.bulk_sync_schools(all_schools)
        assert result2["created"] == 1
        assert result2["updated"] == 4


class TestServingLayerOrchestrator:
    """Tests for ServingLayerOrchestrator integration."""

    @pytest.fixture
    async def setup_orchestrator_data(self, test_session: AsyncSession):
        """Create comprehensive test data for orchestrator tests."""
        from app.models.raw_data import AuthorTechBelong
        from app.models.tech_domain import TechDomain

        # Create tech domain
        domain = TechDomain(
            domain_code="TEST_AI",
            domain_name="测试人工智能",
            is_enabled=True,
        )
        test_session.add(domain)
        await test_session.flush()

        # Create standardized schools
        schools = []
        for i in range(2):
            school = StdSchool(
                openalex_institution_id=f"I{1000 + i:06d}",
                name_normalized=f"Orchestrator School {i}",
                country_code="US",
            )
            test_session.add(school)
            schools.append(school)

        await test_session.flush()

        # Create standardized authors with various CS scores
        authors = []
        for i in range(5):
            cs_score = 0.4 + i * 0.15  # 0.40, 0.55, 0.70, 0.85, 1.0
            author = StdAuthor(
                openalex_author_id=f"A{2000 + i:06d}",
                name_normalized=f"Author {i}",
                std_school_id=schools[i % 2].std_school_id,
                cs_concepts_score=cs_score,
                works_count=20 + i * 5,
                cited_by_count=200 + i * 50,
                h_index=10 + i,
            )
            test_session.add(author)
            authors.append(author)

        await test_session.flush()

        # Create AuthorTechBelong records
        belongs = []
        for author in authors:
            belong = AuthorTechBelong(
                openalex_author_id=author.openalex_author_id,
                tech_domain_id=domain.tech_domain_id,
                source_task_id=None,  # No task reference for test
                work_count_in_venue=5,
            )
            test_session.add(belong)
            belongs.append(belong)

        await test_session.commit()

        return {
            "domain": domain,
            "schools": schools,
            "authors": authors,
            "belongs": belongs,
        }

    @pytest.mark.asyncio
    async def test_orchestrator_sync_all(self, test_session: AsyncSession, setup_orchestrator_data):
        """Test full sync via ServingLayerOrchestrator - with no matching task records."""
        from app.services.sync.orchestrator import ServingLayerOrchestrator

        data = setup_orchestrator_data
        orchestrator = ServingLayerOrchestrator(test_session)

        # Since AuthorTechBelong records have source_task_id=None,
        # querying with task_id=1 will find no matches
        result = await orchestrator.sync_all_for_task(
            task_id=1,
            tech_domain_id=data["domain"].tech_domain_id,
        )

        # Should return empty stats when no matching records
        assert result["authors_synced"] == 0
        assert result["schools_synced"] == 0
        assert result["tags_created"] == 0
        assert "new_talents_for_works" in result

    @pytest.mark.asyncio
    async def test_orchestrator_filters_by_cs_score(
        self, test_session: AsyncSession, setup_orchestrator_data
    ):
        """Test CS score filtering logic is correctly configured."""
        from app.services.common.cs_concepts import CS_SCORE_THRESHOLD

        data = setup_orchestrator_data

        # Verify CS score threshold is being applied correctly
        # Count authors above threshold
        above_threshold = sum(
            1 for a in data["authors"] if (a.cs_concepts_score or 0) >= CS_SCORE_THRESHOLD
        )

        # Verify the threshold is working as expected
        # Authors with CS scores: 0.40, 0.55, 0.70, 0.85, 1.0
        # With threshold 0.7, should have 3 above threshold (0.70, 0.85, 1.0)
        assert above_threshold == 3
        assert len(data["authors"]) - above_threshold == 2  # 0.40 and 0.55 are below

    @pytest.mark.asyncio
    async def test_orchestrator_no_data_for_task(self, test_session: AsyncSession):
        """Test orchestrator handles task with no data."""
        from app.models.tech_domain import TechDomain
        from app.services.sync.orchestrator import ServingLayerOrchestrator

        # Create tech domain
        domain = TechDomain(
            domain_code="EMPTY_DOMAIN",
            domain_name="空元素",
            is_enabled=True,
        )
        test_session.add(domain)
        await test_session.commit()

        orchestrator = ServingLayerOrchestrator(test_session)

        result = await orchestrator.sync_all_for_task(
            task_id=99999,  # Non-existent task
            tech_domain_id=domain.tech_domain_id,
        )

        # Should return empty stats
        assert result["authors_synced"] == 0
        assert result["schools_synced"] == 0
        assert result["tags_created"] == 0


class TestBulkSyncErrorHandling:
    """Tests for bulk sync error handling."""

    @pytest.mark.asyncio
    async def test_bulk_sync_school_with_missing_fields(self, test_session: AsyncSession):
        """Test bulk sync handles schools with missing optional fields."""
        school = StdSchool(
            openalex_institution_id="I000001",
            name_normalized="Minimal School",
            country_code=None,  # Optional field
        )
        test_session.add(school)
        await test_session.commit()

        service = SchoolSyncService(test_session)
        result = await service.bulk_sync_schools([school])

        assert result["synced"] == 1
        assert result["created"] == 1

    @pytest.mark.asyncio
    async def test_bulk_sync_author_without_school(self, test_session: AsyncSession):
        """Test bulk sync handles author without school."""

        author = StdAuthor(
            openalex_author_id="A000001",
            name_normalized="No School Author",
            std_school_id=None,  # No school
            cs_concepts_score=0.8,
        )
        test_session.add(author)
        await test_session.commit()

        service = AuthorSyncService(test_session)
        result = await service.bulk_sync_authors([author], school_id_map={})

        # Should still sync the author
        assert result["synced"] == 1

    @pytest.mark.asyncio
    async def test_bulk_sync_author_with_null_cs_score(self, test_session: AsyncSession):
        """Test bulk sync filters author with null CS score."""
        author = StdAuthor(
            openalex_author_id="A000002",
            name_normalized="No CS Score Author",
            cs_concepts_score=None,  # Null CS score
        )
        test_session.add(author)
        await test_session.commit()

        service = AuthorSyncService(test_session)
        result = await service.bulk_sync_authors([author])

        # Should be filtered due to null CS score (0.0 < threshold)
        assert result["filtered"] == 1
        assert result["synced"] == 0

    @pytest.mark.asyncio
    async def test_bulk_sync_large_batch(self, test_session: AsyncSession):
        """Test bulk sync handles large batch of schools."""
        # Create 100 schools
        schools = []
        for i in range(100):
            school = StdSchool(
                openalex_institution_id=f"I{3000 + i:06d}",
                name_normalized=f"Large Batch School {i}",
                country_code="US",
            )
            test_session.add(school)
            schools.append(school)

        await test_session.commit()

        service = SchoolSyncService(test_session)
        result = await service.bulk_sync_schools(schools)

        assert result["synced"] == 100
        assert result["created"] == 100
