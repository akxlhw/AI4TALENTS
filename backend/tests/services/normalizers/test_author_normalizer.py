"""
Tests for AuthorNormalizer.
Covers: name normalization, raw_json parsing, CS score calculation, create_std_author.
"""

import json

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.academic.models.raw_data import RawAuthor
from app.domains.academic.models.standardized import StdAuthor, StdSchool
from app.domains.academic.services.normalizers.author import AuthorNormalizer


class TestAuthorNormalizerUnit:
    """Unit tests for AuthorNormalizer methods that don't need DB."""

    @pytest.fixture
    def normalizer(self, test_session: AsyncSession):
        """Create AuthorNormalizer instance (session not used for unit tests)."""
        return AuthorNormalizer(test_session)

    def test_normalize_author_name(self, normalizer: AuthorNormalizer):
        """Test name normalization capitalizes correctly."""
        assert normalizer.normalize_author_name("john doe") == "John Doe"
        assert normalizer.normalize_author_name("JANE SMITH") == "Jane Smith"
        assert normalizer.normalize_author_name("") == ""
        assert normalizer.normalize_author_name("a") == "A"

    def test_normalize_author_name_extra_spaces(self, normalizer: AuthorNormalizer):
        """Test name normalization removes extra spaces."""
        assert normalizer.normalize_author_name("  john   doe  ") == "John Doe"

    def test_parse_raw_json_empty(self, normalizer: AuthorNormalizer):
        """Test parsing empty raw_json."""
        topics, score = normalizer._parse_raw_json("")
        assert topics == []
        assert score == 0.0

    def test_parse_raw_json_with_topics(self, normalizer: AuthorNormalizer):
        """Test extracting topics from raw_json."""
        raw = json.dumps(
            {
                "topics": [
                    {"display_name": "Machine Learning", "count": 10},
                    {"display_name": "Deep Learning", "count": 5},
                    {"display_name": "Low Count", "count": 1},
                ]
            }
        )
        topics, score = normalizer._parse_raw_json(raw)
        assert "Machine Learning" in topics
        assert "Deep Learning" in topics
        assert "Low Count" not in topics

    def test_parse_raw_json_cs_score(self, normalizer: AuthorNormalizer):
        """Test calculating CS score from raw_json."""
        raw = json.dumps(
            {
                "x_concepts": [
                    {"id": "https://openalex.org/C41008148", "score": 0.8},
                    {"id": "https://openalex.org/C154945302", "score": 0.5},
                ]
            }
        )
        topics, score = normalizer._parse_raw_json(raw)
        # Only the numeric part of concept IDs are matched
        assert score == 0.0  # URL format not matched by CORE_CS_CONCEPTS

    def test_parse_raw_json_cs_score_numeric_id(self, normalizer: AuthorNormalizer):
        """Test CS score with numeric concept IDs."""
        raw = json.dumps(
            {
                "x_concepts": [
                    {"id": "41008148", "score": 0.8},
                    {"id": "154945302", "score": 0.5},
                ]
            }
        )
        topics, score = normalizer._parse_raw_json(raw)
        assert score == pytest.approx(1.0)  # min(1.3, 1.0)

    def test_extract_topics(self, normalizer: AuthorNormalizer):
        """Test _extract_topics helper."""
        raw = json.dumps({"topics": [{"display_name": "AI", "count": 5}]})
        assert normalizer._extract_topics(raw) == ["AI"]

    def test_calculate_cs_score(self, normalizer: AuthorNormalizer):
        """Test _calculate_cs_score helper."""
        raw = json.dumps({"x_concepts": [{"id": "41008148", "score": 0.9}]})
        assert normalizer._calculate_cs_score(raw) == pytest.approx(0.9)

    def test_parse_raw_json_invalid_json(self, normalizer: AuthorNormalizer):
        """Test parsing invalid JSON returns empty results."""
        topics, score = normalizer._parse_raw_json("not json")
        assert topics == []
        assert score == 0.0


