"""
Tests for OpenSourceService.
Covers: repo config, collect tasks, developers, favourites, talent pools, search.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.domains.open_source.models.open_source import (
    OSCollectTask,
    OSDeveloper,
    OSFavourite,
    OSRepoConfig,
    OSRepository,
    OSTalentPool,
)
from app.domains.open_source.services.open_source_service import OpenSourceService


class TestRepoConfigService:
    """Tests for repo config service methods."""

    @pytest.fixture
    async def service(self, test_session: AsyncSession):
        """Create OpenSourceService instance."""
        return OpenSourceService(test_session)

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
    async def test_list_repo_configs(self, service: OpenSourceService, sample_config):
        """Test listing repo configs through service."""
        items, total = await service.list_repo_configs()
        assert total >= 1
        assert any(i.repo_config_id == sample_config.repo_config_id for i in items)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_repo_config(self, service: OpenSourceService, sample_config):
        """Test getting repo config through service."""
        result = await service.get_repo_config(sample_config.repo_config_id)
        assert result is not None
        assert result.repo_full_name == "test-org/test-repo"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_repo_config_invalid_format(self, service: OpenSourceService):
        """Test creating repo config with invalid format raises ValueError."""
        with pytest.raises(BadRequestError, match="Invalid repo_full_name"):
            await service.create_repo_config("invalid", "ai")

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_repo_config_invalid_tech_element(self, service: OpenSourceService):
        """Test creating repo config with invalid tech_element raises ValueError."""
        with pytest.raises(BadRequestError, match="Invalid tech_element"):
            await service.create_repo_config("owner/repo", "invalid")

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_repo_config_duplicate(self, service: OpenSourceService, sample_config):
        """Test creating duplicate repo config raises ValueError."""
        with pytest.raises(ConflictError, match="already exists"):
            await service.create_repo_config("test-org/test-repo", "ai")

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_update_repo_config(self, service: OpenSourceService, sample_config):
        """Test updating repo config through service."""
        updated = await service.update_repo_config(
            sample_config.repo_config_id, {"display_name": "Updated"}
        )
        assert updated is not None
        assert updated.display_name == "Updated"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_update_repo_config_invalid_tech(self, service: OpenSourceService, sample_config):
        """Test updating with invalid tech_element raises ValueError."""
        with pytest.raises(BadRequestError, match="Invalid tech_element"):
            await service.update_repo_config(
                sample_config.repo_config_id, {"tech_element": ["invalid"]}
            )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_delete_repo_config(self, service: OpenSourceService, sample_config):
        """Test deleting repo config through service."""
        result = await service.delete_repo_config(sample_config.repo_config_id)
        assert result is True


class TestCollectTaskService:
    """Tests for collect task service methods."""

    @pytest.fixture
    async def service(self, test_session: AsyncSession):
        return OpenSourceService(test_session)

    @pytest.fixture
    async def sample_task(self, test_session: AsyncSession):
        from app.domains.shared.models.iam import UserAccount

        user = UserAccount(
            username="taskuser", email="task@test.com", password_hash="hash", role_type="user"
        )
        test_session.add(user)
        await test_session.flush()

        task = OSCollectTask(
            task_name="test-task",
            status="pending",
            config_json={},
            created_by=user.user_id,
        )
        test_session.add(task)
        await test_session.commit()
        await test_session.refresh(task)
        return task

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_list_collect_tasks(self, service: OpenSourceService, sample_task):
        """Test listing collect tasks."""
        items, total = await service.list_collect_tasks()
        assert total >= 1

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_collect_task(self, service: OpenSourceService, sample_task):
        """Test getting collect task."""
        result = await service.get_collect_task(sample_task.task_id)
        assert result is not None
        assert result.task_name == "test-task"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_collect_task(self, service: OpenSourceService, test_session):
        """Test creating collect task."""
        from app.domains.shared.models.iam import UserAccount

        user = UserAccount(
            username="newtaskuser", email="ntask@test.com", password_hash="hash", role_type="user"
        )
        test_session.add(user)
        await test_session.flush()

        task = await service.create_collect_task("new-task", {"repos": ["a/b"]}, user.user_id)
        assert task.task_id is not None
        assert task.task_name == "new-task"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_cancel_collect_task(self, service: OpenSourceService, sample_task):
        """Test cancelling a pending task."""
        result = await service.cancel_collect_task(sample_task.task_id)
        assert result is not None
        assert result.status == "cancelled"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_cancel_collect_task_not_pending(self, service: OpenSourceService, sample_task):
        """Test cancelling a completed task raises ValueError."""
        sample_task.status = "completed"
        await service.session.commit()
        with pytest.raises(BadRequestError, match="Cannot cancel"):
            await service.cancel_collect_task(sample_task.task_id)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_delete_collect_task_not_allowed(self, service: OpenSourceService, sample_task):
        """Test deleting running task raises ValueError."""
        sample_task.status = "running"
        await service.session.commit()
        with pytest.raises(BadRequestError, match="Cannot delete"):
            await service.delete_collect_task(sample_task.task_id)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_collect_single_repo_not_found(self, service: OpenSourceService):
        """Test collect single repo with invalid config raises ValueError."""
        with pytest.raises(NotFoundError, match="Repo config"):
            await service.collect_single_repo(99999, 30, 1)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_collect_single_repo_disabled(self, service: OpenSourceService, test_session):
        """Test collect single repo when disabled raises ValueError."""
        config = OSRepoConfig(
            repo_full_name="disabled/repo",
            tech_element="ai",
            collect_enabled=False,
        )
        test_session.add(config)
        await test_session.commit()
        await test_session.refresh(config)

        with pytest.raises(BadRequestError, match="disabled"):
            await service.collect_single_repo(config.repo_config_id, 30, 1)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_collect_batch_repos(self, service: OpenSourceService, test_session):
        """Test batch collect repos."""
        from app.domains.shared.models.iam import UserAccount

        user = UserAccount(
            username="batchuser", email="batch@test.com", password_hash="hash", role_type="user"
        )
        test_session.add(user)
        await test_session.flush()

        config = OSRepoConfig(
            repo_full_name="batch/repo1",
            tech_element="ai",
            collect_enabled=True,
        )
        test_session.add(config)
        await test_session.commit()
        await test_session.refresh(config)

        tasks, skipped = await service.collect_batch_repos(
            [config.repo_config_id], 30, user.user_id
        )
        assert len(tasks) == 1
        assert skipped == []


class TestDeveloperService:
    """Tests for developer service methods."""

    @pytest.fixture
    async def service(self, test_session: AsyncSession):
        return OpenSourceService(test_session)

    @pytest.fixture
    async def sample_developer(self, test_session: AsyncSession):
        dev = OSDeveloper(
            github_login="testdeveloper",
            name="Test Developer",
            bio="A test bio",
            location="Beijing",
            total_stars_received=15000,
            primary_languages=["Python"],
            tech_tags=["ai"],
            is_visible=True,
        )
        test_session.add(dev)
        await test_session.commit()
        await test_session.refresh(dev)
        return dev

    @pytest.fixture
    async def sample_repos(self, test_session: AsyncSession, sample_developer):
        repos = [
            OSRepository(
                developer_id=sample_developer.developer_id,
                full_name="testdeveloper/awesome-project",
                name="awesome-project",
                language="Python",
                stars_count=8500,
            ),
        ]
        for r in repos:
            test_session.add(r)
        await test_session.commit()
        return repos

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_list_developers(self, service: OpenSourceService, sample_developer):
        """Test listing developers."""
        items, total = await service.list_developers()
        assert total >= 1
        assert any(i.developer_id == sample_developer.developer_id for i in items)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_list_developers_with_filters(self, service: OpenSourceService, sample_developer):
        """Test listing developers with filters."""
        items, total = await service.list_developers(q="Test Developer")
        assert total >= 1

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_developer(self, service: OpenSourceService, sample_developer):
        """Test getting developer."""
        result = await service.get_developer(sample_developer.developer_id)
        assert result is not None
        assert result.github_login == "testdeveloper"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_developer_detail(
        self, service: OpenSourceService, sample_developer, sample_repos
    ):
        """Test getting developer detail."""
        detail = await service.get_developer_detail(sample_developer.developer_id)
        assert detail.github_login == "testdeveloper"
        assert len(detail.repositories) == 1

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_developer_detail_not_found(self, service: OpenSourceService):
        """Test getting detail for non-existent developer raises ValueError."""
        with pytest.raises(NotFoundError, match="Developer"):
            await service.get_developer_detail(99999)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_compare_developers(self, service: OpenSourceService, test_session):
        """Test comparing developers."""
        dev1 = OSDeveloper(github_login="dev1", total_stars_received=100, is_visible=True)
        dev2 = OSDeveloper(github_login="dev2", total_stars_received=200, is_visible=True)
        test_session.add_all([dev1, dev2])
        await test_session.commit()
        await test_session.refresh(dev1)
        await test_session.refresh(dev2)

        result = await service.compare_developers([dev1.developer_id, dev2.developer_id])
        assert len(result.developers) == 2
        assert "radar" in result.model_dump()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_compare_developers_invalid_count(self, service: OpenSourceService):
        """Test comparing with invalid developer count raises ValueError."""
        with pytest.raises(BadRequestError, match="2 to 5"):
            await service.compare_developers([1])

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_recommend_similar(self, service: OpenSourceService, sample_developer):
        """Test recommending similar developers."""
        result = await service.recommend_similar(sample_developer.developer_id, limit=5)
        assert isinstance(result, list)


class TestSearchService:
    """Tests for search service methods."""

    @pytest.fixture
    async def service(self, test_session: AsyncSession):
        return OpenSourceService(test_session)

    @pytest.fixture
    async def sample_developer(self, test_session: AsyncSession):
        dev = OSDeveloper(
            github_login="searchdev",
            name="Search Developer",
            total_stars_received=10000,
            is_visible=True,
        )
        test_session.add(dev)
        await test_session.commit()
        await test_session.refresh(dev)
        return dev

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_search_developers_keyword(self, service: OpenSourceService, sample_developer):
        """Test keyword search."""
        from app.domains.open_source.schemas.open_source import OSSearchRequest

        req = OSSearchRequest(q="Search Developer", mode="keyword")
        items, total = await service.search_developers(req)
        assert total >= 1

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_search_developers_empty_query(
        self, service: OpenSourceService, sample_developer
    ):
        """Test search with empty query falls back to list."""
        from app.domains.open_source.schemas.open_source import OSSearchRequest

        req = OSSearchRequest(q="", mode="keyword")
        items, total = await service.search_developers(req)
        assert total >= 1


class TestFavouriteService:
    """Tests for favourite service methods."""

    @pytest.fixture
    async def service(self, test_session: AsyncSession):
        return OpenSourceService(test_session)

    @pytest.fixture
    async def sample_favourite(self, test_session: AsyncSession):
        from app.domains.shared.models.iam import UserAccount

        user = UserAccount(
            username="favuser", email="fav@test.com", password_hash="hash", role_type="user"
        )
        test_session.add(user)
        await test_session.flush()

        dev = OSDeveloper(github_login="favdev", is_visible=True)
        test_session.add(dev)
        await test_session.flush()

        fav = OSFavourite(
            user_id=user.user_id,
            developer_id=dev.developer_id,
            notes="Great",
            is_active=True,
        )
        test_session.add(fav)
        await test_session.commit()
        await test_session.refresh(fav)
        return fav

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_list_favourites(self, service: OpenSourceService, sample_favourite):
        """Test listing favourites."""
        items, total = await service.list_favourites(user_id=sample_favourite.user_id)
        assert total >= 1

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_favourite_ids(self, service: OpenSourceService, sample_favourite):
        """Test getting favourite IDs."""
        ids = await service.get_favourite_ids(user_id=sample_favourite.user_id)
        assert sample_favourite.developer_id in ids

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_add_favourite(self, service: OpenSourceService, test_session):
        """Test adding favourite."""
        from app.domains.shared.models.iam import UserAccount

        user = UserAccount(
            username="newfavuser", email="newfav@test.com", password_hash="hash", role_type="user"
        )
        test_session.add(user)
        await test_session.flush()

        dev = OSDeveloper(github_login="newfavdev", is_visible=True)
        test_session.add(dev)
        await test_session.flush()

        fav = await service.add_favourite(
            user_id=user.user_id, developer_id=dev.developer_id, notes="Good"
        )
        assert fav.favourite_id is not None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_add_duplicate_favourite(self, service: OpenSourceService, sample_favourite):
        """Test adding duplicate favourite raises ValueError."""
        with pytest.raises(ConflictError, match="Already favorited"):
            await service.add_favourite(
                user_id=sample_favourite.user_id, developer_id=sample_favourite.developer_id
            )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_update_favourite(self, service: OpenSourceService, sample_favourite):
        """Test updating favourite."""
        updated = await service.update_favourite(
            user_id=sample_favourite.user_id,
            developer_id=sample_favourite.developer_id,
            notes="Updated notes",
        )
        assert updated is not None
        assert updated.notes == "Updated notes"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_remove_favourite(self, service: OpenSourceService, sample_favourite):
        """Test removing favourite."""
        result = await service.remove_favourite(
            user_id=sample_favourite.user_id, developer_id=sample_favourite.developer_id
        )
        assert result is True

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_remove_favourite_not_found(self, service: OpenSourceService):
        """Test removing non-existent favourite returns False."""
        result = await service.remove_favourite(user_id=99999, developer_id=99999)
        assert result is False


class TestTalentPoolService:
    """Tests for talent pool service methods."""

    @pytest.fixture
    async def service(self, test_session: AsyncSession):
        return OpenSourceService(test_session)

    @pytest.fixture
    async def sample_pool(self, test_session: AsyncSession):
        from app.domains.shared.models.iam import UserAccount

        user = UserAccount(
            username="poolowner", email="pool@test.com", password_hash="hash", role_type="user"
        )
        test_session.add(user)
        await test_session.flush()

        pool = OSTalentPool(owner_user_id=user.user_id, pool_name="Test Pool")
        test_session.add(pool)
        await test_session.commit()
        await test_session.refresh(pool)
        return pool

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_list_talent_pools(self, service: OpenSourceService, sample_pool):
        """Test listing talent pools."""
        items = await service.list_talent_pools(user_id=sample_pool.owner_user_id)
        assert any(i.pool_id == sample_pool.pool_id for i in items)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_talent_pool(self, service: OpenSourceService, test_session):
        """Test creating talent pool."""
        from app.domains.shared.models.iam import UserAccount

        user = UserAccount(
            username="newpoolowner",
            email="newpool@test.com",
            password_hash="hash",
            role_type="user",
        )
        test_session.add(user)
        await test_session.flush()

        pool = await service.create_talent_pool(user_id=user.user_id, pool_name="New Pool")
        assert pool.pool_id is not None
        assert pool.pool_name == "New Pool"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_update_talent_pool(self, service: OpenSourceService, sample_pool):
        """Test updating talent pool."""
        updated = await service.update_talent_pool(sample_pool.pool_id, {"pool_name": "Updated"})
        assert updated is not None
        assert updated.pool_name == "Updated"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_delete_talent_pool(self, service: OpenSourceService, sample_pool):
        """Test deleting talent pool."""
        result = await service.delete_talent_pool(sample_pool.pool_id)
        assert result is None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_add_pool_member(self, service: OpenSourceService, sample_pool, test_session):
        """Test adding pool member."""
        dev = OSDeveloper(github_login="poolmember", is_visible=True)
        test_session.add(dev)
        await test_session.flush()

        member = await service.add_pool_member(sample_pool.pool_id, dev.developer_id)
        assert member.pool_member_id is not None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_add_duplicate_pool_member(
        self, service: OpenSourceService, sample_pool, test_session
    ):
        """Test adding duplicate pool member raises ValueError."""
        dev = OSDeveloper(github_login="dupmember", is_visible=True)
        test_session.add(dev)
        await test_session.flush()

        await service.add_pool_member(sample_pool.pool_id, dev.developer_id)
        with pytest.raises(ConflictError, match="Already in pool"):
            await service.add_pool_member(sample_pool.pool_id, dev.developer_id)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_remove_pool_member(self, service: OpenSourceService, sample_pool, test_session):
        """Test removing pool member."""
        dev = OSDeveloper(github_login="removemember", is_visible=True)
        test_session.add(dev)
        await test_session.flush()

        await service.add_pool_member(sample_pool.pool_id, dev.developer_id)
        result = await service.remove_pool_member(sample_pool.pool_id, dev.developer_id)
        assert result is True

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_remove_pool_member_not_found(self, service: OpenSourceService, sample_pool):
        """Test removing non-existent pool member returns False."""
        result = await service.remove_pool_member(sample_pool.pool_id, 99999)
        assert result is False
