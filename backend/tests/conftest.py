"""
Test configuration and fixtures for Academic Talent System.
学术人才子系统测试配置

Features:
- PostgreSQL with per-test TRUNCATE for isolation (session-scoped table creation)
- Async session support
- Test data factories
- Common test utilities
"""

import os

# Disable rate limiting for tests - must be set before any app imports
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["ENVIRONMENT"] = "test"

# Test database URL (PostgreSQL for testing - MUST be a separate database)
# IMPORTANT: Never use production database for tests! Tests will DROP ALL TABLES after each run.
# Create test database with: CREATE DATABASE talent_db_test OWNER talent_user;
TEST_DATABASE_URL = "postgresql+asyncpg://talent_user:ai4recruit@localhost:5432/talent_db_test"
TEST_DATABASE_SYNC_URL = "postgresql://talent_user:ai4recruit@localhost:5432/talent_db_test"

# Override database URLs so ALL sessions (including AuditService's independent session)
# point to the test database, not the production database
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["DATABASE_SYNC_URL"] = TEST_DATABASE_SYNC_URL

# Module-level flag: set by test_engine fixture after checking pgvector availability.
# Tests that require pgvector should be decorated with @pytest.mark.requires_pgvector.
PGVECTOR_AVAILABLE = False

from collections.abc import AsyncGenerator  # noqa: E402

import httpx  # noqa: E402
import pytest  # noqa: E402
from httpx import AsyncClient  # noqa: E402
from sqlalchemy import select, text  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool  # noqa: E402

# Clear settings cache and import fresh
from app.core import config  # noqa: E402

config.get_settings.cache_clear()

# Import all models to ensure they are registered with Base.metadata for create_all
import app.model_registry  # noqa: E402, F401
from app.core.database import Base, get_async_session  # noqa: E402
from app.main import app as _fastapi_app  # noqa: E402

# Restore app variable after import app.model_registry rebinds it
app = _fastapi_app


# Historical failures tracked in docs/audit/v2.2.0-known-test-failures.md
# NOTE: All historical failures were fixed in v2.2.0 release cleanup.
_HISTORICALLY_FAILING_TESTS: set[str] = set()


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "requires_pgvector: mark test as requiring pgvector extension in the test database",
    )


def pytest_collection_modifyitems(config, items):
    """Mark historically failing tests as xfail so they don't block CI."""
    for item in items:
        if item.nodeid in _HISTORICALLY_FAILING_TESTS:
            item.add_marker(
                pytest.mark.xfail(
                    reason="Historical failure tracked in docs/audit/v2.2.0-known-test-failures.md",
                    strict=False,
                )
            )


@pytest.fixture(autouse=True)
def require_pgvector(request):
    """Automatically skip tests marked with @pytest.mark.requires_pgvector when
    the pgvector extension is not available in the test database."""
    marker = request.node.get_closest_marker("requires_pgvector")
    if not marker:
        return
    # Dynamically check pgvector availability (in case test_engine hasn't run yet)
    import asyncio

    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    async def _check():
        engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
        try:
            async with engine.begin() as conn:
                result = await conn.execute(
                    text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
                )
                return result.fetchone() is not None
        except Exception:
            return False
        finally:
            await engine.dispose()

    available = asyncio.run(_check())
    if not available:
        pytest.skip("pgvector extension not available in test database")


# ============ Database Fixtures ============

# Module-level flag: ensures tables are created only once per test run.
# Between tests, TRUNCATE is used for fast cleanup while preserving schema.
_TABLES_INITIALIZED = False


