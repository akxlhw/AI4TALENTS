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
from app.models.tech_element import TechDirection, TechElement, TalentTechTag


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


class TestTechElementCursorPagination:
    """Tests for cursor pagination on tech element talent lists."""

    @pytest.fixture
    async def setup_tech_element_data(self, test_session: AsyncSession):
        """Create test data for tech element pagination."""
        # Create tech element
        element = TechElement(
            element_code="AI",
            element_name="人工智能",
            is_enabled=True,
        )
        test_session.add(element)
        await test_session.flush()

        # Create tech direction
        direction = TechDirection(
            tech_element_id=element.tech_element_id,
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
                tech_element_id=element.tech_element_id,
                tech_direction_id=direction.tech_direction_id,
                is_enabled=True,
            )
            test_session.add(tag)

        await test_session.commit()

        return {
            "element": element,
            "direction": direction,
            "school": school,
            "talents": talents,
        }

    @pytest.mark.asyncio
    async def test_tech_element_talents_cursor_pagination(
        self, test_session: AsyncSession, setup_tech_element_data
    ):
        """Test cursor pagination on tech element talent list."""
        from app.repositories.tech_element_repository import TechElementRepository

        repo = TechElementRepository(test_session)
        data = setup_tech_element_data

        # Get first page
        talents, next_cursor = await repo.get_talent_list_by_cursor(
            element_id=data["element"].tech_element_id,
            page_size=10,
        )

        assert len(talents) == 10
        assert next_cursor is not None

        # Get second page
        talents2, next_cursor2 = await repo.get_talent_list_by_cursor(
            element_id=data["element"].tech_element_id,
            cursor=next_cursor,
            page_size=10,
        )

        assert len(talents2) == 10
        assert next_cursor2 is None  # Last page
