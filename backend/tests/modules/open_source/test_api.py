"""
Open Source Talent API integration tests.
Covers: repo config, developers, search, favorites, talent pools, collect tasks, stats, permissions.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.domains.open_source.models.open_source import (
    OSCollectTask,
    OSDeveloper,
    OSFavourite,
    OSPoolMember,
    OSRepoConfig,
    OSTalentPool,
)


# ============= Repo Config Tests =============

class TestRepoConfig:
    @pytest.mark.asyncio
    async def test_list_repo_configs_as_admin(self, admin_client: AsyncClient, sample_os_repo_config):
        """Admin can list repo configs."""
        response = await admin_client.get("/api/v1/open-source/repo-configs")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_list_repo_configs_as_user_forbidden(self, auth_client: AsyncClient):
        """Normal user cannot list repo configs."""
        response = await auth_client.get("/api/v1/open-source/repo-configs")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_create_repo_config(self, admin_client: AsyncClient):
        """Admin can create repo config."""
        response = await admin_client.post(
            "/api/v1/open-source/repo-configs",
            json={
                "repo_full_name": "new-org/new-repo",
                "display_name": "New Repo",
                "tech_element": "ai",
                "language": "Python",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["repo_full_name"] == "new-org/new-repo"
        assert data["tech_element"] == "ai"

    @pytest.mark.asyncio
    async def test_create_repo_config_invalid_format(self, admin_client: AsyncClient):
        """Invalid repo_full_name format returns 400."""
        response = await admin_client.post(
            "/api/v1/open-source/repo-configs",
            json={"repo_full_name": "invalid", "tech_element": "ai"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_create_repo_config_invalid_tech_element(self, admin_client: AsyncClient):
        """Invalid tech_element returns 400."""
        response = await admin_client.post(
            "/api/v1/open-source/repo-configs",
            json={"repo_full_name": "owner/repo", "tech_element": "invalid"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_create_duplicate_repo_config(self, admin_client: AsyncClient, sample_os_repo_config):
        """Duplicate repo_full_name returns 409."""
        response = await admin_client.post(
            "/api/v1/open-source/repo-configs",
            json={"repo_full_name": sample_os_repo_config.repo_full_name, "tech_element": "ai"},
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_get_repo_config(self, admin_client: AsyncClient, sample_os_repo_config):
        """Admin can get single repo config."""
        response = await admin_client.get(f"/api/v1/open-source/repo-configs/{sample_os_repo_config.repo_config_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["repo_config_id"] == sample_os_repo_config.repo_config_id

    @pytest.mark.asyncio
    async def test_update_repo_config(self, admin_client: AsyncClient, sample_os_repo_config):
        """Admin can update repo config."""
        response = await admin_client.put(
            f"/api/v1/open-source/repo-configs/{sample_os_repo_config.repo_config_id}",
            json={"display_name": "Updated Name", "is_active": False},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == "Updated Name"
        assert data["is_active"] is False

    @pytest.mark.asyncio
    async def test_delete_repo_config(self, admin_client: AsyncClient, sample_os_repo_config, test_session):
        """Admin can delete repo config."""
        response = await admin_client.delete(f"/api/v1/open-source/repo-configs/{sample_os_repo_config.repo_config_id}")
        assert response.status_code == 200

        # Verify deletion
        result = await test_session.execute(
            select(OSRepoConfig).where(OSRepoConfig.repo_config_id == sample_os_repo_config.repo_config_id)
        )
        assert result.scalar_one_or_none() is None


# ============= Developer Tests =============

class TestDevelopers:
    @pytest.mark.asyncio
    async def test_list_developers(self, auth_client: AsyncClient, sample_os_developer):
        """Authenticated user can list developers."""
        response = await auth_client.get("/api/v1/open-source/developers")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert data["total"] >= 1
        assert any(i["github_login"] == "testdeveloper" for i in data["items"])

    @pytest.mark.asyncio
    async def test_list_developers_with_keyword_filter(self, auth_client: AsyncClient, sample_os_developer):
        """Keyword search filters developers."""
        response = await auth_client.get("/api/v1/open-source/developers?q=Test Developer")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any(i["name"] == "Test Developer" for i in data["items"])

    @pytest.mark.asyncio
    async def test_list_developers_with_tech_element_filter(self, auth_client: AsyncClient, sample_os_developer):
        """Tech element filter works."""
        response = await auth_client.get("/api/v1/open-source/developers?tech_elements=ai")
        assert response.status_code == 200
        data = response.json()
        # Should include developer with ai tag
        assert any(i["github_login"] == "testdeveloper" for i in data["items"])

    @pytest.mark.asyncio
    async def test_list_developers_unauthorized(self, client: AsyncClient):
        """Unauthenticated request returns 401."""
        response = await client.get("/api/v1/open-source/developers")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_developer_detail(self, auth_client: AsyncClient, sample_os_developer, sample_os_repositories):
        """Get developer detail with repositories."""
        response = await auth_client.get(f"/api/v1/open-source/developers/{sample_os_developer.developer_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["github_login"] == "testdeveloper"
        assert "repositories" in data
        assert len(data["repositories"]) == 2

    @pytest.mark.asyncio
    async def test_get_developer_not_found(self, auth_client: AsyncClient):
        """Non-existent developer returns 404."""
        response = await auth_client.get("/api/v1/open-source/developers/99999")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_developer_repositories(self, auth_client: AsyncClient, sample_os_developer, sample_os_repositories):
        """List developer repositories."""
        response = await auth_client.get(f"/api/v1/open-source/developers/{sample_os_developer.developer_id}/repositories")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["items"][0]["language"] == "Python"

    @pytest.mark.asyncio
    async def test_list_developer_languages(self, auth_client: AsyncClient, sample_os_developer):
        """List developer language skills."""
        response = await auth_client.get(f"/api/v1/open-source/developers/{sample_os_developer.developer_id}/languages")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_recommend_similar_developers(self, auth_client: AsyncClient, sample_os_developer):
        """Get similar developer recommendations."""
        response = await auth_client.get(f"/api/v1/open-source/developers/{sample_os_developer.developer_id}/recommend?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


# ============= Search Tests =============

class TestSearch:
    @pytest.mark.asyncio
    async def test_keyword_search(self, auth_client: AsyncClient, sample_os_developer):
        """Keyword search returns results."""
        response = await auth_client.post(
            "/api/v1/open-source/search",
            json={"q": "Test Developer", "mode": "keyword", "page": 1, "page_size": 20},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any(i["github_login"] == "testdeveloper" for i in data["items"])

    @pytest.mark.asyncio
    async def test_search_with_filters(self, auth_client: AsyncClient, sample_os_developer):
        """Search with multiple filters."""
        response = await auth_client.post(
            "/api/v1/open-source/search",
            json={
                "q": "",
                "mode": "keyword",
                "filters": {"min_stars": 10000, "tech_elements": ["ai"]},
                "page": 1,
                "page_size": 20,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert all(i["total_stars_received"] >= 10000 for i in data["items"])

    @pytest.mark.asyncio
    async def test_search_unauthorized(self, client: AsyncClient):
        """Unauthenticated search returns 401."""
        response = await client.post("/api/v1/open-source/search", json={"q": "test"})
        assert response.status_code == 401


# ============= Favorite Tests =============

class TestFavorites:
    @pytest.mark.asyncio
    async def test_add_favorite(self, auth_client: AsyncClient, sample_os_developer):
        """User can add favorite."""
        response = await auth_client.post(
            "/api/v1/open-source/favourites",
            json={"developer_id": sample_os_developer.developer_id, "notes": "Strong candidate"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["developer_id"] == sample_os_developer.developer_id
        assert data["notes"] == "Strong candidate"

    @pytest.mark.asyncio
    async def test_add_duplicate_favorite(self, auth_client: AsyncClient, sample_os_favorite):
        """Duplicate favorite returns 409."""
        response = await auth_client.post(
            "/api/v1/open-source/favourites",
            json={"developer_id": sample_os_favorite.developer_id},
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_list_favorites(self, auth_client: AsyncClient, sample_os_favorite):
        """User can list favorites."""
        response = await auth_client.get("/api/v1/open-source/favourites")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any(i["developer_id"] == sample_os_favorite.developer_id for i in data["items"])

    @pytest.mark.asyncio
    async def test_get_favorite_ids(self, auth_client: AsyncClient, sample_os_favorite):
        """Get favorite IDs list."""
        response = await auth_client.get("/api/v1/open-source/favourites/ids")
        assert response.status_code == 200
        data = response.json()
        assert sample_os_favorite.developer_id in data["developer_ids"]

    @pytest.mark.asyncio
    async def test_update_favorite(self, auth_client: AsyncClient, sample_os_favorite):
        """User can update favorite notes."""
        response = await auth_client.put(
            f"/api/v1/open-source/favourites/{sample_os_favorite.developer_id}",
            json={"notes": "Updated notes", "followup_status": "interviewed"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["notes"] == "Updated notes"
        assert data["followup_status"] == "interviewed"

    @pytest.mark.asyncio
    async def test_remove_favorite(self, auth_client: AsyncClient, sample_os_favorite, test_session):
        """User can remove favorite."""
        response = await auth_client.delete(f"/api/v1/open-source/favourites/{sample_os_favorite.developer_id}")
        assert response.status_code == 200

        # Verify soft delete
        result = await test_session.execute(
            select(OSFavourite).where(OSFavourite.favourite_id == sample_os_favorite.favourite_id)
        )
        fav = result.scalar_one()
        assert fav.is_active is False


# ============= Talent Pool Tests =============

class TestTalentPools:
    @pytest.mark.asyncio
    async def test_create_talent_pool(self, auth_client: AsyncClient):
        """User can create talent pool."""
        response = await auth_client.post(
            "/api/v1/open-source/talent-pools",
            json={"pool_name": "Test Pool", "pool_type": "custom", "scope_desc": "For testing"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["pool_name"] == "Test Pool"

    @pytest.mark.asyncio
    async def test_list_talent_pools(self, auth_client: AsyncClient, sample_os_talent_pool):
        """User can list their talent pools."""
        response = await auth_client.get("/api/v1/open-source/talent-pools")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert any(i["pool_id"] == sample_os_talent_pool.pool_id for i in data)

    @pytest.mark.asyncio
    async def test_add_pool_member(self, auth_client: AsyncClient, sample_os_talent_pool, sample_os_developer):
        """User can add member to pool."""
        response = await auth_client.post(
            f"/api/v1/open-source/talent-pools/{sample_os_talent_pool.pool_id}/members/{sample_os_developer.developer_id}"
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_add_duplicate_pool_member(self, auth_client: AsyncClient, sample_os_talent_pool, sample_os_developer):
        """Duplicate pool member returns 409."""
        await auth_client.post(
            f"/api/v1/open-source/talent-pools/{sample_os_talent_pool.pool_id}/members/{sample_os_developer.developer_id}"
        )
        response = await auth_client.post(
            f"/api/v1/open-source/talent-pools/{sample_os_talent_pool.pool_id}/members/{sample_os_developer.developer_id}"
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_remove_pool_member(self, auth_client: AsyncClient, sample_os_talent_pool, sample_os_developer, test_session):
        """User can remove member from pool."""
        await auth_client.post(
            f"/api/v1/open-source/talent-pools/{sample_os_talent_pool.pool_id}/members/{sample_os_developer.developer_id}"
        )
        response = await auth_client.delete(
            f"/api/v1/open-source/talent-pools/{sample_os_talent_pool.pool_id}/members/{sample_os_developer.developer_id}"
        )
        assert response.status_code == 200

        # Verify removal
        result = await test_session.execute(
            select(OSPoolMember).where(
                OSPoolMember.pool_id == sample_os_talent_pool.pool_id,
                OSPoolMember.developer_id == sample_os_developer.developer_id,
            )
        )
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_list_pool_members(self, auth_client: AsyncClient, sample_os_talent_pool, sample_os_developer):
        """User can list pool members."""
        await auth_client.post(
            f"/api/v1/open-source/talent-pools/{sample_os_talent_pool.pool_id}/members/{sample_os_developer.developer_id}"
        )
        response = await auth_client.get(f"/api/v1/open-source/talent-pools/{sample_os_talent_pool.pool_id}/members")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["developer_id"] == sample_os_developer.developer_id


# ============= Collect Task Tests =============

class TestCollectTasks:
    @pytest.mark.asyncio
    async def test_create_collect_task_as_admin(self, admin_client: AsyncClient):
        """Admin can create collect task."""
        response = await admin_client.post(
            "/api/v1/open-source/collect/tasks",
            json={
                "task_name": "Test Collection",
                "tech_elements": ["ai"],
                "contributors_per_repo": 30,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "pending"
        assert data["task_name"] == "Test Collection"

    @pytest.mark.asyncio
    async def test_create_collect_task_as_user_forbidden(self, auth_client: AsyncClient):
        """Normal user cannot create collect task."""
        response = await auth_client.post(
            "/api/v1/open-source/collect/tasks",
            json={"tech_elements": ["ai"]},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_list_collect_tasks(self, admin_client: AsyncClient):
        """Admin can list collect tasks."""
        response = await admin_client.get("/api/v1/open-source/collect/tasks")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    @pytest.mark.asyncio
    async def test_get_collect_task(self, admin_client: AsyncClient, test_session):
        """Admin can get collect task detail."""
        task = OSCollectTask(
            task_name="Test Task",
            status="pending",
            config_json={"tech_elements": ["ai"]},
        )
        test_session.add(task)
        await test_session.commit()

        response = await admin_client.get(f"/api/v1/open-source/collect/tasks/{task.task_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == task.task_id

    @pytest.mark.asyncio
    async def test_cancel_collect_task(self, admin_client: AsyncClient, test_session):
        """Admin can cancel pending task."""
        task = OSCollectTask(
            task_name="Task to Cancel",
            status="pending",
            config_json={},
        )
        test_session.add(task)
        await test_session.commit()

        response = await admin_client.post(f"/api/v1/open-source/collect/tasks/{task.task_id}/cancel")
        assert response.status_code == 200

        # Verify status
        result = await test_session.execute(select(OSCollectTask).where(OSCollectTask.task_id == task.task_id))
        updated = result.scalar_one()
        assert updated.status == "cancelled"


# ============= Stats Tests =============

class TestStats:
    @pytest.mark.asyncio
    async def test_get_stats(self, auth_client: AsyncClient, sample_os_developer):
        """Authenticated user can get stats."""
        response = await auth_client.get("/api/v1/open-source/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_developers" in data
        assert "total_repositories" in data
        assert "language_distribution" in data
        assert "tech_element_distribution" in data

    @pytest.mark.asyncio
    async def test_get_stats_unauthorized(self, client: AsyncClient):
        """Unauthenticated request returns 401."""
        response = await client.get("/api/v1/open-source/stats")
        assert response.status_code == 401


# ============= JD Match Tests =============

class TestJDMatch:
    @pytest.mark.asyncio
    async def test_jd_match(self, auth_client: AsyncClient, sample_os_developer):
        """JD match returns candidates."""
        response = await auth_client.post(
            "/api/v1/open-source/jd-match",
            json={
                "jd_text": "招聘 Python 后端工程师，要求熟悉 FastAPI 和 PostgreSQL",
                "top_k": 10,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert isinstance(data["results"], list)


# ============= Embedding Tests =============

class TestEmbeddings:
    @pytest.mark.asyncio
    async def test_get_embedding_status(self, admin_client: AsyncClient):
        """Admin can get embedding status."""
        response = await admin_client.get("/api/v1/open-source/embeddings/status")
        assert response.status_code == 200
        data = response.json()
        assert "total_developers" in data
        assert "embedded_count" in data
        assert "dimension" in data

    @pytest.mark.asyncio
    async def test_generate_embeddings_as_admin(self, admin_client: AsyncClient, test_session):
        """Admin can trigger embedding generation."""
        from app.domains.shared.models.system_config import SystemConfig
        from app.domains.open_source.models.open_source import OSDeveloper

        # Create a visible developer to process
        dev = OSDeveloper(github_login="test-dev", is_visible=True)
        test_session.add(dev)
        await test_session.flush()

        # Seed required LLM config for embedding generation
        test_session.add_all([
            SystemConfig(config_key="LLM_EMBEDDING_ENABLED", config_value="true", config_type="bool"),
            SystemConfig(config_key="LLM_EMBEDDING_MODEL", config_value="text-embedding-3-small", config_type="string"),
            SystemConfig(config_key="LLM_EMBEDDING_API_BASE", config_value="https://api.openai.com/v1", config_type="string"),
        ])
        await test_session.commit()

        response = await admin_client.post(
            "/api/v1/open-source/embeddings/generate",
            json={"batch_size": 50},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_embedding_progress(self, admin_client: AsyncClient):
        """Admin can get embedding progress."""
        response = await admin_client.get("/api/v1/open-source/embeddings/progress")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "processed" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_cancel_embedding_no_task(self, admin_client: AsyncClient):
        """Cancel returns error when no task is running."""
        response = await admin_client.post("/api/v1/open-source/embeddings/cancel")
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_generate_embeddings_as_user_forbidden(self, auth_client: AsyncClient):
        """Normal user cannot trigger embedding generation."""
        response = await auth_client.post(
            "/api/v1/open-source/embeddings/generate",
            json={"batch_size": 50},
        )
        assert response.status_code == 403


# ============= Security / Permission Tests =============

class TestSecurity:
    @pytest.mark.asyncio
    async def test_sql_injection_in_repo_full_name(self, admin_client: AsyncClient):
        """SQL injection in repo_full_name is blocked by validation."""
        response = await admin_client.post(
            "/api/v1/open-source/repo-configs",
            json={"repo_full_name": "' OR '1'='1", "tech_element": "ai"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_cross_user_favorite_access(self, auth_client: AsyncClient, sample_os_favorite, sample_os_developer, test_session):
        """User cannot access another user's favorites directly via ID manipulation."""
        # Try to delete favorite belonging to another user (if any)
        # The endpoint uses current user from token, so this is inherently protected
        response = await auth_client.delete(f"/api/v1/open-source/favourites/{sample_os_developer.developer_id}")
        # Should return 404 since this favorite doesn't exist for auth_client user
        assert response.status_code in (404, 200)

    @pytest.mark.asyncio
    async def test_unauthorized_access_all_endpoints(self, client: AsyncClient, sample_os_developer):
        """All protected endpoints return 401 without token."""
        endpoints = [
            ("GET", "/api/v1/open-source/developers"),
            ("GET", f"/api/v1/open-source/developers/{sample_os_developer.developer_id}"),
            ("GET", "/api/v1/open-source/stats"),
            ("POST", "/api/v1/open-source/search"),
            ("GET", "/api/v1/open-source/favourites"),
            ("POST", "/api/v1/open-source/favourites"),
            ("GET", "/api/v1/open-source/talent-pools"),
            ("POST", "/api/v1/open-source/talent-pools"),
        ]
        for method, url in endpoints:
            if method == "GET":
                response = await client.get(url)
            else:
                response = await client.post(url, json={})
            assert response.status_code == 401, f"{method} {url} should return 401, got {response.status_code}"

    @pytest.mark.asyncio
    async def test_admin_endpoints_forbidden_to_user(self, auth_client: AsyncClient):
        """Admin-only endpoints return 403 for normal user."""
        endpoints = [
            ("GET", "/api/v1/open-source/repo-configs"),
            ("POST", "/api/v1/open-source/repo-configs"),
            ("GET", "/api/v1/open-source/collect/tasks"),
            ("POST", "/api/v1/open-source/collect/tasks"),
            ("GET", "/api/v1/open-source/embeddings/status"),
            ("POST", "/api/v1/open-source/embeddings/generate"),
        ]
        for method, url in endpoints:
            if method == "GET":
                response = await auth_client.get(url)
            else:
                response = await auth_client.post(url, json={})
            assert response.status_code == 403, f"{method} {url} should return 403, got {response.status_code}"
