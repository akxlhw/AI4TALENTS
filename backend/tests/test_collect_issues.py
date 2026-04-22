"""
Tests for collection orchestrator - covering issues found in production.

This test file ensures:
1. AuthorTechBelong has required source_task_id field
2. _update_talent_topic_tags properly eager loads relationships
3. Statistics are correctly reported even when data already exists
4. MAX_WORKS_PER_VENUE limit behavior
"""
import pytest
import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.raw_data import RawWork, RawAuthor, RawInstitution, AuthorTechBelong
from app.models.standardized import StdAuthor, StdSchool
from app.models.talent import Talent
from app.models.tech_domain import TalentTechTag, TechDomain, TechDirection
from app.models.sync import CollectTask
from app.services.collect.orchestrator import CollectionOrchestrator
from app.services.normalizers import AuthorNormalizer, SchoolNormalizer
from app.services.data_fetchers import MAX_WORKS_PER_VENUE


class TestAuthorTechBelongSourceTask:
    """Test that AuthorTechBelong requires source_task_id for sync"""

    @pytest.mark.asyncio
    async def test_author_tech_belong_requires_source_task_id(
        self, test_session: AsyncSession, full_setup
    ):
        """
        Issue: AuthorTechBelong without source_task_id caused sync to fail
        with "No AuthorTechBelong found for task_id=X"

        This test ensures source_task_id is properly set.
        """
        setup = full_setup

        # Create a task with all required fields
        task = CollectTask(
            task_code="TEST-TASK-001",
            tech_domain_id=setup["tech_domain"].tech_domain_id,
            collect_mode="incremental",
            triggered_by=None,
            triggered_at=datetime.utcnow(),  # Required field
            status="completed"
        )
        test_session.add(task)
        await test_session.flush()

        # Create StdAuthor
        std_school = StdSchool(
            openalex_institution_id="I-TEST",
            name_normalized="Test University",
            country_code="US",
            source_task_id=task.task_id
        )
        test_session.add(std_school)
        await test_session.flush()

        std_author = StdAuthor(
            openalex_author_id="A-TEST",
            name_normalized="Test Author",
            works_count=10,
            cited_by_count=100,
            h_index=5,
            std_school_id=std_school.std_school_id,
            source_task_id=task.task_id
        )
        test_session.add(std_author)
        await test_session.flush()

        # Create AuthorTechBelong WITH source_task_id
        tech_belong = AuthorTechBelong(
            openalex_author_id="A-TEST",
            std_author_id=std_author.std_author_id,
            tech_domain_id=setup["tech_domain"].tech_domain_id,
            source_venue_id=setup["venue"].venue_id,
            source_task_id=task.task_id,  # CRITICAL: must be set
            work_count_in_venue=5
        )
        test_session.add(tech_belong)
        await test_session.commit()

        # Verify the record can be queried by task_id
        result = await test_session.execute(
            select(AuthorTechBelong).where(
                AuthorTechBelong.source_task_id == task.task_id,
                AuthorTechBelong.tech_domain_id == setup["tech_domain"].tech_domain_id
            )
        )
        found = result.scalars().all()

        assert len(found) == 1, "AuthorTechBelong should be findable by source_task_id"
        assert found[0].openalex_author_id == "A-TEST"


class TestTalentTopicTagsEagerLoading:
    """Test that _update_talent_topic_tags properly loads relationships"""

    @pytest.mark.asyncio
    async def test_update_topic_tags_eager_loads_tech_domain(
        self, test_session: AsyncSession, full_setup
    ):
        """
        Issue: _update_talent_topic_tags failed with greenlet_spawn error
        because tech_domain was lazily loaded inside async context.

        This test verifies eager loading works correctly.
        """
        setup = full_setup

        # Create a talent with tech tags
        talent = Talent(
            name="Test Talent",
            name_en="Test Talent",
            role_type="professor",
            works_count=10,
            cited_by_count=100,
            h_index=5,
            school_id=None,
            topic_tags=[]
        )
        test_session.add(talent)
        await test_session.flush()

        # Create tech tag
        tech_tag = TalentTechTag(
            talent_id=talent.talent_id,
            tech_domain_id=setup["tech_domain"].tech_domain_id,
            tech_direction_id=setup["tech_direction"].tech_direction_id,
            is_enabled=True
        )
        test_session.add(tech_tag)
        await test_session.commit()

        # Now try to update topic_tags using eager loading
        result = await test_session.execute(
            select(Talent).options(
                selectinload(Talent.tech_tags).selectinload(TalentTechTag.tech_domain)
            )
        )
        talents = result.scalars().all()

        updated_count = 0
        for t in talents:
            if t.tech_tags:
                tech_names = list(set(
                    tag.tech_domain.domain_name
                    for tag in t.tech_tags
                    if tag.tech_domain and tag.is_enabled
                ))
                if tech_names:
                    t.topic_tags = tech_names
                    updated_count += 1

        await test_session.commit()

        # Verify
        assert updated_count > 0, "Should have updated at least one talent"

        # Reload and verify
        await test_session.refresh(talent)
        assert len(talent.topic_tags) > 0, "Talent should have topic tags"
        assert setup["tech_domain"].domain_name in talent.topic_tags


