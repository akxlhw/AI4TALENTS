"""
Tests for sync service and repositories.
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

from app.repositories.sync_repository import SyncBatchRepository, RawSourceRecordRepository
from app.models.sync import SyncBatch, RawSourceRecord
from app.models.enums import SyncJobStatus, SourceType


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


class TestRawSourceRecordRepository:
    """Tests for RawSourceRecordRepository."""

    @pytest.fixture
    def mock_session(self):
        """Create mock session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository instance."""
        return RawSourceRecordRepository(mock_session)

    @pytest.mark.asyncio
    async def test_save_record(self, repo, mock_session):
        """Test saving a raw record."""
        mock_session.flush = AsyncMock()

        record = await repo.save_record(
            batch_id=1,
            source_type="institution",
            source_id="I123456",
            raw_data={"id": "I123456", "display_name": "MIT"},
        )

        assert record is not None
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_records_batch(self, repo, mock_session):
        """Test saving multiple records."""
        mock_session.flush = AsyncMock()

        records = [
            {"id": "https://openalex.org/I1", "display_name": "MIT"},
            {"id": "https://openalex.org/I2", "display_name": "Stanford"},
        ]

        count = await repo.save_records_batch(
            batch_id=1,
            source_type="institution",
            records=records,
        )

        assert count == 2
        assert mock_session.add.call_count == 2

    @pytest.mark.asyncio
    async def test_mark_processed(self, repo, mock_session):
        """Test marking a record as processed."""
        await repo.mark_processed(record_id=1, status="processed")

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
        """Test ID extraction from URL."""
        from app.services.sync_service import SyncService

        # Test URL format
        assert SyncService._extract_id("https://openalex.org/I123456") == "I123456"

        # Test ID format
        assert SyncService._extract_id("I123456") == "I123456"

        # Test with trailing slash
        assert SyncService._extract_id("https://openalex.org/I123456/") == "I123456"
