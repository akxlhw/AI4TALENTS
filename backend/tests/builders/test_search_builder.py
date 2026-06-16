"""
Tests for SearchBuilder.
Covers: search document building, search text generation.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.academic.builders.search_builder import SearchBuilder
from app.domains.academic.models.school import School
from app.domains.academic.models.search import SearchTalentDocument
from app.domains.academic.models.talent import Talent
from app.domains.shared.models.enums import RoleType, VisibilityStatus


class TestSearchBuilder:
    """Tests for SearchBuilder."""

    @pytest.fixture
    async def builder(self, test_session: AsyncSession):
        """Create SearchBuilder instance."""
        return SearchBuilder(session=test_session, batch_id=1)

    @pytest.fixture
    async def sample_talent_and_school(self, test_session: AsyncSession):
        """Create sample talent and school for search builder tests."""
        school = School(
            school_name="Test University",
            school_alias="TU",
            country_code="US",
            is_visible=True,
        )
        test_session.add(school)
        await test_session.flush()

        talent = Talent(
            name="John Doe",
            name_en="John Doe",
            school_id=school.school_id,
            role_type=RoleType.PROFESSOR.value,
            works_count=25,
            cited_by_count=500,
            h_index=10,
            visibility_status=VisibilityStatus.ACTIVE.value,
            is_visible=True,
            orcid="0000-0001-2345-6789",
            topic_tags=["machine learning", "deep learning"],
            openalex_topics=["Artificial Intelligence", "Computer Vision"],
            current_title="Professor of CS",
        )
        test_session.add(talent)
        await test_session.commit()
        return talent, school

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_build_search_text(self, builder: SearchBuilder, sample_talent_and_school):
        """Test _build_search_text combines talent and school data."""
        talent, school = sample_talent_and_school
        text = builder._build_search_text(talent, school)

        assert "John Doe" in text
        assert "Test University" in text
        assert "TU" in text
        assert "0000-0001-2345-6789" in text
        assert "machine learning" in text
        assert "Artificial Intelligence" in text
        assert "Professor of CS" in text

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_build_search_text_no_school(
        self, builder: SearchBuilder, sample_talent_and_school
    ):
        """Test _build_search_text with no school."""
        talent, _ = sample_talent_and_school
        text = builder._build_search_text(talent, None)

        assert "John Doe" in text
        assert "Test University" not in text

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_build_search_text_alias_same_as_name(self, builder: SearchBuilder, test_session):
        """Test _build_search_text does not duplicate alias when same as name."""
        school = School(school_name="MIT", school_alias="MIT", is_visible=True)
        test_session.add(school)
        await test_session.flush()

        talent = Talent(
            name="Alice",
            school_id=school.school_id,
            role_type=RoleType.PROFESSOR.value,
            is_visible=True,
        )
        test_session.add(talent)
        await test_session.commit()

        text = builder._build_search_text(talent, school)
        # "MIT" should appear only once since alias == name
        assert text.count("MIT") == 1

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_build_creates_documents(
        self, builder: SearchBuilder, sample_talent_and_school, test_session: AsyncSession
    ):
        """Test build() creates SearchTalentDocument records."""
        result = await builder.build()

        assert result.success is True
        assert result.records_processed >= 1
        assert result.records_created >= 1
        assert result.records_failed == 0

        # Verify document exists in DB
        from sqlalchemy import select

        docs_result = await test_session.execute(select(SearchTalentDocument))
        docs = docs_result.scalars().all()
        assert len(docs) >= 1
        doc = docs[0]
        assert doc.talent_id is not None
        assert doc.search_text is not None
        assert doc.is_active is True

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_build_updates_existing_document(
        self, builder: SearchBuilder, sample_talent_and_school, test_session
    ):
        """Test build() updates existing document instead of creating duplicate."""
        talent, school = sample_talent_and_school

        # Pre-create a document
        existing = SearchTalentDocument(
            talent_id=talent.talent_id,
            school_id=school.school_id,
            name="Old Name",
            search_text="old text",
            role_type=RoleType.PROFESSOR.value,
            batch_id=0,
            is_active=True,
            created_at=__import__("datetime").datetime.now(),
            updated_at=__import__("datetime").datetime.now(),
        )
        test_session.add(existing)
        await test_session.commit()

        result = await builder.build()

        assert result.success is True
        # Should update, not create new
        from sqlalchemy import select

        docs_result = await test_session.execute(select(SearchTalentDocument))
        docs = list(docs_result.scalars().all())
        assert len(docs) == 1
        assert docs[0].name == "John Doe"
        assert docs[0].batch_id == 1

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_build_no_visible_talents(self, builder: SearchBuilder, test_session):
        """Test build() with no visible talents returns empty result."""
        result = await builder.build()

        assert result.success is True
        assert result.records_processed == 0
        assert result.records_created == 0
