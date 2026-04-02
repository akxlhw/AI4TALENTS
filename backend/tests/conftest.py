"""
Test configuration and fixtures for Academic Talent System MVP v1.1.
学术人才子系统测试配置

Features:
- In-memory SQLite for fast test execution
- Async session support
- Test data factories
- Common test utilities
"""
import asyncio
import os

# Disable rate limiting for tests - must be set before any app imports
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["ENVIRONMENT"] = "test"

import pytest
from typing import AsyncGenerator
from datetime import datetime

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import select

# Clear settings cache and import fresh
from app.core import config
config.get_settings.cache_clear()
from app.core.config import settings

from app.main import app
from app.core.database import Base, get_async_session


# Test database URL (in-memory SQLite for testing)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


# ============ Event Loop ============

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============ Database Fixtures ============

@pytest.fixture(scope="function")
async def test_engine():
    """Create test database engine with all tables."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,  # Set to True for SQL debugging
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="function")
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session_maker = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session


# ============ HTTP Client Fixtures ============

@pytest.fixture(scope="function")
async def client(test_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client with database session override."""

    async def override_get_session():
        yield test_session

    app.dependency_overrides[get_async_session] = override_get_session

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


# ============ Test Data Fixtures ============

@pytest.fixture
async def sample_tech_element(test_session: AsyncSession):
    """Create sample tech element for testing."""
    from app.models.tech_element import TechElement, TechDirection

    element = TechElement(
        element_code="TEST",
        element_name="测试技术要素",
        element_name_en="Test Tech Element",
        is_enabled=True,
    )
    test_session.add(element)
    await test_session.flush()

    direction = TechDirection(
        tech_element_id=element.tech_element_id,
        direction_code="TEST-DIR",
        direction_name="测试方向",
        is_enabled=True,
    )
    test_session.add(direction)
    await test_session.commit()

    return {"element": element, "direction": direction}


@pytest.fixture
async def sample_venue(test_session: AsyncSession):
    """Create sample venue for testing."""
    from app.models.venue import Venue

    venue = Venue(
        venue_code="TEST-VENUE",
        venue_name="Test Conference",
        venue_type="conference",
        openalex_source_id="S-TEST",
        is_enabled=True,
    )
    test_session.add(venue)
    await test_session.commit()
    return venue


@pytest.fixture
async def sample_talent(test_session: AsyncSession):
    """Create sample talent for testing."""
    from app.models.talent import Talent
    from app.models.school import School
    from app.models.enums import RoleType, VisibilityStatus

    school = School(
        school_name="Test University",
        country_code="US",
        country_name="美国",
        is_visible=True,
    )
    test_session.add(school)
    await test_session.flush()

    talent = Talent(
        name="Test Author",
        name_en="Test Author",
        school_id=school.school_id,
        role_type=RoleType.PROFESSOR.value,
        works_count=25,
        cited_by_count=500,
        h_index=10,
        visibility_status=VisibilityStatus.ACTIVE.value,
        is_visible=True,
    )
    test_session.add(talent)
    await test_session.commit()

    return {"talent": talent, "school": school}


# ============ Auth Fixtures ============

@pytest.fixture
def mock_admin_user():
    """Mock admin user for authenticated endpoints."""
    return {
        "user_id": 1,
        "username": "admin",
        "role": "admin",
    }


@pytest.fixture
def mock_normal_user():
    """Mock normal user for authenticated endpoints."""
    return {
        "user_id": 2,
        "username": "user",
        "role": "user",
    }


# ============ Utility Fixtures ============

@pytest.fixture
def assert_response_ok():
    """Helper to assert response is successful."""
    def _assert(response, expected_status: int = 200):
        assert response.status_code == expected_status, \
            f"Expected {expected_status}, got {response.status_code}: {response.text}"
    return _assert


@pytest.fixture
def count_records(test_session: AsyncSession):
    """Helper to count records in a table."""
    async def _count(model_class) -> int:
        from sqlalchemy import func
        result = await test_session.execute(
            select(func.count()).select_from(model_class)
        )
        return result.scalar() or 0
    return _count


# ============ Collection Test Fixtures ============

@pytest.fixture
async def full_setup(test_session: AsyncSession):
    """
    Create full test setup for collection tests.

    Includes:
    - Tech element with default direction
    - Venue
    - Venue-Tech binding
    """
    from app.models.tech_element import TechElement, TechDirection
    from app.models.venue import Venue, VenueTechBinding

    # Create tech element
    tech_element = TechElement(
        element_code="AI",
        element_name="人工智能",
        element_name_en="Artificial Intelligence",
        is_enabled=True,
    )
    test_session.add(tech_element)
    await test_session.flush()

    # Create tech direction
    tech_direction = TechDirection(
        tech_element_id=tech_element.tech_element_id,
        direction_code="AI-ML",
        direction_name="机器学习",
        is_enabled=True,
    )
    test_session.add(tech_direction)
    await test_session.flush()

    # Create venue
    venue = Venue(
        venue_code="NEURIPS",
        venue_name="NeurIPS",
        venue_type="conference",
        openalex_source_id="S12345",
        is_enabled=True,
    )
    test_session.add(venue)
    await test_session.flush()

    # Create binding
    binding = VenueTechBinding(
        venue_id=venue.venue_id,
        tech_element_id=tech_element.tech_element_id,
        is_enabled=True,
    )
    test_session.add(binding)
    await test_session.commit()

    return {
        "tech_element": tech_element,
        "tech_direction": tech_direction,
        "venue": venue,
        "binding": binding,
    }
