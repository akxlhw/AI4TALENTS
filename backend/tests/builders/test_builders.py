"""
Tests for builders.
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.builders.base import BuildResult, extract_openalex_id, normalize_name
from app.builders.school_builder import SchoolBuilder, INSTITUTION_NAME_MAPPING
from app.builders.talent_builder import TalentBuilder


class TestBaseBuilder:
    """Tests for BaseBuilder."""

    def test_extract_openalex_id(self):
        """Test OpenAlex ID extraction."""
        # From URL
        assert extract_openalex_id("https://openalex.org/I123456") == "I123456"
        assert extract_openalex_id("https://openalex.org/I123456/") == "I123456"

        # From ID only
        assert extract_openalex_id("I123456") == "I123456"

        # Empty/None
        assert extract_openalex_id("") == ""
        assert extract_openalex_id(None) == ""

    def test_normalize_name(self):
        """Test name normalization."""
        assert normalize_name("MIT") == "mit"
        assert normalize_name("  Stanford University  ") == "stanford university"
        assert normalize_name("") == ""
        assert normalize_name(None) == ""

    def test_institution_name_mapping(self):
        """Test institution name mapping exists."""
        assert "massachusetts institute of technology" in INSTITUTION_NAME_MAPPING
        assert INSTITUTION_NAME_MAPPING["massachusetts institute of technology"] == "MIT"


class TestBuildResult:
    """Tests for BuildResult dataclass."""

    def test_build_result_creation(self):
        """Test creating a BuildResult."""
        result = BuildResult(
            success=True,
            records_processed=100,
            records_created=80,
            records_updated=20,
            records_failed=0,
            errors=[],
            started_at=datetime.now(),
            completed_at=datetime.now(),
        )

        assert result.success is True
        assert result.records_processed == 100
        assert result.records_created == 80
        assert result.records_updated == 20
        assert result.records_failed == 0

    def test_build_result_with_errors(self):
        """Test BuildResult with errors."""
        result = BuildResult(
            success=False,
            records_processed=100,
            records_created=90,
            records_updated=0,
            records_failed=10,
            errors=["Error 1", "Error 2"],
            started_at=datetime.now(),
            completed_at=datetime.now(),
        )

        assert result.success is False
        assert len(result.errors) == 2


class TestSchoolBuilder:
    """Tests for SchoolBuilder."""

    @pytest.fixture
    def mock_session(self):
        """Create mock session."""
        return AsyncMock()

    def test_builder_initialization(self, mock_session):
        """Test builder initialization."""
        builder = SchoolBuilder(mock_session, batch_id=1)

        assert builder.batch_id == 1
        assert builder.session == mock_session
        assert builder.errors == []


class TestTalentBuilder:
    """Tests for TalentBuilder."""

    @pytest.fixture
    def mock_session(self):
        """Create mock session."""
        return AsyncMock()

    def test_builder_initialization(self, mock_session):
        """Test builder initialization."""
        builder = TalentBuilder(mock_session, batch_id=1)

        assert builder.batch_id == 1
        assert builder.session == mock_session

    def test_identify_role_type_professor(self, mock_session):
        """Test role identification for professor."""
        builder = TalentBuilder(mock_session, batch_id=1)

        # Professor indicators
        raw_data = {
            "works_count": 50,
            "cited_by_count": 1000,
        }
        role = builder._identify_role_type(raw_data)
        assert role == "professor"

    def test_identify_role_type_student(self, mock_session):
        """Test role identification for student."""
        builder = TalentBuilder(mock_session, batch_id=1)

        # Student indicators
        raw_data = {
            "works_count": 2,
            "cited_by_count": 10,
        }
        role = builder._identify_role_type(raw_data)
        assert role == "student"

    def test_identify_role_type_graduate(self, mock_session):
        """Test role identification for graduate."""
        builder = TalentBuilder(mock_session, batch_id=1)

        # Graduate indicators
        raw_data = {
            "works_count": 15,
            "cited_by_count": 100,
        }
        role = builder._identify_role_type(raw_data)
        assert role == "graduated"

    def test_extract_topics(self, mock_session):
        """Test topic extraction."""
        builder = TalentBuilder(mock_session, batch_id=1)

        raw_data = {
            "x_concepts": [
                {"display_name": "Machine Learning", "score": 0.9},
                {"display_name": "Computer Science", "score": 0.8},
                {"display_name": "Artificial Intelligence", "score": 0.7},
            ]
        }

        topics = builder._extract_topics(raw_data)

        assert len(topics) == 3
        assert "Machine Learning" in topics
        assert "Computer Science" in topics

    def test_extract_orcid(self, mock_session):
        """Test ORCID extraction."""
        builder = TalentBuilder(mock_session, batch_id=1)

        # From URL
        assert builder._extract_orcid("https://orcid.org/0000-0001-2345-6789") == "0000-0001-2345-6789"

        # Already ID
        assert builder._extract_orcid("0000-0001-2345-6789") == "0000-0001-2345-6789"

        # None
        assert builder._extract_orcid(None) is None
