"""
Tests for OpenSourceRepository.
Covers: repo config, developer, favourite, talent pool, collect task CRUD.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.open_source.models.open_source import (
    OSCollectTask,
    OSContribution,
    OSDeveloper,
    OSFavourite,
    OSLanguageSkill,
    OSPoolMember,
    OSRepoConfig,
    OSRepository,
    OSTalentPool,
)
from app.domains.open_source.repositories.open_source_repository import OpenSourceRepository


class TestRepoConfigRepository:
    """Tests for repo config CRUD."""

    @pytest.fixture
    async def sample_config(self, test_session: AsyncSession):
        """Create a sample repo config."""
        config = OSRepoConfig(
            repo_full_name="test-org/test-repo",
            tech_element="ai",
            display_name="Test Repo",
            stars_count=1000,
            is_active=True,
            collect_enabled=True,
        )
        test_session.add(config)
        await test_session.commit()
        await test_session.refresh(config)
        return config

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_list_repo_configs(self, test_session: AsyncSession, sample_config):
        """Test listing repo configs."""
        repo = OpenSourceRepository(test_session)
        items, total = await repo.list_repo_configs()
        assert total >= 1
        assert any(i.repo_config_id == sample_config.repo_config_id for i in items)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_list_repo_configs_with_filter(self, test_session: AsyncSession, sample_config):
        """Test listing repo configs with tech_element filter."""
        repo = OpenSourceRepository(test_session)
        items, total = await repo.list_repo_configs(filters={"tech_element": "ai"})
        assert total >= 1
        assert all(i.tech_element == "ai" for i in items)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_repo_config(self, test_session: AsyncSession, sample_config):
        """Test getting repo config by ID."""
        repo = OpenSourceRepository(test_session)
        result = await repo.get_repo_config(sample_config.repo_config_id)
        assert result is not None
        assert result.repo_full_name == "test-org/test-repo"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_repo_config_not_found(self, test_session: AsyncSession):
        """Test getting non-existent repo config."""
        repo = OpenSourceRepository(test_session)
        result = await repo.get_repo_config(99999)
        assert result is None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_repo_config(self, test_session: AsyncSession):
        """Test creating a repo config."""
        repo = OpenSourceRepository(test_session)
        created = await repo.create_repo_config({
            "repo_full_name": "new-org/new-repo",
            "tech_element": "robotics",
            "display_name": "New Repo",
        })
        assert created.repo_config_id is not None
        assert created.repo_full_name == "new-org/new-repo"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_update_repo_config(self, test_session: AsyncSession, sample_config):
        """Test updating a repo config."""
        repo = OpenSourceRepository(test_session)
        updated = await repo.update_repo_config(
            sample_config.repo_config_id, {"display_name": "Updated Name"}
        )
        assert updated is not None
        assert updated.display_name == "Updated Name"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_delete_repo_config(self, test_session: AsyncSession, sample_config):
        """Test deleting a repo config."""
        repo = OpenSourceRepository(test_session)
        deleted = await repo.delete_repo_config(sample_config.repo_config_id)
        assert deleted is True
        assert await repo.get_repo_config(sample_config.repo_config_id) is None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_repo_config_by_full_name(self, test_session: AsyncSession, sample_config):
        """Test getting repo config by full name."""
        repo = OpenSourceRepository(test_session)
        result = await repo.get_repo_config_by_full_name("test-org/test-repo")
        assert result is not None
        assert result.repo_config_id == sample_config.repo_config_id


class TestDeveloperRepository:
    """Tests for developer CRUD and queries."""

    @pytest.fixture
    async def sample_developer(self, test_session: AsyncSession):
        """Create a sample developer."""
        dev = OSDeveloper(
            github_login="testdeveloper",
            name="Test Developer",
            bio="A test bio",
            location="Beijing",
            company="Test Corp",
            total_stars_received=15000,
            primary_languages=["Python", "Go"],
            tech_tags=["ai", "systems"],
            is_visible=True,
        )
        test_session.add(dev)
        await test_session.commit()
        await test_session.refresh(dev)
        return dev

    @pytest.fixture
    async def sample_repos(self, test_session: AsyncSession, sample_developer):
        """Create sample repositories."""
        repos = [
            OSRepository(
                developer_id=sample_developer.developer_id,
                full_name="testdeveloper/awesome-project",
                name="awesome-project",
                language="Python",
                stars_count=8500,
            ),
            OSRepository(
                developer_id=sample_developer.developer_id,
                full_name="testdeveloper/go-microservice",
                name="go-microservice",
                language="Go",
                stars_count=3200,
            ),
        ]
        for r in repos:
            test_session.add(r)
        await test_session.commit()
        return repos

    @pytest.fixture
    async def sample_contributions(self, test_session: AsyncSession, sample_developer, sample_repos):
        """Create sample contributions."""
        contrib = OSContribution(
            developer_id=sample_developer.developer_id,
            repo_id=sample_repos[0].repo_id,
            commits_count=42,
            is_committer=True,
        )
        test_session.add(contrib)
        await test_session.commit()
        return contrib

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_list_developers(self, test_session: AsyncSession, sample_developer):
        """Test listing developers."""
        repo = OpenSourceRepository(test_session)
        items, total = await repo.list_developers()
        assert total >= 1
        assert any(i.developer_id == sample_developer.developer_id for i in items)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_list_developers_with_keyword(self, test_session: AsyncSession, sample_developer):
        """Test listing developers with keyword filter."""
        repo = OpenSourceRepository(test_session)
        items, total = await repo.list_developers(filters={"q": "Test Developer"})
        assert total >= 1
        assert any(i.developer_id == sample_developer.developer_id for i in items)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_developer(self, test_session: AsyncSession, sample_developer):
        """Test getting developer by ID."""
        repo = OpenSourceRepository(test_session)
        result = await repo.get_developer(sample_developer.developer_id)
        assert result is not None
        assert result.github_login == "testdeveloper"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_developer_repositories(self, test_session: AsyncSession, sample_developer, sample_repos):
        """Test getting developer repositories."""
        repo = OpenSourceRepository(test_session)
        results = await repo.get_developer_repositories(sample_developer.developer_id)
        assert len(results) == 2
        assert results[0].stars_count >= results[1].stars_count

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_developer_contributions(self, test_session: AsyncSession, sample_developer, sample_contributions):
        """Test getting developer contributions."""
        repo = OpenSourceRepository(test_session)
        results = await repo.get_developer_contributions(sample_developer.developer_id)
        assert len(results) == 1
        contrib, full_name = results[0]
        assert contrib.commits_count == 42

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_similar_developers(self, test_session: AsyncSession, sample_developer):
        """Test getting similar developers."""
        repo = OpenSourceRepository(test_session)
        results = await repo.get_similar_developers(sample_developer.developer_id, limit=5)
        assert isinstance(results, list)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_developers_by_ids(self, test_session: AsyncSession, sample_developer):
        """Test getting multiple developers by IDs."""
        repo = OpenSourceRepository(test_session)
        results = await repo.get_developers_by_ids([sample_developer.developer_id])
        assert len(results) == 1
        assert results[0].developer_id == sample_developer.developer_id

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_developers_by_ids_empty(self, test_session: AsyncSession):
        """Test get_developers_by_ids with empty list."""
        repo = OpenSourceRepository(test_session)
        results = await repo.get_developers_by_ids([])
        assert results == []


class TestFavouriteRepository:
    """Tests for favourite CRUD."""

    @pytest.fixture
    async def sample_favourite(self, test_session: AsyncSession):
        """Create a sample favourite."""
        from app.domains.shared.models.iam import UserAccount

        user = UserAccount(username="favuser", email="fav@test.com", password_hash="hash", role_type="user")
        test_session.add(user)
        await test_session.flush()

        dev = OSDeveloper(github_login="favdev", is_visible=True)
        test_session.add(dev)
        await test_session.flush()

        fav = OSFavourite(
            user_id=user.user_id,
            developer_id=dev.developer_id,
            notes="Great candidate",
            is_active=True,
        )
        test_session.add(fav)
        await test_session.commit()
        await test_session.refresh(fav)
        return fav

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_list_favourites(self, test_session: AsyncSession, sample_favourite):
        """Test listing favourites for a user."""
        repo = OpenSourceRepository(test_session)
        items, total = await repo.list_favourites(user_id=1)
        assert total >= 1
        assert any(i.favourite_id == sample_favourite.favourite_id for i in items)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_favourite_ids(self, test_session: AsyncSession, sample_favourite):
        """Test getting favourite developer IDs."""
        repo = OpenSourceRepository(test_session)
        ids = await repo.get_favourite_ids(user_id=1)
        assert sample_favourite.developer_id in ids

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_favourite(self, test_session: AsyncSession):
        """Test creating a favourite."""
        from app.domains.shared.models.iam import UserAccount

        user = UserAccount(username="newfavuser", email="newfav@test.com", password_hash="hash", role_type="user")
        test_session.add(user)
        await test_session.flush()

        dev = OSDeveloper(github_login="newfavdev", is_visible=True)
        test_session.add(dev)
        await test_session.flush()

        repo = OpenSourceRepository(test_session)
        fav = await repo.create_favourite(user_id=user.user_id, developer_id=dev.developer_id, notes="Note")
        assert fav.favourite_id is not None
        assert fav.is_active is True

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_delete_favourite_soft(self, test_session: AsyncSession, sample_favourite):
        """Test soft-deleting a favourite."""
        repo = OpenSourceRepository(test_session)
        await repo.delete_favourite(sample_favourite)
        assert sample_favourite.is_active is False


class TestTalentPoolRepository:
    """Tests for talent pool CRUD."""

    @pytest.fixture
    async def sample_pool(self, test_session: AsyncSession):
        """Create a sample talent pool."""
        from app.domains.shared.models.iam import UserAccount

        user = UserAccount(username="poolowner", email="pool@test.com", password_hash="hash", role_type="user")
        test_session.add(user)
        await test_session.flush()

        pool = OSTalentPool(
            owner_user_id=user.user_id,
            pool_name="Test Pool",
            pool_type="custom",
        )
        test_session.add(pool)
        await test_session.commit()
        await test_session.refresh(pool)
        return pool

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_list_talent_pools(self, test_session: AsyncSession, sample_pool):
        """Test listing talent pools."""
        repo = OpenSourceRepository(test_session)
        items = await repo.list_talent_pools(user_id=1)
        assert any(i.pool_id == sample_pool.pool_id for i in items)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_talent_pool(self, test_session: AsyncSession, sample_pool):
        """Test getting talent pool by ID."""
        repo = OpenSourceRepository(test_session)
        result = await repo.get_talent_pool(sample_pool.pool_id)
        assert result is not None
        assert result.pool_name == "Test Pool"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_talent_pool(self, test_session: AsyncSession):
        """Test creating a talent pool."""
        from app.domains.shared.models.iam import UserAccount

        user = UserAccount(username="newpoolowner", email="newpool@test.com", password_hash="hash", role_type="user")
        test_session.add(user)
        await test_session.flush()

        repo = OpenSourceRepository(test_session)
        pool = await repo.create_talent_pool({
            "owner_user_id": user.user_id,
            "pool_name": "New Pool",
        })
        assert pool.pool_id is not None
        assert pool.pool_status == "active"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_update_talent_pool(self, test_session: AsyncSession, sample_pool):
        """Test updating a talent pool."""
        repo = OpenSourceRepository(test_session)
        updated = await repo.update_talent_pool(sample_pool.pool_id, {"pool_name": "Updated"})
        assert updated is not None
        assert updated.pool_name == "Updated"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_delete_talent_pool(self, test_session: AsyncSession, sample_pool):
        """Test deleting a talent pool."""
        repo = OpenSourceRepository(test_session)
        await repo.delete_talent_pool(sample_pool.pool_id)
        assert await repo.get_talent_pool(sample_pool.pool_id) is None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_add_pool_member(self, test_session: AsyncSession, sample_pool):
        """Test adding a member to a pool."""
        dev = OSDeveloper(github_login="poolmember", is_visible=True)
        test_session.add(dev)
        await test_session.flush()

        repo = OpenSourceRepository(test_session)
        member = await repo.add_pool_member(sample_pool.pool_id, dev.developer_id)
        assert member.pool_member_id is not None
        # Need to commit so subsequent remove tests don't fail on missing user FK
        await test_session.commit()


class TestCollectTaskRepository:
    """Tests for collect task CRUD."""

    @pytest.fixture
    async def sample_task(self, test_session: AsyncSession):
        """Create a sample collect task."""
        task = OSCollectTask(
            task_name="test-task",
            status="pending",
            config_json={"repos": ["test/repo"]},
        )
        test_session.add(task)
        await test_session.commit()
        await test_session.refresh(task)
        return task

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_list_collect_tasks(self, test_session: AsyncSession, sample_task):
        """Test listing collect tasks."""
        repo = OpenSourceRepository(test_session)
        items, total = await repo.list_collect_tasks()
        assert total >= 1

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_collect_task(self, test_session: AsyncSession, sample_task):
        """Test getting collect task by ID."""
        repo = OpenSourceRepository(test_session)
        result = await repo.get_collect_task(sample_task.task_id)
        assert result is not None
        assert result.task_name == "test-task"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_collect_task(self, test_session: AsyncSession):
        """Test creating a collect task."""
        repo = OpenSourceRepository(test_session)
        task = await repo.create_collect_task({
            "task_name": "new-task",
            "config_json": {},
        })
        assert task.task_id is not None
        assert task.status == "pending"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_cancel_collect_task(self, test_session: AsyncSession, sample_task):
        """Test cancelling a collect task."""
        repo = OpenSourceRepository(test_session)
        result = await repo.cancel_collect_task(sample_task.task_id)
        assert result is not None
        assert result.status == "cancelled"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_delete_collect_task(self, test_session: AsyncSession, sample_task):
        """Test deleting a collect task."""
        repo = OpenSourceRepository(test_session)
        deleted = await repo.delete_collect_task(sample_task.task_id)
        assert deleted is True
        assert await repo.get_collect_task(sample_task.task_id) is None


class TestStatsRepository:
    """Tests for stats and embedding methods."""

    @pytest.fixture
    async def sample_developer_for_stats(self, test_session: AsyncSession):
        """Create a sample developer for stats."""
        dev = OSDeveloper(github_login="statsdev", is_visible=True)
        test_session.add(dev)
        await test_session.flush()

        repo = OSRepository(developer_id=dev.developer_id, full_name="statsdev/repo", name="repo")
        test_session.add(repo)
        await test_session.flush()

        skill = OSLanguageSkill(developer_id=dev.developer_id, language="Python", repo_count=5)
        test_session.add(skill)

        config = OSRepoConfig(repo_full_name="statsdev/repo", tech_element="ai", is_active=True)
        test_session.add(config)

        await test_session.commit()
        return dev

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_stats(self, test_session: AsyncSession, sample_developer_for_stats):
        """Test getting aggregated stats."""
        repo = OpenSourceRepository(test_session)
        stats = await repo.get_stats()
        assert "total_developers" in stats
        assert "total_repositories" in stats
        assert "language_distribution" in stats
        assert "tech_element_distribution" in stats

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_embedding_status(self, test_session: AsyncSession, sample_developer_for_stats):
        """Test getting embedding status."""
        repo = OpenSourceRepository(test_session)
        status = await repo.get_embedding_status()
        assert "total_developers" in status
        assert "embedded_count" in status
        assert "pending_count" in status
