"""
Fixtures for open source talent tests.
"""

import pytest
from httpx import AsyncClient

from app.core.auth import create_access_token, hash_password
from app.models.enums import UserRoleType
from app.models.iam import UserAccount
from app.domains.open_source.models.open_source import (
    OSDeveloper,
    OSFavourite,
    OSRepoConfig,
    OSRepository,
    OSTalentPool,
)


@pytest.fixture
async def os_test_user(test_session):
    """Create a test user for open source tests."""
    user = UserAccount(
        username="os_test_user",
        email="os_test@example.com",
        password_hash=hash_password("testpassword123"),
        role_type=UserRoleType.USER.value,
        is_active=True,
        display_name="OS Test User",
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


@pytest.fixture
async def os_test_admin(test_session):
    """Create a test admin for open source tests."""
    admin = UserAccount(
        username="os_test_admin",
        email="os_admin@example.com",
        password_hash=hash_password("adminpassword123"),
        role_type=UserRoleType.ADMIN.value,
        is_active=True,
        display_name="OS Test Admin",
    )
    test_session.add(admin)
    await test_session.commit()
    await test_session.refresh(admin)
    return admin


@pytest.fixture
def os_user_token(os_test_user):
    """Generate auth token for test user."""
    return create_access_token(
        user_id=os_test_user.user_id,
        username=os_test_user.username,
        role=os_test_user.role_type,
    )


@pytest.fixture
def os_admin_token(os_test_admin):
    """Generate auth token for test admin."""
    return create_access_token(
        user_id=os_test_admin.user_id,
        username=os_test_admin.username,
        role=os_test_admin.role_type,
    )


@pytest.fixture
async def sample_os_repo_config(test_session):
    """Create sample repo config."""
    config = OSRepoConfig(
        repo_full_name="test-org/test-repo",
        display_name="Test Repo",
        description="A test repository",
        tech_element="ai",
        language="Python",
        stars_count=1000,
        is_active=True,
        collect_enabled=True,
    )
    test_session.add(config)
    await test_session.commit()
    await test_session.refresh(config)
    return config


@pytest.fixture
async def sample_os_developer(test_session):
    """Create sample open source developer."""
    dev = OSDeveloper(
        github_login="testdeveloper",
        github_id=12345,
        name="Test Developer",
        bio="A passionate open source contributor",
        location="Beijing",
        company="Test Corp",
        blog_url="https://test.dev",
        email="test@example.com",
        avatar_url="https://avatars.githubusercontent.com/u/12345",
        followers_count=500,
        following_count=100,
        public_repos_count=50,
        total_stars_received=15000,
        total_forks_received=3000,
        primary_languages=["Python", "Go", "Rust"],
        tech_tags=["ai", "systems"],
        is_visible=True,
    )
    test_session.add(dev)
    await test_session.commit()
    await test_session.refresh(dev)
    return dev


@pytest.fixture
async def sample_os_repositories(test_session, sample_os_developer):
    """Create sample repositories for developer."""
    repos = [
        OSRepository(
            developer_id=sample_os_developer.developer_id,
            github_repo_id=111,
            full_name="testdeveloper/awesome-project",
            name="awesome-project",
            language="Python",
            stars_count=8500,
            forks_count=1200,
            topics=["machine-learning", "python"],
            is_fork=False,
        ),
        OSRepository(
            developer_id=sample_os_developer.developer_id,
            github_repo_id=222,
            full_name="testdeveloper/go-microservice",
            name="go-microservice",
            language="Go",
            stars_count=3200,
            forks_count=400,
            topics=["microservices", "go"],
            is_fork=False,
        ),
    ]
    for repo in repos:
        test_session.add(repo)
    await test_session.commit()
    return repos


@pytest.fixture
async def sample_os_favorite(test_session, os_test_user, sample_os_developer):
    """Create sample favorite."""
    fav = OSFavourite(
        user_id=os_test_user.user_id,
        developer_id=sample_os_developer.developer_id,
        notes="Great candidate",
        followup_status="contacted",
        is_active=True,
    )
    test_session.add(fav)
    await test_session.commit()
    return fav


@pytest.fixture
async def sample_os_talent_pool(test_session, os_test_user):
    """Create sample talent pool."""
    pool = OSTalentPool(
        owner_user_id=os_test_user.user_id,
        pool_name="AI Backend Pool",
        pool_type="custom",
        scope_desc="Backend engineers with AI experience",
        pool_status="active",
    )
    test_session.add(pool)
    await test_session.commit()
    await test_session.refresh(pool)
    return pool


@pytest.fixture
async def auth_client(client: AsyncClient, os_user_token):
    """Create authenticated client for normal user."""
    client.headers["Authorization"] = f"Bearer {os_user_token}"
    return client


@pytest.fixture
async def admin_client(client: AsyncClient, os_admin_token):
    """Create authenticated client for admin user."""
    client.headers["Authorization"] = f"Bearer {os_admin_token}"
    return client
