"""
Tests for CS concepts score calculation and filtering.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.standardized import StdAuthor
from app.services.common.cs_concepts import CORE_CS_CONCEPTS, CS_SCORE_THRESHOLD
from app.services.normalizers.author import AuthorNormalizer
from app.services.sync.author_sync import AuthorSyncService


class TestCSCoreCalculation:
    """Tests for CS score calculation in AuthorNormalizer."""

    @pytest.fixture
    def normalizer(self):
        """Create normalizer instance with mock session."""
        mock_session = AsyncMock()
        return AuthorNormalizer(mock_session)

    def test_calculate_cs_score_with_ai_background(self, normalizer):
        """AI background author should get high score."""
        raw_json = """{
            "x_concepts": [
                {"id": "154945302", "display_name": "Artificial intelligence", "score": 0.8},
                {"id": "119857082", "display_name": "Machine learning", "score": 0.6}
            ]
        }"""
        score = normalizer._calculate_cs_score(raw_json)
        assert score >= 0.5
        assert score <= 1.0

    def test_calculate_cs_score_with_cs_background(self, normalizer):
        """Computer science background author should get high score."""
        raw_json = """{
            "x_concepts": [
                {"id": "41008148", "display_name": "Computer science", "score": 0.9}
            ]
        }"""
        score = normalizer._calculate_cs_score(raw_json)
        assert score >= 0.5

    def test_calculate_cs_score_without_cs(self, normalizer):
        """Non-CS background author should get low score."""
        raw_json = """{
            "x_concepts": [
                {"id": "86803240", "display_name": "Biology", "score": 0.9},
                {"id": "54427621", "display_name": "Chemistry", "score": 0.8}
            ]
        }"""
        score = normalizer._calculate_cs_score(raw_json)
        assert score < CS_SCORE_THRESHOLD

    def test_calculate_cs_score_with_mixed_background(self, normalizer):
        """Mixed background author should get moderate score."""
        raw_json = """{
            "x_concepts": [
                {"id": "41008148", "display_name": "Computer science", "score": 0.3},
                {"id": "86803240", "display_name": "Biology", "score": 0.5}
            ]
        }"""
        score = normalizer._calculate_cs_score(raw_json)
        assert 0 < score < 1.0

    def test_calculate_cs_score_empty_concepts(self, normalizer):
        """Empty concepts should return 0.0."""
        raw_json = '{"x_concepts": []}'
        score = normalizer._calculate_cs_score(raw_json)
        assert score == 0.0

    def test_calculate_cs_score_invalid_json(self, normalizer):
        """Invalid JSON should return 0.0."""
        raw_json = "not valid json"
        score = normalizer._calculate_cs_score(raw_json)
        assert score == 0.0

    def test_calculate_cs_score_capped_at_one(self, normalizer):
        """Score should be capped at 1.0."""
        raw_json = """{
            "x_concepts": [
                {"id": "41008148", "display_name": "Computer science", "score": 0.9},
                {"id": "154945302", "display_name": "Artificial intelligence", "score": 0.8},
                {"id": "119857082", "display_name": "Machine learning", "score": 0.7}
            ]
        }"""
        score = normalizer._calculate_cs_score(raw_json)
        assert score == 1.0

    def test_core_cs_concepts_not_empty(self):
        """CORE_CS_CONCEPTS should not be empty."""
        assert len(CORE_CS_CONCEPTS) > 0

    def test_cs_score_threshold_reasonable(self):
        """CS_SCORE_THRESHOLD should be between 0 and 1."""
        assert 0 < CS_SCORE_THRESHOLD < 1


class TestAuthorSyncFiltering:
    """Tests for author sync filtering by CS score."""

    @pytest.fixture
    def sync_service(self):
        """Create sync service instance with mock session."""
        mock_session = AsyncMock()
        return AuthorSyncService(mock_session)

    @pytest.fixture
    def low_cs_author(self):
        """Create StdAuthor with low CS score."""
        author = MagicMock(spec=StdAuthor)
        author.std_author_id = 1
        author.openalex_author_id = "A123456"
        author.name_normalized = "Test Author"
        author.name_original = "Test Author"
        author.orcid = None
        author.works_count = 10
        author.cited_by_count = 100
        author.h_index = 5
        author.i10_index = 3
        author.openalex_topics = []
        author.cs_concepts_score = 0.1
        author.std_school_id = None
        return author

    @pytest.fixture
    def high_cs_author(self):
        """Create StdAuthor with high CS score."""
        author = MagicMock(spec=StdAuthor)
        author.std_author_id = 2
        author.openalex_author_id = "A789012"
        author.name_normalized = "CS Expert"
        author.name_original = "CS Expert"
        author.orcid = None
        author.works_count = 50
        author.cited_by_count = 500
        author.h_index = 15
        author.i10_index = 20
        author.openalex_topics = ["Machine Learning"]
        author.cs_concepts_score = 0.8
        author.std_school_id = None
        return author

    @pytest.mark.asyncio
    async def test_sync_filters_low_cs_score(self, sync_service, low_cs_author):
        """Author with low CS score should not be synced."""
        talent, is_new = await sync_service.sync_author_to_talent(low_cs_author)
        assert talent is None
        assert is_new is False

    @pytest.mark.asyncio
    async def test_sync_accepts_high_cs_score(self, sync_service, high_cs_author):
        """Author with high CS score should be synced."""
        # Mock the database query for existing talent
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        sync_service.session.execute.return_value = mock_result
        sync_service.session.flush = AsyncMock()

        talent, is_new = await sync_service.sync_author_to_talent(high_cs_author)
        # The talent should be created (not None)
        assert talent is not None
        assert is_new is True

    @pytest.mark.asyncio
    async def test_sync_filters_at_threshold(self, sync_service):
        """Author with CS score exactly at threshold should be filtered."""
        author = MagicMock(spec=StdAuthor)
        author.cs_concepts_score = CS_SCORE_THRESHOLD - 0.01
        author.name_normalized = "Threshold Author"
        author.openalex_author_id = "A999999"

        talent, is_new = await sync_service.sync_author_to_talent(author)
        assert talent is None

    @pytest.mark.asyncio
    async def test_sync_accepts_above_threshold(self, sync_service):
        """Author with CS score above threshold should be accepted."""
        author = MagicMock(spec=StdAuthor)
        author.cs_concepts_score = CS_SCORE_THRESHOLD + 0.01
        author.name_normalized = "Above Threshold"
        author.openalex_author_id = "A888888"
        author.std_author_id = 3
        author.name_original = "Above Threshold"
        author.orcid = None
        author.works_count = 10
        author.cited_by_count = 100
        author.h_index = 5
        author.i10_index = 3
        author.openalex_topics = []
        author.std_school_id = None

        # Mock the database query for existing talent
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        sync_service.session.execute.return_value = mock_result
        sync_service.session.flush = AsyncMock()

        talent, is_new = await sync_service.sync_author_to_talent(author)
        assert talent is not None

    @pytest.mark.asyncio
    async def test_sync_handles_none_cs_score(self, sync_service):
        """Author with None CS score should be filtered (treated as 0.0)."""
        author = MagicMock(spec=StdAuthor)
        author.cs_concepts_score = None
        author.name_normalized = "No Score Author"
        author.openalex_author_id = "A111111"

        talent, is_new = await sync_service.sync_author_to_talent(author)
        assert talent is None
        assert is_new is False
