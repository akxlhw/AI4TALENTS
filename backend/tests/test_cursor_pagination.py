"""
Tests for cursor-based pagination functionality.
"""
import os

os.environ["REDIS_ENABLED"] = "false"

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base, async_engine
from app.models.enums import RoleType, VisibilityStatus
from app.models.school import School
from app.models.talent import Talent
from app.models.tech_domain import TechDirection, TechDomain, TalentTechTag


@pytest.fixture
async def setup_pagination_data(test_session: AsyncSession):
    """Create test data for pagination tests."""
    # Create school
    school = School(
        school_name="Test University",
        country_code="US",
        country_name="美国",
        is_visible=True,
    )
    test_session.add(school)
    await test_session.flush()

    # Create 25 talents with different h_index for sorting
    talents = []
    for i in range(25):
        talent = Talent(
            name=f"Talent {i:02d}",
            name_en=f"Talent {i:02d}",
            school_id=school.school_id,
            role_type=RoleType.PROFESSOR.value,
            h_index=100 - i,  # Descending h_index
            works_count=50 + i,
            cited_by_count=1000 + i * 10,
            visibility_status=VisibilityStatus.ACTIVE.value,
            is_visible=True,
        )
        test_session.add(talent)
        talents.append(talent)

    await test_session.commit()

    return {
        "school": school,
        "talents": talents,
    }


class TestCursorPagination:
    """Tests for cursor-based pagination."""

    @pytest.mark.asyncio
    async def test_get_talents_by_cursor_first_page(
        self, test_session: AsyncSession, setup_pagination_data
    ):
        """Test getting first page with cursor pagination."""
        from app.repositories.talent_repository import TalentRepository

        repo = TalentRepository(test_session)
        talents, next_cursor = await repo.get_list_by_cursor(
            page_size=10,
        )

        assert len(talents) == 10
        assert next_cursor is not None
        # Ordering is by talent_id DESC
        # First page should have highest talent_id (newest first)
        assert talents[0].talent_id > talents[9].talent_id

    @pytest.mark.asyncio
    async def test_get_talents_by_cursor_second_page(
        self, test_session: AsyncSession, setup_pagination_data
    ):
        """Test getting second page with cursor pagination."""
        from app.repositories.talent_repository import TalentRepository

        repo = TalentRepository(test_session)

        # Get first page
        first_page, next_cursor = await repo.get_list_by_cursor(
            page_size=10,
        )
        assert next_cursor is not None

        # Get second page using cursor
        second_page, next_cursor2 = await repo.get_list_by_cursor(
            cursor=next_cursor,
            page_size=10,
        )

        assert len(second_page) == 10
        # Second page should have lower talent_ids than first page
        assert second_page[0].talent_id < first_page[-1].talent_id

    @pytest.mark.asyncio
    async def test_get_talents_by_cursor_last_page(
        self, test_session: AsyncSession, setup_pagination_data
    ):
        """Test getting last page with cursor pagination."""
        from app.repositories.talent_repository import TalentRepository

        repo = TalentRepository(test_session)

        # Get all pages
        all_talents = []
        cursor = None
        page_count = 0

        while True:
            talents, next_cursor = await repo.get_list_by_cursor(
                cursor=cursor,
                page_size=10,
            )
            all_talents.extend(talents)
            cursor = next_cursor
            page_count += 1

            if next_cursor is None:
                break

            if page_count > 5:  # Safety limit
                break

        # Should have all 25 talents
        assert len(all_talents) == 25

    @pytest.mark.asyncio
    async def test_get_talents_by_cursor_with_filters(
        self, test_session: AsyncSession, setup_pagination_data
    ):
        """Test cursor pagination with role type filter."""
        from app.repositories.talent_repository import TalentRepository

        repo = TalentRepository(test_session)

        # Update some talents to student role
        data = setup_pagination_data
        for i in range(5):
            data["talents"][i].role_type = RoleType.STUDENT.value
        await test_session.commit()

        # Filter by professor
        talents, next_cursor = await repo.get_list_by_cursor(
            role_type="professor",
            page_size=10,
        )

        # Should only get professors (20 of them)
        assert len(talents) == 10
        for t in talents:
            assert t.role_type == "professor"

    @pytest.mark.asyncio
    async def test_get_talents_by_cursor_with_school_filter(
        self, test_session: AsyncSession, setup_pagination_data
    ):
        """Test cursor pagination with school filter."""
        from app.repositories.talent_repository import TalentRepository

        repo = TalentRepository(test_session)
        data = setup_pagination_data

        talents, next_cursor = await repo.get_list_by_cursor(
            school_id=data["school"].school_id,
            page_size=10,
        )

        assert len(talents) == 10
        for t in talents:
            assert t.school_id == data["school"].school_id


