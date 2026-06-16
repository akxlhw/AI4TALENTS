"""
Tests for SchoolNormalizer.
Covers: name normalization, country code normalization, find_matching_school, create_std_school.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.academic.models.raw_data import RawInstitution
from app.domains.academic.models.standardized import SchoolNameAlias, StdSchool
from app.domains.academic.services.normalizers.school import SchoolNormalizer


class TestSchoolNormalizerUnit:
    """Unit tests for SchoolNormalizer methods that don't need DB."""

    @pytest.fixture
    def normalizer(self, test_session: AsyncSession):
        """Create SchoolNormalizer instance (session not used for unit tests)."""
        return SchoolNormalizer(test_session)

    def test_normalize_school_name_basic(self, normalizer: SchoolNormalizer):
        """Test basic school name normalization."""
        assert normalizer.normalize_school_name("MIT") == "mit"
        assert normalizer.normalize_school_name("Stanford University") == "stanford"

    def test_normalize_school_name_removes_suffixes(self, normalizer: SchoolNormalizer):
        """Test removal of common suffixes."""
        assert (
            normalizer.normalize_school_name("California Institute of Technology")
            == "california of technology"
        )
        assert normalizer.normalize_school_name("Boston College") == "boston"

    def test_normalize_school_name_empty(self, normalizer: SchoolNormalizer):
        """Test normalization of empty string."""
        assert normalizer.normalize_school_name("") == ""
        assert normalizer.normalize_school_name("   ") == ""

    def test_normalize_school_name_punctuation(self, normalizer: SchoolNormalizer):
        """Test removal of punctuation."""
        assert normalizer.normalize_school_name("U.C. Berkeley") == "uc berkeley"

    def test_normalize_school_name_fallback(self, normalizer: SchoolNormalizer):
        """Test fallback when suffix removal leaves nothing."""
        assert normalizer.normalize_school_name("University School") == "university school"

    def test_normalize_country_code(self, normalizer: SchoolNormalizer):
        """Test country code normalization."""
        assert normalizer._normalize_country_code("US") == "US"
        assert normalizer._normalize_country_code("tw") == "CN"
        assert normalizer._normalize_country_code(None) is None
        assert normalizer._normalize_country_code("") is None


class TestSchoolNormalizerIntegration:
    """Integration tests for SchoolNormalizer with database."""

    @pytest.fixture
    async def normalizer(self, test_session: AsyncSession):
        """Create SchoolNormalizer instance."""
        return SchoolNormalizer(test_session)

    @pytest.fixture
    async def sample_std_school(self, test_session: AsyncSession):
        """Create a sample standardized school."""
        school = StdSchool(
            openalex_institution_id="I123456789",
            name_normalized="Test University",
            country_code="US",
            confirm_status="auto_identified",
        )
        test_session.add(school)
        await test_session.commit()
        await test_session.refresh(school)
        return school

    @pytest.fixture
    async def sample_raw_institution(self, test_session: AsyncSession):
        """Create a sample raw institution."""
        inst = RawInstitution(
            openalex_institution_id="I123456789",
            raw_json="{}",
            display_name="Test University",
            country_code="US",
            country_name="United States",
            type="education",
        )
        test_session.add(inst)
        await test_session.commit()
        await test_session.refresh(inst)
        return inst

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_find_matching_school_by_openalex_id(
        self, normalizer: SchoolNormalizer, sample_std_school
    ):
        """Test finding school by OpenAlex ID."""
        school, match_type = await normalizer.find_matching_school("I123456789", "Any Name")
        assert school is not None
        assert school.std_school_id == sample_std_school.std_school_id
        assert match_type == "openalex_id"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_find_matching_school_by_name(
        self, normalizer: SchoolNormalizer, sample_std_school
    ):
        """Test finding school by exact name match."""
        school, match_type = await normalizer.find_matching_school(None, "Test University")
        assert school is not None
        assert match_type == "name"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_find_matching_school_by_alias(
        self, normalizer: SchoolNormalizer, sample_std_school, test_session
    ):
        """Test finding school by alias."""
        alias = SchoolNameAlias(
            std_school_id=sample_std_school.std_school_id,
            alias_name="TU",
        )
        test_session.add(alias)
        await test_session.commit()

        school, match_type = await normalizer.find_matching_school(None, "TU")
        assert school is not None
        assert match_type == "alias"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_find_matching_school_by_normalized(
        self, normalizer: SchoolNormalizer, sample_std_school
    ):
        """Test finding school by normalized name match."""
        school, match_type = await normalizer.find_matching_school(None, "Test Univ")
        assert school is not None
        assert match_type == "normalized"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_find_matching_school_not_found(self, normalizer: SchoolNormalizer):
        """Test finding non-existent school."""
        school, match_type = await normalizer.find_matching_school(None, "NonExistent School XYZ")
        assert school is None
        assert match_type == "none"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_create_std_school(
        self, normalizer: SchoolNormalizer, sample_raw_institution, test_session
    ):
        """Test creating StdSchool from RawInstitution."""
        school = await normalizer.create_std_school(sample_raw_institution, task_id=None)

        assert school.std_school_id is not None
        assert school.openalex_institution_id == "I123456789"
        assert school.name_normalized == "Test University"
        assert school.country_code == "US"
        assert school.confirm_status == "auto_identified"
        assert school.source_task_id is None

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_create_std_school_tw_to_cn(self, normalizer: SchoolNormalizer, test_session):
        """Test TW country code is mapped to CN."""
        inst = RawInstitution(
            openalex_institution_id="I999",
            raw_json="{}",
            display_name="Taiwan University",
            country_code="TW",
            country_name="Taiwan",
        )
        test_session.add(inst)
        await test_session.flush()

        school = await normalizer.create_std_school(inst)
        assert school.country_code == "CN"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_normalize_institution_creates_new(
        self, normalizer: SchoolNormalizer, sample_raw_institution, test_session
    ):
        """Test normalize_institution creates new when no match."""
        # Use a raw institution that won't match existing
        inst = RawInstitution(
            openalex_institution_id="I777",
            raw_json="{}",
            display_name="Brand New University",
            country_code="UK",
        )
        test_session.add(inst)
        await test_session.flush()

        school = await normalizer.normalize_institution(inst, task_id=None)
        assert school.std_school_id is not None
        assert school.name_normalized == "Brand New University"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_normalize_institution_updates_existing(
        self, normalizer: SchoolNormalizer, sample_std_school, sample_raw_institution, test_session
    ):
        """Test normalize_institution updates existing matched school."""
        # Modify raw_inst to have same openalex_id
        sample_raw_institution.type = "updated_type"
        await test_session.commit()

        school = await normalizer.normalize_institution(sample_raw_institution, task_id=None)
        assert school.std_school_id == sample_std_school.std_school_id
        assert school.inst_type == "updated_type"