@pytest.fixture(scope="function")
async def test_engine():
    """Create test database engine.

    On first invocation: wipes schema, creates extensions and all tables.
    On subsequent invocations: TRUNCATEs all tables for fast isolation.
    """
    global _TABLES_INITIALIZED, PGVECTOR_AVAILABLE

    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )

    if not _TABLES_INITIALIZED:
        # First test run: full schema setup
        # Drop all tables (not the entire schema) to preserve extensions like pgvector
        async with engine.begin() as conn:
            result = await conn.execute(
                text(
                    """
                SELECT tablename FROM pg_tables
                WHERE schemaname = 'public'
                AND tablename NOT LIKE 'pg_%'
                AND tablename NOT LIKE 'sql_%'
            """
                )
            )
            tables = [row[0] for row in result.fetchall()]
            if tables:
                await conn.execute(
                    text(
                        f"""
                    DROP TABLE IF EXISTS {','.join(tables)} CASCADE
                """
                    )
                )

        # Ensure pgvector extension exists
        _pgvector_create_error = None
        try:
            async with engine.begin() as conn:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        except Exception as e:
            _pgvector_create_error = str(e)

        # Check pgvector availability
        try:
            async with engine.begin() as conn:
                result = await conn.execute(
                    text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
                )
                PGVECTOR_AVAILABLE = result.fetchone() is not None
        except Exception:
            PGVECTOR_AVAILABLE = False

        if not PGVECTOR_AVAILABLE and _pgvector_create_error:
            import warnings

            warnings.warn(
                f"pgvector extension not available in test database: {_pgvector_create_error[:200]}. "
                f"Tests marked @pytest.mark.requires_pgvector will be skipped. "
                f"To enable them, run as superuser: CREATE EXTENSION IF NOT EXISTS vector;",
                RuntimeWarning,
                stacklevel=2,
            )

        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Fix embedding column type: model defines it as String, but migration uses vector(1536)
        if PGVECTOR_AVAILABLE:
            try:
                async with engine.begin() as conn:
                    await conn.execute(
                        text(
                            """
                        ALTER TABLE core_talent_embedding
                        ALTER COLUMN embedding TYPE vector(1536)
                        USING embedding::vector(1536)
                    """
                        )
                    )
            except Exception:
                pass  # Column may already be the correct type

        _TABLES_INITIALIZED = True
    else:
        # Fast path: TRUNCATE all tables to maintain isolation
        async with engine.begin() as conn:
            result = await conn.execute(
                text(
                    """
                SELECT tablename FROM pg_tables
                WHERE schemaname = 'public'
                AND tablename NOT LIKE 'pg_%'
                AND tablename NOT LIKE 'sql_%'
                ORDER BY tablename
            """
                )
            )
            tables = [row[0] for row in result.fetchall()]

            if tables:
                await conn.execute(
                    text(
                        f"""
                    TRUNCATE TABLE {','.join(tables)} RESTART IDENTITY CASCADE
                """
                    )
                )

    # Dispose the application engine's connection pool
    from app.core.database import async_engine as app_engine

    await app_engine.dispose()

    yield engine

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

    transport = httpx.ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


# ============ Test Data Fixtures ============


@pytest.fixture
async def sample_tech_domain(test_session: AsyncSession):
    """Create sample tech domain for testing."""
    from app.domains.academic.models.tech_domain import TechDirection, TechDomain

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
    from app.domains.academic.models.venue import Venue

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
    from app.domains.academic.models.school import School
    from app.domains.academic.models.talent import Talent
    from app.domains.shared.models.enums import RoleType, VisibilityStatus

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
    from app.core.auth import hash_password
    from app.domains.shared.models.iam import UserAccount

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
        assert (
            response.status_code == expected_status
        ), f"Expected {expected_status}, got {response.status_code}: {response.text}"

    return _assert


@pytest.fixture
def count_records(test_session: AsyncSession):
    """Helper to count records in a table."""

    async def _count(model_class) -> int:
        from sqlalchemy import func

        result = await test_session.execute(select(func.count()).select_from(model_class))
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
    from app.domains.academic.models.tech_domain import TechDirection, TechDomain
    from app.domains.academic.models.venue import Venue, VenueTechBinding

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
