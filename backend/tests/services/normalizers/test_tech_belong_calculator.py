"""
Tests for TechBelongCalculator.
Covers: calculate_for_venue with raw works, author grouping, year tracking.
"""

import json

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.academic.models.raw_data import AuthorTechBelong, RawWork
from app.domains.academic.models.venue import Venue
from app.domains.academic.services.normalizers.tech_belong import TechBelongCalculator


class TestTechBelongCalculator:
    """Tests for TechBelongCalculator."""

    @pytest.fixture
    async def calculator(self, test_session: AsyncSession):
        """Create TechBelongCalculator instance."""
        return TechBelongCalculator(test_session)

    @pytest.fixture
    async def sample_venue(self, test_session: AsyncSession):
        """Create a sample venue."""
        venue = Venue(
            venue_code="TEST-VENUE",
            venue_name="Test Conference",
            venue_type="conference",
            openalex_source_id="S-TEST-123",
            is_enabled=True,
        )
        test_session.add(venue)
        await test_session.commit()
        await test_session.refresh(venue)
        return venue

    @pytest.fixture
    async def sample_tech_domain(self, test_session: AsyncSession):
        """Create a sample tech domain."""
        from app.domains.academic.models.tech_domain import TechDomain
        domain = TechDomain(
            domain_code="TEST",
            domain_name="Test Domain",
            is_enabled=True,
        )
        test_session.add(domain)
        await test_session.commit()
        await test_session.refresh(domain)
        return domain

    @pytest.fixture
    async def sample_works(self, test_session: AsyncSession, sample_venue):
        """Create sample raw works for the venue."""
        works = [
            RawWork(
                openalex_work_id="W1",
                raw_json='{}',
                source_id="S-TEST-123",
                publication_year=2020,
                author_ids=json.dumps(["A1", "A2"]),
            ),
            RawWork(
                openalex_work_id="W2",
                raw_json='{}',
                source_id="S-TEST-123",
                publication_year=2021,
                author_ids=json.dumps(["A1", "A3"]),
            ),
            RawWork(
                openalex_work_id="W3",
                raw_json='{}',
                source_id="S-TEST-123",
                publication_year=2022,
                author_ids=json.dumps(["A1"]),
            ),
            RawWork(
                openalex_work_id="W4",
                raw_json='{}',
                source_id="S-TEST-123",
                publication_year=2021,
                author_ids='null',  # parses to None, causes TypeError in loop (caught by source)
            ),
            RawWork(
                openalex_work_id="W5",
                raw_json='{}',
                source_id="S-TEST-123",
                publication_year=2023,
                author_ids=None,
            ),
        ]
        for w in works:
            test_session.add(w)
        await test_session.commit()
        return works

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_calculate_for_venue(self, calculator: TechBelongCalculator, sample_venue, sample_tech_domain, sample_works, test_session):
        """Test calculate_for_venue creates correct AuthorTechBelong records."""
        count = await calculator.calculate_for_venue(sample_venue.venue_id, tech_domain_id=sample_tech_domain.tech_domain_id, task_id=None)

        # A1 appears in 3 works, A2 in 1, A3 in 1
        assert count == 3

        # Verify records in DB
        from sqlalchemy import select

        result = await test_session.execute(
            select(AuthorTechBelong).where(AuthorTechBelong.source_venue_id == sample_venue.venue_id)
        )
        belongs = result.scalars().all()
        assert len(belongs) == 3

        a1 = next(b for b in belongs if b.openalex_author_id == "A1")
        assert a1.work_count_in_venue == 3
        assert a1.first_work_year == 2020
        assert a1.last_work_year == 2022
        assert a1.tech_domain_id == 1
        assert a1.source_task_id is None

        a2 = next(b for b in belongs if b.openalex_author_id == "A2")
        assert a2.work_count_in_venue == 1
        assert a2.first_work_year == 2020
        assert a2.last_work_year == 2020

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_calculate_for_venue_updates_existing(self, calculator: TechBelongCalculator, sample_venue, sample_tech_domain, sample_works, test_session):
        """Test calculate_for_venue updates existing AuthorTechBelong records."""
        # Pre-create an existing record
        existing = AuthorTechBelong(
            openalex_author_id="A1",
            tech_domain_id=sample_tech_domain.tech_domain_id,
            source_venue_id=sample_venue.venue_id,
            work_count_in_venue=1,
            first_work_year=2019,
            last_work_year=2019,
        )
        test_session.add(existing)
        await test_session.commit()

        count = await calculator.calculate_for_venue(sample_venue.venue_id, tech_domain_id=sample_tech_domain.tech_domain_id)

        assert count == 3
        assert existing.work_count_in_venue == 3
        assert existing.first_work_year == 2020
        assert existing.last_work_year == 2022

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_calculate_for_venue_no_venue(self, calculator: TechBelongCalculator):
        """Test calculate_for_venue with non-existent venue returns 0."""
        count = await calculator.calculate_for_venue(99999, tech_domain_id=1)
        assert count == 0

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_calculate_for_venue_no_source_id(self, calculator: TechBelongCalculator, test_session):
        """Test calculate_for_venue with venue missing openalex_source_id returns 0."""
        venue = Venue(
            venue_code="NO-SOURCE",
            venue_name="No Source Venue",
            openalex_source_id=None,
            is_enabled=True,
        )
        test_session.add(venue)
        await test_session.commit()
        await test_session.refresh(venue)

        count = await calculator.calculate_for_venue(venue.venue_id, tech_domain_id=1)
        assert count == 0

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_calculate_for_venue_no_works(self, calculator: TechBelongCalculator, sample_venue, sample_tech_domain):
        """Test calculate_for_venue with no matching works returns 0."""
        count = await calculator.calculate_for_venue(sample_venue.venue_id, tech_domain_id=sample_tech_domain.tech_domain_id)
        assert count == 0

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_calculate_for_venue_skips_invalid_author_ids(self, calculator: TechBelongCalculator, sample_venue, sample_tech_domain, test_session):
        """Test calculate_for_venue skips works with invalid author_ids."""
        work = RawWork(
            openalex_work_id="W-INVALID",
            raw_json='{}',
            source_id="S-TEST-123",
            publication_year=2021,
            author_ids='null',  # parses to None, loop raises TypeError (caught by source)
        )
        test_session.add(work)
        await test_session.commit()

        count = await calculator.calculate_for_venue(sample_venue.venue_id, tech_domain_id=sample_tech_domain.tech_domain_id)
        # No valid authors, so count should be 0
        assert count == 0
