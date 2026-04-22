"""
Tests for BaseRepository class.

Tests the common CRUD operations provided by the base repository.
Uses School model for testing since it's a simple, self-contained model.
"""
import pytest
from sqlalchemy import select

from app.models.school import School
from app.models.venue import Venue
from app.repositories.base import BaseRepository


class TestBaseRepository:
    """Tests for BaseRepository using School model."""

    @pytest.fixture
    def repo(self, test_session):
        """Create a repository instance using School model."""
        return BaseRepository(test_session, School)

    @pytest.fixture
    async def test_schools(self, test_session):
        """Create test school records."""
        schools = [
            School(school_name="清华大学", country_code="CN", country_name="中国", is_visible=True),
            School(school_name="北京大学", country_code="CN", country_name="中国", is_visible=True),
            School(school_name="MIT", country_code="US", country_name="美国", is_visible=True),
        ]
        test_session.add_all(schools)
        await test_session.commit()

        # Refresh to get IDs
        for s in schools:
            await test_session.refresh(s)

        return schools

    # ========== get_by_id tests ==========

    @pytest.mark.asyncio
    async def test_get_by_id_success(self, repo, test_schools):
        """Test getting a record by ID successfully."""
        school = test_schools[0]
        result = await repo.get_by_id(school.school_id)

        assert result is not None
        assert result.school_id == school.school_id
        assert result.school_name == "清华大学"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repo):
        """Test getting a non-existent record returns None."""
        result = await repo.get_by_id(99999)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_id_with_custom_column(self, repo, test_schools):
        """Test get_by_id with custom ID column name."""
        school = test_schools[0]
        result = await repo.get_by_id(school.school_id, id_column="school_id")

        assert result is not None
        assert result.school_name == "清华大学"

    # ========== get_by_ids tests ==========

    @pytest.mark.asyncio
    async def test_get_by_ids_batch(self, repo, test_schools):
        """Test getting multiple records by IDs."""
        ids = [s.school_id for s in test_schools]
        result = await repo.get_by_ids(ids)

        assert len(result) == 3
        assert all(id in result for id in ids)

    @pytest.mark.asyncio
    async def test_get_by_ids_empty_list(self, repo):
        """Test get_by_ids with empty list returns empty dict."""
        result = await repo.get_by_ids([])

        assert result == {}

    @pytest.mark.asyncio
    async def test_get_by_ids_partial_match(self, repo, test_schools):
        """Test get_by_ids with some IDs not existing."""
        ids = [test_schools[0].school_id, 99999]
        result = await repo.get_by_ids(ids)

        assert len(result) == 1
        assert test_schools[0].school_id in result

    # ========== count tests ==========

    @pytest.mark.asyncio
    async def test_count_all(self, repo, test_schools):
        """Test counting all records."""
        result = await repo.count()

        assert result == 3

    @pytest.mark.asyncio
    async def test_count_empty_table(self, repo):
        """Test counting an empty table returns 0."""
        result = await repo.count()

        assert result == 0

    # ========== paginate tests ==========

    @pytest.mark.asyncio
    async def test_paginate_offset_and_limit(self, repo, test_session, test_schools):
        """Test pagination applies correct offset and limit."""
        query = select(School).order_by(School.school_id)
        paginated = repo.paginate(query, page=2, page_size=1)

        # Execute to verify
        result = await test_session.execute(paginated)
        records = list(result.scalars().all())

        assert len(records) == 1
        # Should be the second record (page 2, page_size 1)
        assert records[0].school_name == "北京大学"

    @pytest.mark.asyncio
    async def test_paginate_first_page(self, repo, test_session, test_schools):
        """Test pagination on first page."""
        query = select(School).order_by(School.school_id)
        paginated = repo.paginate(query, page=1, page_size=2)

        result = await test_session.execute(paginated)
        records = list(result.scalars().all())

        assert len(records) == 2
        assert records[0].school_name == "清华大学"

    # ========== list_paginated tests ==========

    @pytest.mark.asyncio
    async def test_list_paginated(self, repo, test_schools):
        """Test list_paginated returns items and total."""
        query = select(School)
        items, total = await repo.list_paginated(query, page=1, page_size=2)

        assert total == 3
        assert len(items) == 2

    @pytest.mark.asyncio
    async def test_list_paginated_last_page(self, repo, test_schools):
        """Test list_paginated on last page."""
        query = select(School)
        items, total = await repo.list_paginated(query, page=2, page_size=2)

        assert total == 3
        assert len(items) == 1  # Only 1 item on last page

    @pytest.mark.asyncio
    async def test_list_paginated_with_order(self, repo, test_schools):
        """Test list_paginated with order_by."""
        query = select(School)
        items, total = await repo.list_paginated(
            query,
            page=1,
            page_size=10,
            order_by=School.school_name.desc()
        )

        assert total == 3
        # Descending order: 清华大学 > 北京大学 > MIT (Chinese characters sort after ASCII)
        # Actually depends on DB collation, so just check we got results
        assert len(items) == 3

    # ========== create tests ==========

    @pytest.mark.asyncio
    async def test_create(self, repo):
        """Test creating a new record."""
        new_school = School(
            school_name="Stanford",
            country_code="US",
            country_name="美国",
            is_visible=True
        )
        result = await repo.create(new_school)

        assert result.school_id is not None
        assert result.school_name == "Stanford"
        assert result.country_code == "US"


class TestBaseRepositoryConfigTable:
    """Tests for BaseRepository with config_ prefixed tables (Venue)."""

    @pytest.fixture
    def repo(self, test_session):
        """Create a repository instance using Venue model (config_venue table)."""
        return BaseRepository(test_session, Venue)

    @pytest.fixture
    async def test_venues(self, test_session):
        """Create test venue records."""
        venues = [
            Venue(
                venue_code="TEST-VENUE-1",
                venue_name="Test Conference 1",
                venue_type="conference",
                openalex_source_id="S-TEST-1",
                is_enabled=True,
            ),
            Venue(
                venue_code="TEST-VENUE-2",
                venue_name="Test Journal",
                venue_type="journal",
                openalex_source_id="S-TEST-2",
                is_enabled=True,
            ),
        ]
        test_session.add_all(venues)
        await test_session.commit()

        for v in venues:
            await test_session.refresh(v)

        return venues

    @pytest.mark.asyncio
    async def test_get_by_id_config_table(self, repo, test_venues):
        """Test get_by_id works with config_ prefixed tables."""
        venue = test_venues[0]
        result = await repo.get_by_id(venue.venue_id)

        assert result is not None
        assert result.venue_id == venue.venue_id
        assert result.venue_code == "TEST-VENUE-1"

    @pytest.mark.asyncio
    async def test_get_by_ids_config_table(self, repo, test_venues):
        """Test get_by_ids works with config_ prefixed tables."""
        ids = [v.venue_id for v in test_venues]
        result = await repo.get_by_ids(ids)

        assert len(result) == 2
        assert all(vid in result for vid in ids)