class TestTechDomainCursorPagination:
    """Tests for cursor pagination on tech domain talent lists."""

    @pytest.fixture
    async def setup_tech_domain_data(self, test_session: AsyncSession):
        """Create test data for tech domain pagination."""
        # Create tech domain
        domain = TechDomain(
            domain_code="AI",
            domain_name="人工智能",
            is_enabled=True,
        )
        test_session.add(domain)
        await test_session.flush()

        # Create tech direction
        direction = TechDirection(
            tech_domain_id=domain.tech_domain_id,
            direction_code="AI-ML",
            direction_name="机器学习",
            is_enabled=True,
        )
        test_session.add(direction)
        await test_session.flush()

        # Create school
        school = School(
            school_name="Tech University",
            country_code="CN",
            country_name="中国",
            is_visible=True,
        )
        test_session.add(school)
        await test_session.flush()

        # Create talents with tech tags
        talents = []
        for i in range(20):
            talent = Talent(
                name=f"AI Talent {i:02d}",
                school_id=school.school_id,
                role_type=RoleType.PROFESSOR.value,
                h_index=50 - i,
                works_count=30 + i,
                visibility_status=VisibilityStatus.ACTIVE.value,
                is_visible=True,
            )
            test_session.add(talent)
            talents.append(talent)

        await test_session.flush()

        # Create tech tags
        for talent in talents:
            tag = TalentTechTag(
                talent_id=talent.talent_id,
                tech_domain_id=domain.tech_domain_id,
                tech_direction_id=direction.tech_direction_id,
                is_enabled=True,
            )
            test_session.add(tag)

        await test_session.commit()

        return {
            "domain": domain,
            "direction": direction,
            "school": school,
            "talents": talents,
        }

    @pytest.mark.asyncio
    async def test_tech_domain_talents_cursor_pagination(
        self, test_session: AsyncSession, setup_tech_domain_data
    ):
        """Test cursor pagination on tech domain talent list."""
        from app.repositories.tech_domain_repository import TechDomainRepository

        repo = TechDomainRepository(test_session)
        data = setup_tech_domain_data

        # Get first page
        talents, next_cursor = await repo.get_talent_list_by_cursor(
            domain_id=data["domain"].tech_domain_id,
            page_size=10,
        )

        assert len(talents) == 10
        assert next_cursor is not None

        # Get second page
        talents2, next_cursor2 = await repo.get_talent_list_by_cursor(
            domain_id=data["domain"].tech_domain_id,
            cursor=next_cursor,
            page_size=10,
        )

        assert len(talents2) == 10
        assert next_cursor2 is None  # Last page


