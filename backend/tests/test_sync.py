"""
Tests for sync service and repositories.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.repositories.sync_repository import SyncBatchRepository


class TestSyncBatchRepository:
    """Tests for SyncBatchRepository."""

    @pytest.fixture
    def mock_session(self):
        """Create mock session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository instance."""
        return SyncBatchRepository(mock_session)

    @pytest.mark.asyncio
    async def test_create_batch(self, repo, mock_session):
        """Test creating a sync batch."""
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        batch = await repo.create_batch(
            batch_type="full",
            source_type="openalex",
        )

        assert batch is not None
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_batch(self, repo, mock_session):
        """Test starting a batch."""
        await repo.start_batch(batch_id=1)

        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_complete_batch_success(self, repo, mock_session):
        """Test completing a batch successfully."""
        await repo.complete_batch(
            batch_id=1,
            total_records=100,
            success_records=100,
            failed_records=0,
        )

        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_complete_batch_partial(self, repo, mock_session):
        """Test completing a batch with partial failures."""
        await repo.complete_batch(
            batch_id=1,
            total_records=100,
            success_records=90,
            failed_records=10,
        )

        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_fail_batch(self, repo, mock_session):
        """Test failing a batch."""
        await repo.fail_batch(
            batch_id=1,
            error_message="Test error",
        )

        mock_session.execute.assert_called_once()


class TestSyncService:
    """Tests for SyncService."""

    @pytest.fixture
    def mock_session(self):
        """Create mock session."""
        session = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.fixture
    def mock_client(self):
        """Create mock OpenAlex client."""
        client = MagicMock()
        client.iterate_institutions = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_extract_id(self):
        """Test ID extraction from URL using extract_openalex_id."""
        from app.builders.base import extract_openalex_id

        # Test URL format
        assert extract_openalex_id("https://openalex.org/I123456") == "I123456"

        # Test ID format
        assert extract_openalex_id("I123456") == "I123456"

        # Test with trailing slash
        assert extract_openalex_id("https://openalex.org/I123456/") == "I123456"
