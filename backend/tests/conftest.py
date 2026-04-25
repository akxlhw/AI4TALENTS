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


# Test database URL (PostgreSQL for testing - MUST be a separate database)
# IMPORTANT: Never use production database for tests! Tests will DROP ALL TABLES after each run.
# Create test database with: CREATE DATABASE talent_db_test OWNER talent_user;
TEST_DATABASE_URL = "postgresql+asyncpg://talent_user:ai4recruit@localhost:5432/talent_db_test"


def pytest_configure(config):
    """Skip tests that require PostgreSQL-specific features if tables don't exist."""
    pass


# ============ Database Fixtures ============

# Import all models to ensure they are registered with Base.metadata
from app.models import school, talent, raw_data, standardized, venue, tech_domain, sync, enums


@pytest.fixture(scope="function")
async def test_engine():
    """Create test database engine with all tables."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,  # Set to True for SQL debugging
        pool_pre_ping=True,  # Verify connections before use
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables after test
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
async def sample_tech_domain(test_session: AsyncSession):
    """Create sample tech domain for testing."""
    from app.models.tech_domain import TechDomain, TechDirection

    domain = TechDomain(
        domain_code="TEST",
        domain_name="测试技术领域",
        domain_name_en="Test Tech Domain",
        is_enabled=True,
    )
    test_session.add(domain)
    await test_session.flush()

    direction = TechDirection(
        tech_domain_id=domain.tech_domain_id,
        direction_code="TEST-DIR",
        direction_name="测试方向",
        is_enabled=True,
    )
    test_session.add(direction)
    await test_session.commit()

    return {"domain": domain, "direction": direction}


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
        # 添加研究主题，支持推荐和搜索测试
        openalex_topics=["machine learning", "deep learning"],
        topic_tags=["人工智能", "机器学习"],
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


@pytest.fixture
async def test_user(test_session: AsyncSession):
    """Create a test user in database for JD match tests."""
    from app.models.iam import UserAccount
    from app.core.auth import hash_password

    # Check if user already exists
    result = await test_session.execute(
        select(UserAccount).where(UserAccount.username == "test_jd_matcher")
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    user = UserAccount(
        username="test_jd_matcher",
        email="test_jd@example.com",
        password_hash=hash_password("test123"),
        role_type="admin",
        is_active=True,
    )
    test_session.add(user)
    await test_session.flush()
    await test_session.refresh(user)
    return user


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
    - Tech domain with default direction
    - Venue
    - Venue-Tech binding
    """
    from app.models.tech_domain import TechDomain, TechDirection
    from app.models.venue import Venue, VenueTechBinding

    # Create tech domain
    tech_domain = TechDomain(
        domain_code="AI",
        domain_name="人工智能",
        domain_name_en="Artificial Intelligence",
        is_enabled=True,
    )
    test_session.add(tech_domain)
    await test_session.flush()

    # Create tech direction
    tech_direction = TechDirection(
        tech_domain_id=tech_domain.tech_domain_id,
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
        tech_domain_id=tech_domain.tech_domain_id,
        is_enabled=True,
    )
    test_session.add(binding)
    await test_session.commit()

    return {
        "tech_domain": tech_domain,
        "tech_direction": tech_direction,
        "venue": venue,
        "binding": binding,
    }