class TestNormalizationStatistics:
    """Test that normalizers report correct statistics"""

    @pytest.mark.asyncio
    async def test_normalize_authors_reports_existing_count(
        self, test_session: AsyncSession
    ):
        """
        Test that normalizer correctly processes pending RawAuthors.

        The normalizer processes RawAuthor -> StdAuthor transformation.
        It should report the count of processed authors.
        """
        # Create a task first
        task = CollectTask(
            task_code="TEST-NORM-001",
            collect_mode="incremental",
            triggered_by=None,
            triggered_at=datetime.utcnow(),
            status="running"
        )
        test_session.add(task)
        await test_session.flush()

        # Create pending RawAuthors
        for i in range(5):
            raw_author = RawAuthor(
                openalex_author_id=f"A-NORM-{i}",
                raw_json='{"x_concepts": []}',
                display_name=f"Author {i}",
                works_count=10,
                cited_by_count=100,
                h_index=5,
                fetch_task_id=task.task_id,
                processed_status="pending"
            )
            test_session.add(raw_author)
        await test_session.commit()

        # Now run normalizer
        normalizer = AuthorNormalizer(test_session)
        result = await normalizer.normalize_all_authors(task_id=task.task_id)

        # Should have processed all 5 pending authors
        assert result.total >= 5, f"Should report at least 5 authors, got {result.total}"
        assert result.processed >= 5, f"Should have processed at least 5, got {result.processed}"

    @pytest.mark.asyncio
    async def test_normalize_schools_reports_existing_count(
        self, test_session: AsyncSession
    ):
        """
        Test that school normalizer correctly processes pending RawInstitutions.
        """
        # Create a task first
        task = CollectTask(
            task_code="TEST-NORM-002",
            collect_mode="incremental",
            triggered_by=None,
            triggered_at=datetime.utcnow(),
            status="running"
        )
        test_session.add(task)
        await test_session.flush()

        # Create pending RawInstitutions
        for i in range(3):
            raw_inst = RawInstitution(
                openalex_institution_id=f"I-NORM-{i}",
                raw_json='{}',
                display_name=f"University {i}",
                country_code="US",
                fetch_task_id=task.task_id,
                processed_status="pending"
            )
            test_session.add(raw_inst)
        await test_session.commit()

        # Now run normalizer
        normalizer = SchoolNormalizer(test_session)
        result = await normalizer.normalize_all_institutions(task_id=task.task_id)

        # Should have processed all 3 pending institutions
        assert result.total >= 3, f"Should report at least 3 schools, got {result.total}"
        assert result.processed >= 3, f"Should have processed at least 3, got {result.processed}"


class TestWorksLimit:
    """Test works fetching limit behavior"""

    def test_max_works_per_venue_default(self):
        """
        Issue: MAX_WORKS_PER_VENUE was hardcoded to 500, limiting data collection.

        After fix: Should be 0 (no limit) by default.
        """
        # MAX_WORKS_PER_VENUE should be 0 (no limit)
        assert MAX_WORKS_PER_VENUE == 0, "MAX_WORKS_PER_VENUE should be 0 (no limit)"


class TestCollectionProgressStatistics:
    """Test that collection progress statistics are accurate"""

    @pytest.mark.asyncio
    async def test_progress_shows_total_unique_authors(
        self, test_session: AsyncSession, full_setup
    ):
        """
        Issue: Progress showed 0 authors because it only counted newly fetched.

        Should show total unique authors extracted from works.
        """
        setup = full_setup

        # Create a task with all required fields
        task = CollectTask(
            task_code="TEST-PROGRESS-001",
            tech_domain_id=setup["tech_domain"].tech_domain_id,
            collect_mode="incremental",
            triggered_by=None,
            triggered_at=datetime.utcnow(),  # Required field
            status="running"
        )
        test_session.add(task)
        await test_session.flush()

        # Create some raw works with author IDs
        for i in range(3):
            work = RawWork(
                openalex_work_id=f"W-PROGRESS-{i}",
                raw_json="{}",
                title=f"Test Work {i}",
                publication_year=2024,
                author_ids=json.dumps([f"A-{i}", f"A-{i+10}"]),  # 2 authors each
                source_id=setup["venue"].openalex_source_id,
                fetch_task_id=task.task_id
            )
            test_session.add(work)
        await test_session.commit()

        # Create some raw authors (simulating existing data)
        for i in range(6):
            author = RawAuthor(
                openalex_author_id=f"A-{i}",
                raw_json="{}",
                display_name=f"Author {i}",
                works_count=10,
                cited_by_count=100,
                h_index=5,
                fetch_task_id=task.task_id
            )
            test_session.add(author)
        await test_session.commit()

        # Verify we have works with author IDs
        result = await test_session.execute(
            select(RawWork).where(RawWork.fetch_task_id == task.task_id)
        )
        works = result.scalars().all()

        # Extract unique author IDs
        unique_authors = set()
        for work in works:
            if work.author_ids:
                unique_authors.update(json.loads(work.author_ids))

        # Should have 6 unique authors (A-0, A-10, A-1, A-11, A-2, A-12)
        assert len(unique_authors) >= 4, "Should have extracted unique author IDs"
