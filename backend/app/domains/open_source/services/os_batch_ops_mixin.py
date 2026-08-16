"""
OS Collection - 批量操作 Mixin

从 os_collection_service.py 拆出：批量创建仓库配置、批量设置技术要素、
仓库采集数据清理（purge）预览与执行。
"""

from __future__ import annotations

import logging
from typing import Any
from typing import cast as tcast

from app.core.exceptions import NotFoundError
from app.domains.open_source.schemas.open_source import OSPurgePreview
from app.domains.open_source.services.os_collection_common import parse_repo_input
from app.domains.open_source.services.os_repo_config_mixin import RepoConfigMixin

logger = logging.getLogger(__name__)


class BatchOpsMixin(RepoConfigMixin):
    """批量仓库操作与数据清理能力。"""

    async def batch_create_repo_configs(
        self,
        repo_inputs: list[str],
        tech_element: list[str] | str,
        created_by: int | None = None,
    ) -> dict[str, list]:
        """Batch create repo configs with auto-fetched GitHub metadata.

        Each input is parsed (URL or owner/repo), then GitHub API is called
        to fetch repo metadata (name, description, language, stars). Existing
        repos are skipped, invalid/unreachable repos go to failed.

        Returns {"created": [...], "skipped": [...], "failed": [...]}.
        """
        from app.domains.open_source.services.github_client import GitHubClient
        from app.domains.shared.services.config_service import ConfigService

        tech_elements = self._validate_tech_elements(tech_element)

        # Get GitHub token once for the whole batch
        config_service = ConfigService(self.session)
        github_config = await config_service.get_github_config()
        token = github_config.tokens if github_config.tokens else None

        created: list[dict[str, Any]] = []
        skipped: list[dict[str, str]] = []
        failed: list[dict[str, str]] = []

        for raw_input in repo_inputs:
            raw_input = raw_input.strip()
            if not raw_input:
                continue

            repo_full_name = parse_repo_input(raw_input)
            if not repo_full_name:
                failed.append({"repo_input": raw_input, "reason": "无法解析仓库地址"})
                continue

            # Check duplicate
            existing = await self.repo.get_repo_config_by_full_name(repo_full_name)
            if existing:
                skipped.append({"repo_input": raw_input, "reason": "仓库配置已存在"})
                continue

            # Fetch metadata from GitHub
            try:
                async with GitHubClient(token=token) as client:
                    owner, repo_name = repo_full_name.split("/", 1)
                    repo_info = await client.get_repo(owner, repo_name)

                if not repo_info:
                    failed.append(
                        {"repo_input": raw_input, "reason": "GitHub 返回 404（仓库不存在）"}
                    )
                    continue

                config = await self.repo.create_repo_config(
                    {
                        "repo_full_name": repo_full_name,
                        "tech_element": tech_elements,
                        "display_name": repo_info.get("name") or repo_full_name.split("/")[-1],
                        "description": (repo_info.get("description") or "")[:65000],
                        "language": repo_info.get("language"),
                        "created_by": created_by,
                        "stars_count": repo_info.get("stargazers_count", 0) or 0,
                    }
                )
                created.append(
                    {
                        "repo_config_id": config.repo_config_id,
                        "repo_full_name": config.repo_full_name,
                        "display_name": config.display_name,
                        "language": config.language,
                        "stars_count": config.stars_count,
                    }
                )
            except Exception as e:
                failed.append({"repo_input": raw_input, "reason": str(e)[:200]})
                logger.warning(f"Batch create failed for {repo_full_name}: {e}")

        return {"created": created, "skipped": skipped, "failed": failed}

    async def batch_update_tech_element(
        self,
        repo_config_ids: list[int],
        tech_element: list[str],
    ) -> dict[str, Any]:
        """Batch set tech_element on multiple repos, syncing developer tags.

        Each repo goes through update_repo_config (which validates and
        triggers sync_developer_tech_tags), so developer tags stay correct.
        Individual failures are collected, not fatal.

        Returns {"updated": int, "failed": [{repo_config_id, reason}]}.
        """
        elements = self._validate_tech_elements(tech_element)
        updated = 0
        failed: list[dict[str, str]] = []

        for repo_config_id in repo_config_ids:
            try:
                result = await self.repo.update_repo_config(
                    repo_config_id, {"tech_element": elements}
                )
                if result is None:
                    failed.append({"repo_input": str(repo_config_id), "reason": "仓库配置不存在"})
                    continue
                # Trigger developer tag sync (same as single update path)
                try:
                    await self.sync_developer_tech_tags(result.repo_full_name)
                except Exception as e:
                    logger.warning(
                        f"Failed to sync developer tech_tags for {result.repo_full_name}: {e}"
                    )
                updated += 1
            except Exception as e:
                failed.append({"repo_input": str(repo_config_id), "reason": str(e)[:200]})

        return {"updated": updated, "failed": failed}

    async def preview_repo_purge(self, repo_config_id: int) -> OSPurgePreview:
        """
        预览仓库采集数据清理的影响范围（不执行删除）

        Args:
            repo_config_id: 配置ID

        Returns:
            OSPurgePreview: 各表将删除/保留的计数

        Raises:
            NotFoundError: 配置不存在
        """
        config = await self.repo.get_repo_config(repo_config_id)
        if not config:
            raise NotFoundError("Repo config", repo_config_id)
        repo_full_name = tcast(str, config.repo_full_name)
        counts = await self.repo.get_repo_purge_preview(repo_full_name)
        return OSPurgePreview(
            repo_full_name=repo_full_name,
            config_deleted=False,
            **counts,
        )

    async def purge_repo(self, repo_config_id: int, delete_config: bool = False) -> OSPurgePreview:
        """
        执行仓库采集数据清理（硬删除），可选同时删除仓库配置行

        Args:
            repo_config_id: 配置ID
            delete_config: 是否同时删除仓库配置

        Returns:
            OSPurgePreview: 实际删除/保留的计数

        Raises:
            NotFoundError: 配置不存在
        """
        config = await self.repo.get_repo_config(repo_config_id)
        if not config:
            raise NotFoundError("Repo config", repo_config_id)
        repo_full_name = tcast(str, config.repo_full_name)
        counts = await self.repo.purge_repo_data(repo_full_name)
        config_deleted = False
        if delete_config:
            config_deleted = await self.repo.delete_repo_config(repo_config_id)
        return OSPurgePreview(
            repo_full_name=repo_full_name,
            config_deleted=config_deleted,
            **counts,
        )
