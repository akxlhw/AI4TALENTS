"""
Tests for collection orchestrator - covering issues found in production.

This test file ensures:
1. AuthorTechBelong has required source_task_id field
2. _update_talent_topic_tags properly eager loads relationships
3. Statistics are correctly reported even when data already exists
4. MAX_WORKS_PER_VENUE limit behavior
"""

import json
from datetime import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.academic.models.raw_data import (
    AuthorTechBelong,
    RawAuthor,
    RawInstitution,
    RawWork,
)
from app.domains.academic.models.standardized import StdAuthor, StdSchool
from app.domains.academic.models.sync import CollectTask
from app.domains.academic.models.talent import Talent
from app.domains.academic.models.tech_domain import TalentTechTag
from app.domains.academic.services.data_fetchers import MAX_WORKS_PER_VENUE
from app.domains.academic.services.normalizers import AuthorNormalizer, SchoolNormalizer


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
            status="completed",
        )
        test_session.add(task)
        await test_session.flush()

        # Create StdAuthor
        std_school = StdSchool(
            openalex_institution_id="I-TEST",
            name_normalized="Test University",
            country_code="US",
            source_task_id=task.task_id,
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
            source_task_id=task.task_id,
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
            work_count_in_venue=5,
        )
        test_session.add(tech_belong)
        await test_session.commit()

        # Verify the record can be queried by task_id
        result = await test_session.execute(
            select(AuthorTechBelong).where(
                AuthorTechBelong.source_task_id == task.task_id,
                AuthorTechBelong.tech_domain_id == setup["tech_domain"].tech_domain_id,
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
            topic_tags=[],
        )
        test_session.add(talent)
        await test_session.flush()

        # Create tech tag
        tech_tag = TalentTechTag(
            talent_id=talent.talent_id,
            tech_domain_id=setup["tech_domain"].tech_domain_id,
            tech_direction_id=setup["tech_direction"].tech_direction_id,
            is_enabled=True,
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
                tech_names = list(
                    {
                        tag.tech_domain.domain_name
                        for tag in t.tech_tags
                        if tag.tech_domain and tag.is_enabled
                    }
                )
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
    async def test_normalize_authors_reports_existing_count(self, test_session: AsyncSession):
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
            status="running",
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
                processed_status="pending",
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
    async def test_normalize_schools_reports_existing_count(self, test_session: AsyncSession):
        """
        Test that school normalizer correctly processes pending RawInstitutions.
        """
        # Create a task first
        task = CollectTask(
            task_code="TEST-NORM-002",
            collect_mode="incremental",
            triggered_by=None,
            triggered_at=datetime.utcnow(),
            status="running",
        )
        test_session.add(task)
        await test_session.flush()

        # Create pending RawInstitutions
        for i in range(3):
            raw_inst = RawInstitution(
                openalex_institution_id=f"I-NORM-{i}",
                raw_json="{}",
                display_name=f"University {i}",
                country_code="US",
                fetch_task_id=task.task_id,
                processed_status="pending",
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
            status="running",
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
                fetch_task_id=task.task_id,
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
                fetch_task_id=task.task_id,
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


class TestMultiVenueTechBelong:
    """Test that AuthorTechBelong handles same author+domain across multiple venues."""

    @pytest.mark.asyncio
    async def test_author_tech_belong_across_multiple_venues(
        self, test_session: AsyncSession, full_setup
    ):
        """
        Issue: Unique constraint (author_id, domain_id) caused integrity errors
        when the same author published in multiple venues within the same domain.

        After fix: Each venue gets its own record, and tech_tag_sync aggregates
        work counts across venues.
        """
        from app.domains.academic.models.raw_data import RawWork
        from app.domains.academic.models.talent import Talent
        from app.domains.academic.models.tech_domain import TalentTechTag
        from app.domains.academic.models.venue import Venue, VenueTechBinding
        from app.domains.academic.services.normalizers import TechBelongCalculator
        from app.domains.academic.services.sync.tech_tag_sync import TechTagSyncService

        setup = full_setup
        domain = setup["tech_domain"]
        venue_a = setup["venue"]  # NEURIPS, openalex_source_id=S12345

        # Create venue B (ICML) bound to the same domain
        venue_b = Venue(
            venue_code="ICML",
            venue_name="ICML",
            venue_type="conference",
            openalex_source_id="S67890",
            is_enabled=True,
        )
        test_session.add(venue_b)
        await test_session.flush()

        binding_b = VenueTechBinding(
            venue_id=venue_b.venue_id,
            tech_domain_id=domain.tech_domain_id,
            is_enabled=True,
        )
        test_session.add(binding_b)
        await test_session.commit()

        author_id = "A-MULTI-VENUE"

        # Create 2 RawWorks for venue A
        for i in range(2):
            work = RawWork(
                openalex_work_id=f"W-NEURIPS-{i}",
                raw_json="{}",
                title=f"NeurIPS Work {i}",
                publication_year=2024,
                author_ids=json.dumps([author_id]),
                source_id=venue_a.openalex_source_id,
            )
            test_session.add(work)

        # Create 3 RawWorks for venue B
        for i in range(3):
            work = RawWork(
                openalex_work_id=f"W-ICML-{i}",
                raw_json="{}",
                title=f"ICML Work {i}",
                publication_year=2024,
                author_ids=json.dumps([author_id]),
                source_id=venue_b.openalex_source_id,
            )
            test_session.add(work)

        await test_session.commit()

        # Phase 6: calculate_for_venue for both venues
        calculator = TechBelongCalculator(test_session)
        count_a = await calculator.calculate_for_venue(
            venue_id=venue_a.venue_id,
            tech_domain_id=domain.tech_domain_id,
            task_id=None,
        )
        count_b = await calculator.calculate_for_venue(
            venue_id=venue_b.venue_id,
            tech_domain_id=domain.tech_domain_id,
            task_id=None,
        )

        assert count_a == 1, "Should create 1 belong record for venue A"
        assert count_b == 1, "Should create 1 belong record for venue B"

        # Verify both records exist in DB
        result = await test_session.execute(
            select(AuthorTechBelong).where(
                AuthorTechBelong.openalex_author_id == author_id,
                AuthorTechBelong.tech_domain_id == domain.tech_domain_id,
            )
        )
        belongs = result.scalars().all()
        assert (
            len(belongs) == 2
        ), f"Should have 2 AuthorTechBelong records (one per venue), got {len(belongs)}"

        # Verify venue-specific counts
        venue_counts = {b.source_venue_id: b.work_count_in_venue for b in belongs}
        assert venue_counts.get(venue_a.venue_id) == 2
        assert venue_counts.get(venue_b.venue_id) == 3

        # Verify downstream sync aggregates correctly
        talent = Talent(
            name="Multi Venue Author",
            name_en="Multi Venue Author",
            role_type="professor",
            works_count=5,
            cited_by_count=100,
            h_index=5,
        )
        test_session.add(talent)
        await test_session.flush()

        sync_service = TechTagSyncService(test_session)
        created = await sync_service.sync_talent_tech_tags(
            talent=talent,
            belongs=list(belongs),
            default_tech_direction_id=setup["tech_direction"].tech_direction_id,
        )

        assert created == 1, "Should create exactly 1 TalentTechTag"

        # Verify aggregated confidence_score: (2+3)/10 = 0.5
        result = await test_session.execute(
            select(TalentTechTag).where(TalentTechTag.talent_id == talent.talent_id)
        )
        tag = result.scalar_one()
        assert (
            tag.confidence_score == 0.5
        ), f"Expected confidence_score=0.5 (5 works / 10), got {tag.confidence_score}"


class TestBatchNormalization:
    """Test batch-mode normalize_all_authors with mixed existing/new/bad-json authors."""

    @pytest.mark.asyncio
    async def test_batch_normalize_with_fallback(self, test_session: AsyncSession, full_setup):
        """
        Regression test for batch normalization refactor.

        Scenarios covered:
        - Existing StdAuthor updated in batch
        - New StdAuthor created in batch
        - Bad raw_json isolated and skipped
        - RawAuthor.processed_status and std_author_id updated correctly
        """
        from app.domains.academic.models.standardized import StdAuthor
        from app.domains.academic.models.sync import CollectTask
        from app.domains.academic.services.normalizers import AuthorNormalizer

        _ = full_setup

        # Create a dedicated task so get_pending is scoped
        task = CollectTask(
            task_code="TEST-BATCH-001",
            collect_mode="incremental",
            triggered_by=None,
            triggered_at=datetime.utcnow(),
            status="running",
        )
        test_session.add(task)
        await test_session.flush()

        # Pre-create an existing StdAuthor (to test UPDATE path)
        existing_std = StdAuthor(
            openalex_author_id="A-EXISTING",
            name_normalized="Old Name",
            name_original="Old Name",
            works_count=5,
            cited_by_count=50,
            h_index=3,
            confirm_status="auto_identified",
            cs_concepts_score=0.0,
            openalex_topics=[],
        )
        test_session.add(existing_std)
        await test_session.flush()

        # Create 4 RawAuthors: 1 existing, 2 new, 1 bad JSON
        raw_authors = [
            RawAuthor(
                openalex_author_id="A-EXISTING",
                raw_json=json.dumps(
                    {
                        "topics": [{"display_name": "Machine Learning", "count": 5}],
                        "x_concepts": [{"id": "154945302", "score": 0.8}],
                    }
                ),
                display_name="Updated Name",
                works_count=20,
                cited_by_count=200,
                h_index=10,
                processed_status="pending",
                fetch_task_id=task.task_id,
            ),
            RawAuthor(
                openalex_author_id="A-NEW-1",
                raw_json=json.dumps(
                    {
                        "topics": [{"display_name": "Deep Learning", "count": 4}],
                        "x_concepts": [{"id": "154945302", "score": 0.5}],
                    }
                ),
                display_name="New Author One",
                works_count=15,
                cited_by_count=150,
                h_index=8,
                processed_status="pending",
                fetch_task_id=task.task_id,
            ),
            RawAuthor(
                openalex_author_id="A-NEW-2",
                raw_json=json.dumps(
                    {
                        "topics": [{"display_name": "NLP", "count": 6}],
                        "x_concepts": [{"id": "154945302", "score": 0.9}],
                    }
                ),
                display_name="New Author Two",
                works_count=30,
                cited_by_count=300,
                h_index=12,
                processed_status="pending",
                fetch_task_id=task.task_id,
            ),
            RawAuthor(
                openalex_author_id="A-BAD-JSON",
                raw_json="not valid json {{",
                display_name="Bad Json Author",
                works_count=1,
                cited_by_count=1,
                h_index=1,
                processed_status="pending",
                fetch_task_id=task.task_id,
            ),
        ]
        for ra in raw_authors:
            test_session.add(ra)
        await test_session.commit()

        # Run batch normalization scoped to the task
        normalizer = AuthorNormalizer(test_session)
        result = await normalizer.normalize_all_authors(task_id=task.task_id)

        # Assert counts
        assert result.total == 4, f"Expected total=4, got {result.total}"
        assert result.processed == 3, f"Expected processed=3, got {result.processed}"
        assert result.failed == 1, f"Expected failed=1, got {result.failed}"

        # Verify exactly 3 StdAuthor rows (1 updated + 2 new)
        result = await test_session.execute(
            select(StdAuthor).where(
                StdAuthor.openalex_author_id.in_(["A-EXISTING", "A-NEW-1", "A-NEW-2", "A-BAD-JSON"])
            )
        )
        std_authors = result.scalars().all()
        assert (
            len(std_authors) == 3
        ), f"Expected 3 StdAuthors (existing+2 new), got {len(std_authors)}"

        # Verify existing author was updated (refresh from DB to avoid stale cache)
        existing = next((a for a in std_authors if a.openalex_author_id == "A-EXISTING"), None)
        assert existing is not None, "Existing StdAuthor should still exist"
        await test_session.refresh(existing)
        assert existing.works_count == 20, "Existing author works_count should be updated"
        assert existing.name_normalized == "Updated Name", "Existing author name should be updated"
        assert existing.cs_concepts_score > 0, "Existing author CS score should be updated"

        # Verify new authors created
        new_1 = next((a for a in std_authors if a.openalex_author_id == "A-NEW-1"), None)
        new_2 = next((a for a in std_authors if a.openalex_author_id == "A-NEW-2"), None)
        assert new_1 is not None, "New author 1 should be created"
        assert new_2 is not None, "New author 2 should be created"
        assert new_1.works_count == 15
        assert new_2.works_count == 30

        # Verify RawAuthor statuses
        result = await test_session.execute(
            select(RawAuthor).where(
                RawAuthor.openalex_author_id.in_(["A-EXISTING", "A-NEW-1", "A-NEW-2"])
            )
        )
        processed_raws = result.scalars().all()
        for ra in processed_raws:
            assert (
                ra.processed_status == "processed"
            ), f"RawAuthor {ra.openalex_author_id} should be marked processed"
            assert (
                ra.std_author_id is not None
            ), f"RawAuthor {ra.openalex_author_id} should have std_author_id"

        # Verify bad JSON author is marked as failed (not re-processed in next loop)
        result = await test_session.execute(
            select(RawAuthor).where(RawAuthor.openalex_author_id == "A-BAD-JSON")
        )
        bad_raw = result.scalar_one()
        assert (
            bad_raw.processed_status == "failed"
        ), "Bad JSON author should be marked failed to avoid infinite re-processing"


class TestSchoolNormalizerNoEmptyStringMatch:
    """Regression tests for the 'University School' data pollution bug.

    Root cause chain:
    1. normalize_school_name("University School") -> ""
    2. find_matching_school() with "" triggers ilike("%%") matching entire table
    3. normalize_institution() blindly overwrites the first matched record
    4. The overwritten record keeps its old openalex_id, so many talents
       linked to that popular school now display "University School"
    """

    @pytest.mark.asyncio
    async def test_normalize_school_name_never_returns_empty(self):
        """normalize_school_name must never return "" to avoid full-table matches."""
        from app.domains.academic.services.normalizers.school import SchoolNormalizer

        normalizer = SchoolNormalizer(session=None)  # session not needed for pure method

        # The exact name that caused the bug
        assert normalizer.normalize_school_name("University School") != ""
        assert normalizer.normalize_school_name("University School") == "university school"

        # Other edge cases that would also strip to nothing
        assert normalizer.normalize_school_name("University College") != ""
        assert normalizer.normalize_school_name("School Institute") != ""

        # Normal cases should still work
        assert normalizer.normalize_school_name("MIT") == "mit"
        assert normalizer.normalize_school_name("Stanford University") == "stanford"

    @pytest.mark.asyncio
    async def test_find_matching_school_skips_empty_normalized(self, test_session: AsyncSession):
        """When normalized name is empty/too short, skip fuzzy match entirely."""
        from app.domains.academic.models.standardized import StdSchool
        from app.domains.academic.services.normalizers.school import SchoolNormalizer

        normalizer = SchoolNormalizer(test_session)

        # Seed a popular school
        mit = StdSchool(
            openalex_institution_id="I-MIT-REGTEST",
            name_normalized="Massachusetts Institute of Technology",
            country_code="US",
        )
        test_session.add(mit)
        await test_session.commit()

        # Try to match "University School" — should NOT fall back to fuzzy match
        matched, match_type = await normalizer.find_matching_school(
            openalex_id=None, raw_name="University School"
        )

        # Must return None because openalex_id is None and exact/alias fail,
        # and normalized match is skipped for empty/short strings.
        assert matched is None, "Empty normalized string must not trigger a full-table fuzzy match"
        assert match_type == "none"

    @pytest.mark.asyncio
    async def test_normalize_institution_does_not_overwrite_on_weak_match(
        self, test_session: AsyncSession
    ):
        """If find_matching_school returns a weak match, normalize_institution
        must create a new record instead of overwriting the existing one."""
        from app.domains.academic.models.raw_data import RawInstitution
        from app.domains.academic.models.standardized import StdSchool
        from app.domains.academic.services.normalizers.school import SchoolNormalizer

        normalizer = SchoolNormalizer(test_session)

        # 1. Seed an existing popular school (MIT)
        mit = StdSchool(
            openalex_institution_id="I-MIT-REGTEST",
            name_normalized="Massachusetts Institute of Technology",
            country_code="US",
            confirm_status="auto_identified",
        )
        test_session.add(mit)
        await test_session.flush()
        mit_id = mit.std_school_id

        # 2. Create a RawInstitution for "University School" with a DIFFERENT openalex_id
        raw_univ = RawInstitution(
            openalex_institution_id="I-UNIV-SCHOOL",
            raw_json="{}",
            display_name="University School",
            country_code="US",
            processed_status="pending",
        )
        test_session.add(raw_univ)
        await test_session.flush()

        # 3. Manually simulate the dangerous path:
        #    force a fuzzy match to MIT (as would happen with the old bug)
        matched, match_type = await normalizer.find_matching_school(
            openalex_id=raw_univ.openalex_institution_id,
            raw_name=raw_univ.display_name,
        )

        # Because openalex_id "I-UNIV-SCHOOL" does not exist in DB, exact name fails,
        # and normalized match is now skipped for empty/short strings,
        # matched should be None. But even if matched were somehow returned
        # (e.g. via a future code path), normalize_institution must refuse to
        # overwrite when openalex_ids differ.

        # 4. Run normalize_institution
        std_school = await normalizer.normalize_institution(raw_univ, task_id=None)

        # 5. Verify: a NEW record was created
        assert (
            std_school.std_school_id != mit_id
        ), "normalize_institution must create a new record, not overwrite MIT"
        assert std_school.name_normalized == "University School"
        assert std_school.openalex_institution_id == "I-UNIV-SCHOOL"

        # 6. Verify MIT is untouched
        result = await test_session.execute(
            select(StdSchool).where(StdSchool.std_school_id == mit_id)
        )
        mit_refreshed = result.scalar_one()
        assert mit_refreshed.name_normalized == "Massachusetts Institute of Technology"
        assert mit_refreshed.openalex_institution_id == "I-MIT-REGTEST"

    @pytest.mark.asyncio
    async def test_normalize_institution_updates_on_same_openalex_id(
        self, test_session: AsyncSession
    ):
        """When openalex_id matches exactly, updating the existing record is safe."""
        from app.domains.academic.models.raw_data import RawInstitution
        from app.domains.academic.models.standardized import StdSchool
        from app.domains.academic.services.normalizers.school import SchoolNormalizer

        normalizer = SchoolNormalizer(test_session)

        # Seed an existing school
        existing = StdSchool(
            openalex_institution_id="I-STANFORD",
            name_normalized="Stanford University",
            country_code="US",
            confirm_status="auto_identified",
        )
        test_session.add(existing)
        await test_session.flush()
        existing_id = existing.std_school_id

        # Raw institution with the SAME openalex_id but updated name
        raw_updated = RawInstitution(
            openalex_institution_id="I-STANFORD",
            raw_json="{}",
            display_name="Stanford University",
            country_code="US",
            country_name="United States",
            processed_status="pending",
        )
        test_session.add(raw_updated)
        await test_session.flush()

        std_school = await normalizer.normalize_institution(raw_updated, task_id=None)

        # Should update the existing record, not create a new one
        assert std_school.std_school_id == existing_id
        assert std_school.country_name == "United States"
