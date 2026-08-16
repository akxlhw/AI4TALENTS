"""
OS Collection - 仓库配置 CRUD Mixin

从 os_collection_service.py 拆出：仓库配置的查询/创建/更新/删除，
以及 tech_element 校验。更新 tech_element 时触发开发者标签同步。
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.exceptions import BadRequestError, ConflictError
from app.domains.open_source.models.open_source import OSRepoConfig
from app.domains.open_source.services.os_collection_common import (
    REPO_FULL_NAME_PATTERN,
)
from app.domains.open_source.services.os_tech_tag_sync_mixin import TechTagSyncMixin
from app.domains.shared.constants.tech_taxonomy import (
    VALID_TECH_ELEMENTS,
)

logger = logging.getLogger(__name__)


class RepoConfigMixin(TechTagSyncMixin):
    """仓库配置管理能力（list/get/create/update/delete）。"""

    # ============= Repo Config =============

    async def get_repo_full_names_by_ids(self, repo_config_ids: list[int]) -> dict[int, str]:
        """Batch fetch {repo_config_id: repo_full_name}. Used by collect-check."""
        return await self.repo.get_repo_full_names_by_ids(repo_config_ids)

    async def get_last_collection_status(self, repo_full_names: list[str]) -> dict[str, dict]:
        """Latest non-active collection task per repo_full_name."""
        return await self.repo.get_last_collection_status(repo_full_names)

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
        """
        获取仓库配置列表（带筛选）

        Args:
            page: 页码
            page_size: 每页数量
            tech_elements: 技术要素筛选（支持多选）
            is_active: 是否激活筛选
            collect_enabled: 是否启用采集筛选
            sort_by: 排序方式
            collected_only: 仅显示已完成采集的仓库

        Returns:
            Tuple[List[OSRepoConfig], int]: 配置列表和总数
        """
        filters = {}
        if tech_elements is not None:
            filters["tech_elements"] = tech_elements
        if is_active is not None:
            filters["is_active"] = is_active
        if collect_enabled is not None:
            filters["collect_enabled"] = collect_enabled
        if collected_only:
            filters["collected_only"] = collected_only
        if q:
            filters["q"] = q
        return await self.repo.list_repo_configs(
            filters=filters,
            sort_by=sort_by,
            page=page,
            page_size=page_size,
        )

    async def get_repo_config(self, repo_config_id: int) -> OSRepoConfig | None:
        """
        获取仓库配置详情

        Args:
            repo_config_id: 配置ID

        Returns:
            Optional[OSRepoConfig]: 配置详情或None
        """
        return await self.repo.get_repo_config(repo_config_id)

    def _validate_tech_elements(self, tech_element: list[str] | str) -> list[str]:
        """Validate and normalize tech_element to a list of valid codes.

        Accepts a single code (legacy str) or a list; raises BadRequestError
        on any invalid entry. Returns the normalized list.
        """
        elements = [tech_element] if isinstance(tech_element, str) else list(tech_element or [])
        if not elements:
            raise BadRequestError("tech_element must contain at least one code")
        invalid = [e for e in elements if e not in VALID_TECH_ELEMENTS]
        if invalid:
            raise BadRequestError(
                f"Invalid tech_element: {', '.join(invalid)}. Must be one of: "
                f"{', '.join(sorted(VALID_TECH_ELEMENTS))}"
            )
        # dedupe, preserve order
        seen: set[str] = set()
        return [e for e in elements if not (e in seen or seen.add(e))]

    async def create_repo_config(
        self,
        repo_full_name: str,
        tech_element: list[str] | str,
        display_name: str | None = None,
        description: str | None = None,
        tech_direction_id: int | None = None,
        language: str | None = None,
        notes: str | None = None,
        created_by: int | None = None,
    ) -> OSRepoConfig:
        """
        创建仓库配置

        Args:
            repo_full_name: GitHub 仓库全名，如 'pytorch/pytorch'
            tech_element: 技术要素编码列表（兼容单个字符串）
            display_name: 显示名称
            description: 描述
            tech_direction_id: 技术方向ID
            language: 主要编程语言
            notes: 备注
            created_by: 创建者用户ID

        Returns:
            OSRepoConfig: 创建的配置

        Raises:
            ValueError: 参数校验失败
        """
        if not REPO_FULL_NAME_PATTERN.match(repo_full_name):
            raise BadRequestError("Invalid repo_full_name format. Expected 'owner/repo'")
        tech_elements = self._validate_tech_elements(tech_element)

        existing = await self.repo.get_repo_config_by_full_name(repo_full_name)
        if existing:
            raise ConflictError(f"Repository '{repo_full_name}' already exists")

        # Fetch stars from GitHub API
        stars_count = 0
        try:
            from app.domains.open_source.services.github_client import GitHubClient
            from app.domains.shared.services.config_service import ConfigService

            config_service = ConfigService(self.session)
            github_config = await config_service.get_github_config()
            token = github_config.tokens if github_config.tokens else None
            async with GitHubClient(token=token) as client:
                owner, repo_name = repo_full_name.split("/", 1)
                repo_info = await client.get_repo(owner, repo_name)
                stars_count = repo_info.get("stargazers_count", 0) or 0
        except Exception as e:
            logger.warning(f"Failed to fetch stars for {repo_full_name}: {e}")

        return await self.repo.create_repo_config(
            {
                "repo_full_name": repo_full_name,
                "tech_element": tech_elements,
                "display_name": display_name or repo_full_name.split("/")[-1],
                "description": description,
                "tech_direction_id": tech_direction_id,
                "language": language,
                "notes": notes,
                "created_by": created_by,
                "stars_count": stars_count,
            }
        )

    async def update_repo_config(
        self, repo_config_id: int, update_data: dict[str, Any]
    ) -> OSRepoConfig | None:
        """
        更新仓库配置

        Args:
            repo_config_id: 配置ID
            update_data: 更新字段字典

        Returns:
            Optional[OSRepoConfig]: 更新后的配置或None

        Raises:
            ValueError: tech_element 不合法
        """
        if "tech_element" in update_data:
            update_data["tech_element"] = self._validate_tech_elements(update_data["tech_element"])

        updated = await self.repo.update_repo_config(repo_config_id, update_data)

        # Sync developer tech_tags when tech_element changed (union semantics:
        # each affected developer's tags = union across all their configured repos)
        if updated is not None and "tech_element" in update_data:
            try:
                await self.sync_developer_tech_tags(updated.repo_full_name)
            except Exception as e:
                logger.warning(
                    f"Failed to sync developer tech_tags for {updated.repo_full_name}: {e}"
                )

        return updated

    async def delete_repo_config(self, repo_config_id: int) -> bool:
        """
        删除仓库配置

        Args:
            repo_config_id: 配置ID

        Returns:
            bool: 是否删除成功
        """
        return await self.repo.delete_repo_config(repo_config_id)