class TestCursorPaginationEdgeCases:
    """Tests for cursor pagination edge cases."""

    @pytest.fixture
    async def setup_empty_data(self, test_session: AsyncSession):
        """Create minimal test data for edge case tests."""
        school = School(
            school_name="Empty University",
            country_code="US",
            country_name="美国",
            is_visible=True,
        )
        test_session.add(school)
        await test_session.commit()
        return {"school": school}

    @pytest.mark.asyncio
    async def test_empty_result_set(
        self, test_session: AsyncSession, setup_empty_data
    ):
        """Test cursor pagination with no results."""
        from app.repositories.talent_repository import TalentRepository

        repo = TalentRepository(test_session)

        talents, next_cursor = await repo.get_list_by_cursor(
            school_id=99999,  # Non-existent school
            page_size=10,
        )

        assert len(talents) == 0
        assert next_cursor is None

    @pytest.mark.asyncio
    async def test_cursor_exhausted_returns_empty(
        self, test_session: AsyncSession, setup_pagination_data
    ):
        """Test cursor pagination when cursor points to first item (no more before it)."""
        from app.repositories.talent_repository import TalentRepository

        repo = TalentRepository(test_session)
        data = setup_pagination_data

        # Get first page to find the smallest talent_id
        first_page, _ = await repo.get_list_by_cursor(page_size=100)

        if first_page:
            # Use the smallest ID as cursor - should return empty (no IDs smaller)
            min_id = min(t.talent_id for t in first_page)
            talents, next_cursor = await repo.get_list_by_cursor(
                cursor=min_id,
                page_size=10,
            )

            # Should return empty since no talent_id < min_id
            assert len(talents) == 0
            assert next_cursor is None

    @pytest.mark.asyncio
    async def test_pagination_with_country_filter(
        self, test_session: AsyncSession, setup_pagination_data
    ):
        """Test cursor pagination with country code filter."""
        from app.repositories.talent_repository import TalentRepository

        repo = TalentRepository(test_session)

        talents, next_cursor = await repo.get_list_by_cursor(
            country_code="US",
            page_size=10,
        )

        # All talents are from US school in setup_pagination_data
        assert len(talents) <= 10
        for t in talents:
            assert t.school is not None

    @pytest.mark.asyncio
    async def test_pagination_with_keyword(
        self, test_session: AsyncSession, setup_pagination_data
    ):
        """Test cursor pagination with keyword search."""
        from app.repositories.talent_repository import TalentRepository

        repo = TalentRepository(test_session)

        talents, next_cursor = await repo.get_list_by_cursor(
            keyword="Talent",
            page_size=10,
        )

        assert len(talents) <= 10
        for t in talents:
            # Name should contain "Talent"
            assert "Talent" in t.name or "Talent" in (t.name_en or "")

    @pytest.mark.asyncio
    async def test_pagination_with_min_works_filter(
        self, test_session: AsyncSession, setup_pagination_data
    ):
        """Test cursor pagination with minimum works filter."""
        from app.repositories.talent_repository import TalentRepository

        repo = TalentRepository(test_session)

        talents, next_cursor = await repo.get_list_by_cursor(
            min_works=60,
            page_size=10,
        )

        for t in talents:
            assert t.works_count >= 60

    @pytest.mark.asyncio
    async def test_pagination_with_min_citations_filter(
        self, test_session: AsyncSession, setup_pagination_data
    ):
        """Test cursor pagination with minimum citations filter."""
        from app.repositories.talent_repository import TalentRepository

        repo = TalentRepository(test_session)

        talents, next_cursor = await repo.get_list_by_cursor(
            min_citations=1100,
            page_size=10,
        )

        for t in talents:
            assert t.cited_by_count >= 1100

    @pytest.mark.asyncio
    async def test_single_item_page(
        self, test_session: AsyncSession
    ):
        """Test cursor pagination with page_size=1."""
        from app.repositories.talent_repository import TalentRepository

        # Create a single talent
        school = School(
            school_name="Single School",
            country_code="CN",
            country_name="中国",
            is_visible=True,
        )
        test_session.add(school)
        await test_session.flush()

        talent = Talent(
            name="Single Talent",
            school_id=school.school_id,
            role_type=RoleType.PROFESSOR.value,
            h_index=50,
            visibility_status=VisibilityStatus.ACTIVE.value,
            is_visible=True,
        )
        test_session.add(talent)
        await test_session.commit()

        repo = TalentRepository(test_session)

        talents, next_cursor = await repo.get_list_by_cursor(
            page_size=1,
        )

        assert len(talents) == 1
        assert next_cursor is None  # Only one item

    @pytest.mark.asyncio
    async def test_exactly_page_size_results(
        self, test_session: AsyncSession
    ):
        """Test cursor pagination when results equal page_size."""
        from app.repositories.talent_repository import TalentRepository

        # Create exactly 10 talents
        school = School(
            school_name="Exact School",
            country_code="GB",
            country_name="英国",
            is_visible=True,
        )
        test_session.add(school)
        await test_session.flush()

        for i in range(10):
            talent = Talent(
                name=f"Exact Talent {i:02d}",
                school_id=school.school_id,
                role_type=RoleType.PROFESSOR.value,
                h_index=50 - i,
                visibility_status=VisibilityStatus.ACTIVE.value,
                is_visible=True,
            )
            test_session.add(talent)

        await test_session.commit()

        repo = TalentRepository(test_session)

        talents, next_cursor = await repo.get_list_by_cursor(
            school_id=school.school_id,
            page_size=10,
        )

        assert len(talents) == 10
        # Should have no next cursor since exactly page_size results
        assert next_cursor is None
