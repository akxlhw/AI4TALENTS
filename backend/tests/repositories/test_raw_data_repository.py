"""
Tests for RawAuthorRepository batch_upsert functionality.

Tests the PostgreSQL INSERT ON CONFLICT batch upsert for efficient data operations.
"""

import json

import pytest

from app.domains.academic.models.raw_data import RawAuthor
from app.domains.academic.repositories.raw_data_repository import RawAuthorRepository


class TestRawAuthorRepository:
    """Tests for RawAuthorRepository."""

    @pytest.fixture
    def repo(self, test_session):
        """Create a repository instance."""
        return RawAuthorRepository(test_session)

    @pytest.fixture
    def sample_author_data(self):
        """Sample author data for testing."""
        return {
            "openalex_author_id": "A12345",
            "raw_json": json.dumps({"id": "A12345", "display_name": "Test Author"}),
            "display_name": "Test Author",
            "orcid": "0000-0001-2345-6789",
            "works_count": 50,
            "cited_by_count": 1000,
            "h_index": 15,
            "i10_index": 25,
            "last_known_institution_id": "I999",
            "last_known_institution_name": "Test University",
        }

    # ========== batch_upsert tests ==========

    @pytest.mark.asyncio
    async def test_batch_upsert_empty_list(self, repo):
        """Test batch_upsert with empty list returns 0."""
        result = await repo.batch_upsert([])
        assert result == 0

    @pytest.mark.asyncio
    async def test_batch_upsert_single_insert(self, repo, sample_author_data):
        """Test batch_upsert inserts a single new author."""
        author = RawAuthor(**sample_author_data)
        result = await repo.batch_upsert([author])

        assert result == 1

        # Verify author was inserted
        inserted = await repo.get_by_openalex_id("A12345")
        assert inserted is not None
        assert inserted.display_name == "Test Author"
        assert inserted.works_count == 50

    @pytest.mark.asyncio
    async def test_batch_upsert_multiple_inserts(self, repo):
        """Test batch_upsert inserts multiple new authors."""
        authors = [
            RawAuthor(
                openalex_author_id=f"A{i:05d}",
                raw_json=json.dumps({"id": f"A{i:05d}", "display_name": f"Author {i}"}),
                display_name=f"Author {i}",
                works_count=i * 10,
                cited_by_count=i * 100,
                h_index=i,
            )
            for i in range(1, 4)
        ]

        result = await repo.batch_upsert(authors)
        assert result == 3

        # Verify all authors were inserted
        for i in range(1, 4):
            author = await repo.get_by_openalex_id(f"A{i:05d}")
            assert author is not None
            assert author.display_name == f"Author {i}"

    @pytest.mark.asyncio
    async def test_batch_upsert_update_existing(self, repo, sample_author_data):
        """Test batch_upsert updates existing author."""
        # Insert initial author
        initial = RawAuthor(**sample_author_data)
        await repo.batch_upsert([initial])

        # Update with new data
        updated_data = sample_author_data.copy()
        updated_data["works_count"] = 100
        updated_data["h_index"] = 20
        updated_author = RawAuthor(**updated_data)

        result = await repo.batch_upsert([updated_author])
        assert result == 1

        # Verify author was updated
        check = await repo.get_by_openalex_id("A12345")
        assert check.works_count == 100
        assert check.h_index == 20

    @pytest.mark.asyncio
    async def test_batch_upsert_mixed_insert_update(self, repo):
        """Test batch_upsert handles mix of new and existing authors."""
        # Insert initial author
        initial = RawAuthor(
            openalex_author_id="A00001",
            raw_json=json.dumps({"id": "A00001"}),
            display_name="Initial Author",
            works_count=10,
        )
        await repo.batch_upsert([initial])

        # Mix: update existing + insert new
        authors = [
            # Update existing
            RawAuthor(
                openalex_author_id="A00001",
                raw_json=json.dumps({"id": "A00001"}),
                display_name="Updated Author",
                works_count=20,
            ),
            # Insert new
            RawAuthor(
                openalex_author_id="A00002",
                raw_json=json.dumps({"id": "A00002"}),
                display_name="New Author",
                works_count=30,
            ),
        ]

        result = await repo.batch_upsert(authors)
        assert result == 2

        # Verify update
        updated = await repo.get_by_openalex_id("A00001")
        assert updated.display_name == "Updated Author"
        assert updated.works_count == 20

        # Verify insert
        new = await repo.get_by_openalex_id("A00002")
        assert new.display_name == "New Author"
        assert new.works_count == 30

    @pytest.mark.asyncio
    async def test_batch_upsert_large_batch(self, repo):
        """Test batch_upsert handles large batches."""
        # Create 100 authors
        authors = [
            RawAuthor(
                openalex_author_id=f"A{i:06d}",
                raw_json=json.dumps({"id": f"A{i:06d}"}),
                display_name=f"Author {i}",
                works_count=i,
            )
            for i in range(100)
        ]

        result = await repo.batch_upsert(authors)
        assert result == 100

        # Spot check a few
        check1 = await repo.get_by_openalex_id("A000000")
        assert check1.display_name == "Author 0"

        check50 = await repo.get_by_openalex_id("A000050")
        assert check50.display_name == "Author 50"

        check99 = await repo.get_by_openalex_id("A000099")
        assert check99.display_name == "Author 99"
