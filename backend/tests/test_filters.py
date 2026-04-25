"""
Tests for filter parameter dataclasses.

Tests the filter parameter objects used by repository methods.
"""

from app.schemas.filters import (
    CollectTaskFilterParams,
    PaginationParams,
    TalentFilterParams,
    VenueFilterParams,
)


class TestPaginationParams:
    """Tests for PaginationParams."""

    def test_default_values(self):
        """Test default pagination values."""
        params = PaginationParams()
        assert params.page == 1
        assert params.page_size == 20

    def test_custom_values(self):
        """Test custom pagination values."""
        params = PaginationParams(page=3, page_size=50)
        assert params.page == 3
        assert params.page_size == 50

    def test_offset_calculation(self):
        """Test offset property calculation."""
        # First page
        params = PaginationParams(page=1, page_size=20)
        assert params.offset == 0

        # Second page
        params = PaginationParams(page=2, page_size=20)
        assert params.offset == 20

        # Custom values
        params = PaginationParams(page=5, page_size=50)
        assert params.offset == 200

    def test_from_dict(self):
        """Test creating from dictionary."""
        params = PaginationParams.from_dict({"page": 2, "page_size": 30})
        assert params.page == 2
        assert params.page_size == 30

    def test_from_dict_missing_values(self):
        """Test from_dict with missing values uses defaults."""
        params = PaginationParams.from_dict({})
        assert params.page == 1
        assert params.page_size == 20


class TestTalentFilterParams:
    """Tests for TalentFilterParams."""

    def test_default_values(self):
        """Test default filter values."""
        params = TalentFilterParams()
        assert params.school_id is None
        assert params.country_code is None
        assert params.role_type is None
        assert params.visible_only is True

    def test_has_filters_false_when_empty(self):
        """Test has_filters returns False when no filters set."""
        params = TalentFilterParams()
        assert params.has_filters() is False

    def test_has_filters_true_when_set(self):
        """Test has_filters returns True when filters are set."""
        params = TalentFilterParams(school_id=123)
        assert params.has_filters() is True

        params = TalentFilterParams(keyword="AI")
        assert params.has_filters() is True

        params = TalentFilterParams(min_citations=100)
        assert params.has_filters() is True

    def test_has_filters_with_is_graduated(self):
        """Test has_filters correctly handles is_graduated."""
        params = TalentFilterParams(is_graduated=True)
        assert params.has_filters() is True

        params = TalentFilterParams(is_graduated=False)
        assert params.has_filters() is True

    def test_to_dict(self):
        """Test serialization to dictionary."""
        params = TalentFilterParams(
            school_id=1,
            country_code="US",
            role_type="professor",
            min_works=10,
        )
        result = params.to_dict()

        assert result["school_id"] == 1
        assert result["country_code"] == "US"
        assert result["role_type"] == "professor"
        assert result["min_works"] == 10
        assert "visible_only" not in result  # Not included in to_dict

    def test_to_dict_excludes_none(self):
        """Test to_dict excludes None values."""
        params = TalentFilterParams(school_id=1)
        result = params.to_dict()

        assert "school_id" in result
        assert "country_code" not in result
        assert "role_type" not in result

    def test_from_dict(self):
        """Test creating from dictionary."""
        params = TalentFilterParams.from_dict(
            {
                "school_id": 1,
                "country_code": "CN",
                "role_type": "phd",
                "visible_only": False,
            }
        )

        assert params.school_id == 1
        assert params.country_code == "CN"
        assert params.role_type == "phd"
        assert params.visible_only is False

    def test_from_dict_missing_values(self):
        """Test from_dict with missing values."""
        params = TalentFilterParams.from_dict({})
        assert params.school_id is None
        assert params.visible_only is True  # Default


class TestVenueFilterParams:
    """Tests for VenueFilterParams."""

    def test_default_values(self):
        """Test default filter values."""
        params = VenueFilterParams()
        assert params.venue_type is None
        assert params.is_enabled is None
        assert params.keyword is None

    def test_has_filters(self):
        """Test has_filters method."""
        params = VenueFilterParams()
        assert params.has_filters() is False

        params = VenueFilterParams(venue_type="conference")
        assert params.has_filters() is True

        params = VenueFilterParams(is_enabled=True)
        assert params.has_filters() is True

    def test_from_dict(self):
        """Test creating from dictionary."""
        params = VenueFilterParams.from_dict(
            {
                "venue_type": "journal",
                "is_enabled": True,
            }
        )

        assert params.venue_type == "journal"
        assert params.is_enabled is True


class TestCollectTaskFilterParams:
    """Tests for CollectTaskFilterParams."""

    def test_default_values(self):
        """Test default filter values."""
        params = CollectTaskFilterParams()
        assert params.status is None
        assert params.tech_domain_id is None

    def test_has_filters(self):
        """Test has_filters method."""
        params = CollectTaskFilterParams()
        assert params.has_filters() is False

        params = CollectTaskFilterParams(status="pending")
        assert params.has_filters() is True

        params = CollectTaskFilterParams(tech_domain_id=1)
        assert params.has_filters() is True

    def test_from_dict(self):
        """Test creating from dictionary."""
        params = CollectTaskFilterParams.from_dict(
            {
                "status": "running",
                "tech_domain_id": 2,
            }
        )

        assert params.status == "running"
        assert params.tech_domain_id == 2