class TestAuthorNormalizerIntegration:
    """Integration tests for AuthorNormalizer with database."""

    @pytest.fixture
    async def normalizer(self, test_session: AsyncSession):
        """Create AuthorNormalizer instance."""
        return AuthorNormalizer(test_session)

    @pytest.fixture
    async def sample_raw_author(self, test_session: AsyncSession):
        """Create a sample raw author."""
        raw = RawAuthor(
            openalex_author_id="A123456789",
            display_name="test author",
            raw_json=json.dumps(
                {
                    "topics": [{"display_name": "Machine Learning", "count": 10}],
                    "x_concepts": [{"id": "41008148", "score": 0.85}],
                }
            ),
            works_count=25,
            cited_by_count=500,
            h_index=10,
            i10_index=5,
        )
        test_session.add(raw)
        await test_session.commit()
        await test_session.refresh(raw)
        return raw

    @pytest.fixture
    async def sample_std_school(self, test_session: AsyncSession):
        """Create a sample standardized school."""
        school = StdSchool(
            openalex_institution_id="I987654321",
            name_normalized="Test University",
            country_code="US",
        )
        test_session.add(school)
        await test_session.commit()
        await test_session.refresh(school)
        return school

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_find_std_author_not_found(self, normalizer: AuthorNormalizer):
        """Test finding non-existent std author."""
        result = await normalizer.find_std_author("A999999999")
        assert result is None

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_create_std_author(
        self, normalizer: AuthorNormalizer, sample_raw_author, test_session
    ):
        """Test creating StdAuthor from RawAuthor."""
        std = await normalizer.create_std_author(sample_raw_author)

        assert std.std_author_id is not None
        assert std.openalex_author_id == "A123456789"
        assert std.name_normalized == "Test Author"
        assert std.name_original == "test author"
        assert std.works_count == 25
        assert std.cs_concepts_score == pytest.approx(0.85)
        assert "Machine Learning" in std.openalex_topics
        assert std.confirm_status == "auto_identified"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_create_std_author_with_school(
        self, normalizer: AuthorNormalizer, sample_raw_author, sample_std_school, test_session
    ):
        """Test creating StdAuthor with school linkage."""
        std = await normalizer.create_std_author(
            sample_raw_author, std_school_id=sample_std_school.std_school_id
        )

        assert std.std_school_id == sample_std_school.std_school_id
        assert std.confidence_score == pytest.approx(0.8)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_normalize_author_creates_new(
        self, normalizer: AuthorNormalizer, sample_raw_author, test_session
    ):
        """Test normalize_author creates new StdAuthor when not exists."""
        std = await normalizer.normalize_author(sample_raw_author)

        assert std.std_author_id is not None
        assert std.name_normalized == "Test Author"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_normalize_author_updates_existing(
        self, normalizer: AuthorNormalizer, sample_raw_author, test_session
    ):
        """Test normalize_author updates existing StdAuthor."""
        # Create existing StdAuthor
        existing = StdAuthor(
            openalex_author_id="A123456789",
            name_normalized="Old Name",
            works_count=10,
        )
        test_session.add(existing)
        await test_session.commit()

        # Update via normalize_author
        updated = await normalizer.normalize_author(sample_raw_author)

        assert updated.std_author_id == existing.std_author_id
        assert updated.name_normalized == "Test Author"
        assert updated.works_count == 25
        assert updated.cs_concepts_score == pytest.approx(0.85)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_batch_find_std_authors(self, normalizer: AuthorNormalizer, test_session):
        """Test batch finding std authors by OpenAlex IDs."""
        std1 = StdAuthor(openalex_author_id="A111", name_normalized="One")
        std2 = StdAuthor(openalex_author_id="A222", name_normalized="Two")
        test_session.add_all([std1, std2])
        await test_session.commit()

        result = await normalizer._batch_find_std_authors(["A111", "A222", "A999"])
        assert len(result) == 2
        assert result["A111"].name_normalized == "One"
        assert result["A222"].name_normalized == "Two"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_batch_find_std_authors_empty(self, normalizer: AuthorNormalizer):
        """Test batch finding with empty list."""
        result = await normalizer._batch_find_std_authors([])
        assert result == {}

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_batch_find_std_schools(
        self, normalizer: AuthorNormalizer, sample_std_school, test_session
    ):
        """Test batch finding std schools by institution IDs."""
        result = await normalizer._batch_find_std_schools(["I987654321", "I000"])
        assert len(result) == 1
        assert result["I987654321"] == sample_std_school.std_school_id

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_build_std_author_values(self, normalizer: AuthorNormalizer, sample_raw_author):
        """Test _build_std_author_values produces correct dict."""
        values = normalizer._build_std_author_values(
            sample_raw_author, topics=["AI"], cs_score=0.9, std_school_id=None, task_id=1
        )
        assert values["openalex_author_id"] == "A123456789"
        assert values["name_normalized"] == "Test Author"
        assert values["openalex_topics"] == ["AI"]
        assert values["cs_concepts_score"] == pytest.approx(0.9)
        assert values["source_task_id"] == 1
        assert values["confirm_status"] == "auto_identified"
