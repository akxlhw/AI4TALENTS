"""
Open Source Service - 开源人才库业务逻辑门面

Thin facade that delegates to specialised sub-services:
- OSCollectionService: 仓库配置 & 采集任务
- OSDeveloperService: 开发者查询/搜索/对比/推荐/统计/JD匹配
- OSFavouriteService: 收藏 & 人才池
- OSEmbeddingService: 嵌入向量生成

Endpoint layer continues to import OpenSourceService — no API changes needed.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.open_source.models.open_source import (
    OSCollectTask,
    OSDeveloper,
    OSFavourite,
    OSPoolMember,
    OSRepoConfig,
    OSTalentPool,
)
from app.domains.open_source.repositories.open_source import OpenSourceRepository
from app.domains.open_source.schemas.open_source import (
    OSDeveloperCompareResponse,
    OSDeveloperDetail,
    OSJDMatchResponse,
    OSRepositoryContributor,
    OSSearchRequest,
    OSStatsResponse,
)
from app.domains.open_source.services.os_collection_service import OSCollectionService
from app.domains.open_source.services.os_developer_service import OSDeveloperService
from app.domains.open_source.services.os_embedding_service import OSEmbeddingService
from app.domains.open_source.services.os_favourite_service import OSFavouriteService

logger = logging.getLogger(__name__)

VALID_TECH_ELEMENTS = {"ai", "robotics", "data_science", "networks", "systems", "security"}
REPO_FULL_NAME_PATTERN = re.compile(r"^[\w.-]+/[\w.-]+$")
COLLECTION_SEMAPHORE = asyncio.Semaphore(1)


class OpenSourceService:
    """开源人才服务 — 门面类，委托给子 Service。

    保留全部公开方法签名以确保向后兼容。内部实现转发到对应的子 Service。
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = OpenSourceRepository(session)
        self._collection = OSCollectionService(session)
        self._developer = OSDeveloperService(session)
        self._favourite = OSFavouriteService(session)
        self._embedding = OSEmbeddingService(session)

    # ============= Repo Config =============

    async def list_repo_configs(
        self,
        page: int = 1,
        page_size: int = 50,
        tech_elements: list[str] | None = None,
        is_active: bool | None = None,
        collect_enabled: bool | None = None,
        sort_by: str = "id_desc",
        collected_only: bool = False,
        q: str | None = None,
    ) -> tuple[list[OSRepoConfig], int]:
        return await self._collection.list_repo_configs(
            page=page,
            page_size=page_size,
            tech_elements=tech_elements,
            is_active=is_active,
            collect_enabled=collect_enabled,
            sort_by=sort_by,
            collected_only=collected_only,
            q=q,
        )

    async def get_repo_config(self, repo_config_id: int) -> OSRepoConfig | None:
        return await self._collection.get_repo_config(repo_config_id)

    async def create_repo_config(
        self,
        repo_full_name: str,
        tech_element: str,
        display_name: str | None = None,
        description: str | None = None,
        tech_direction_id: int | None = None,
        language: str | None = None,
        notes: str | None = None,
        created_by: int | None = None,
    ) -> OSRepoConfig:
        return await self._collection.create_repo_config(
            repo_full_name=repo_full_name,
            tech_element=tech_element,
            display_name=display_name,
            description=description,
            tech_direction_id=tech_direction_id,
            language=language,
            notes=notes,
            created_by=created_by,
        )

    async def update_repo_config(self, repo_config_id: int, update_data: dict[str, Any]) -> OSRepoConfig | None:
        return await self._collection.update_repo_config(repo_config_id, update_data)

    async def delete_repo_config(self, repo_config_id: int) -> bool:
        return await self._collection.delete_repo_config(repo_config_id)

    # ============= Collect Task =============

    async def list_collect_tasks(self, page: int = 1, page_size: int = 20) -> tuple[list[OSCollectTask], int]:
        return await self._collection.list_collect_tasks(page=page, page_size=page_size)

    async def get_collect_task(self, task_id: int) -> OSCollectTask | None:
        return await self._collection.get_collect_task(task_id)

    async def create_collect_task(self, task_name: str, config_json: dict[str, Any], created_by: int) -> OSCollectTask:
        return await self._collection.create_collect_task(task_name=task_name, config_json=config_json, created_by=created_by)

    async def cancel_collect_task(self, task_id: int) -> OSCollectTask | None:
        return await self._collection.cancel_collect_task(task_id)

    async def delete_collect_task(self, task_id: int) -> bool:
        return await self._collection.delete_collect_task(task_id)

    async def collect_single_repo(
        self,
        repo_config_id: int,
        contributors_per_repo: int,
        created_by: int,
    ) -> tuple[OSCollectTask, str, str]:
        return await self._collection.collect_single_repo(
            repo_config_id=repo_config_id,
            contributors_per_repo=contributors_per_repo,
            created_by=created_by,
        )

    async def collect_batch_repos(
        self,
        repo_config_ids: list[int],
        contributors_per_repo: int,
        created_by: int,
    ) -> tuple[list[OSCollectTask], list[dict[str, Any]]]:
        return await self._collection.collect_batch_repos(
            repo_config_ids=repo_config_ids,
            contributors_per_repo=contributors_per_repo,
            created_by=created_by,
        )

    # ============= Developer =============

    async def list_developers(self, **kwargs: Any) -> tuple[list[OSDeveloper], int]:
        return await self._developer.list_developers(**kwargs)

    async def get_developer(self, developer_id: int) -> OSDeveloper | None:
        return await self._developer.get_developer(developer_id)

    async def get_developer_detail(self, developer_id: int) -> OSDeveloperDetail:
        return await self._developer.get_developer_detail(developer_id)

    async def get_repository_detail(self, repo_full_name: str) -> dict[str, Any]:
        return await self._developer.get_repository_detail(repo_full_name)

    async def get_repository_contributors(self, repo_full_name: str, page: int = 1, page_size: int = 50) -> tuple[list[OSRepositoryContributor], int]:
        return await self._developer.get_repository_contributors(repo_full_name, page=page, page_size=page_size)

    async def search_developers(self, req: OSSearchRequest) -> tuple[list[OSDeveloper], int]:
        return await self._developer.search_developers(req)

    async def compare_developers(self, developer_ids: list[int]) -> OSDeveloperCompareResponse:
        return await self._developer.compare_developers(developer_ids)

    async def recommend_similar(self, developer_id: int, limit: int = 10) -> list[OSDeveloper]:
        return await self._developer.recommend_similar(developer_id, limit=limit)

    # ============= Favourite =============

    async def list_favourites(self, user_id: int, page: int = 1, page_size: int = 20, keyword: str | None = None) -> tuple[list[OSFavourite], int]:
        return await self._favourite.list_favourites(user_id=user_id, page=page, page_size=page_size, keyword=keyword)

    async def get_favourite_ids(self, user_id: int) -> list[int]:
        return await self._favourite.get_favourite_ids(user_id)

    async def add_favourite(self, user_id: int, developer_id: int, notes: str | None = None) -> OSFavourite:
        return await self._favourite.add_favourite(user_id=user_id, developer_id=developer_id, notes=notes)

    async def update_favourite(self, user_id: int, developer_id: int, notes: str | None = None, followup_status: str | None = None) -> OSFavourite | None:
        return await self._favourite.update_favourite(user_id=user_id, developer_id=developer_id, notes=notes, followup_status=followup_status)

    async def remove_favourite(self, user_id: int, developer_id: int) -> bool:
        return await self._favourite.remove_favourite(user_id=user_id, developer_id=developer_id)

    # ============= Talent Pool =============

    async def list_talent_pools(self, user_id: int) -> list[OSTalentPool]:
        return await self._favourite.list_talent_pools(user_id)

    async def create_talent_pool(self, user_id: int, pool_name: str, pool_type: str | None = "custom", scope_desc: str | None = None) -> OSTalentPool:
        return await self._favourite.create_talent_pool(user_id=user_id, pool_name=pool_name, pool_type=pool_type, scope_desc=scope_desc)

    async def update_talent_pool(self, pool_id: int, update_data: dict[str, Any]) -> OSTalentPool | None:
        return await self._favourite.update_talent_pool(pool_id, update_data)

    async def delete_talent_pool(self, pool_id: int) -> bool:
        return await self._favourite.delete_talent_pool(pool_id)

    async def add_pool_member(self, pool_id: int, developer_id: int, notes: str | None = None) -> OSPoolMember:
        return await self._favourite.add_pool_member(pool_id=pool_id, developer_id=developer_id, notes=notes)

    async def remove_pool_member(self, pool_id: int, developer_id: int) -> bool:
        return await self._favourite.remove_pool_member(pool_id=pool_id, developer_id=developer_id)

    async def list_pool_members(self, pool_id: int, page: int = 1, page_size: int = 20) -> tuple[list[dict[str, Any]], int]:
        return await self._favourite.list_pool_members(pool_id=pool_id, page=page, page_size=page_size)

    # ============= Stats & JD Match =============

    async def get_stats(self) -> OSStatsResponse:
        return await self._developer.get_stats()

    async def jd_match(self, jd_text: str, filters: Any | None = None, top_k: int = 20) -> OSJDMatchResponse:
        return await self._developer.jd_match(jd_text=jd_text, filters=filters, top_k=top_k)

    # ============= Embedding =============

    async def get_visible_developer_ids(self) -> list[int]:
        return await self._developer.get_visible_developer_ids()

    async def get_embedding_status(self) -> dict[str, int]:
        return await self._embedding.get_embedding_status()

    async def get_embedding_status_with_config(self) -> dict[str, Any]:
        return await self._embedding.get_embedding_status_with_config()

    async def trigger_batch_embedding(self, batch_size: int, force: bool) -> int:
        return await self._embedding.trigger_batch_embedding(batch_size=batch_size, force=force)

    async def generate_single_embedding(self, developer_id: int) -> None:
        return await self._embedding.generate_single_embedding(developer_id)

    @staticmethod
    async def run_embedding_generation_background(
        developer_ids: list[int],
        batch_size: int,
        force: bool,
        progress_dict: dict,
    ) -> None:
        return await OSEmbeddingService.run_embedding_generation_background(
            developer_ids=developer_ids,
            batch_size=batch_size,
            force=force,
            progress_dict=progress_dict,
        )

    async def generate_embeddings(self, batch_size: int = 50) -> dict[str, Any]:
        return await self._embedding.generate_embeddings(batch_size=batch_size)

    # ============= Repository passthroughs =============

    async def get_developer_repositories(self, developer_id: int) -> list[Any]:
        return await self._developer.get_developer_repositories(developer_id)

    async def get_developer_contributions(self, developer_id: int) -> list[Any]:
        return await self._developer.get_developer_contributions(developer_id)

    async def get_developer_languages(self, developer_id: int) -> list[Any]:
        return await self._developer.get_developer_languages(developer_id)

    async def get_developers_by_ids(self, developer_ids: list[int]) -> list[OSDeveloper]:
        return await self._developer.get_developers_by_ids(developer_ids)

    async def get_repositories_for_developers(self, developer_ids: list[int]) -> dict[int, list[Any]]:
        return await self._developer.get_repositories_for_developers(developer_ids)

    async def get_raw_developers_by_logins(self, github_logins: list[str]) -> dict[str, dict[str, Any]]:
        return await self._developer.get_raw_developers_by_logins(github_logins)

    async def get_collected_repos_for_developers(self, developer_ids: list[int]) -> dict[int, list[str]]:
        return await self._developer.get_collected_repos_for_developers(developer_ids)

    async def get_talent_pool(self, pool_id: int) -> OSTalentPool | None:
        return await self._favourite.get_talent_pool(pool_id)

    # ============= Background collection =============

    async def run_repo_collection_background(
        self,
        task_id: int,
        repo_config_id: int,
        repo_full_name: str,
        tech_element: str,
        contributors_per_repo: int,
    ) -> None:
        return await self._collection.run_repo_collection_background(
            task_id=task_id,
            repo_config_id=repo_config_id,
            repo_full_name=repo_full_name,
            tech_element=tech_element,
            contributors_per_repo=contributors_per_repo,
        )
