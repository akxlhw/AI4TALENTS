"""
OS Collection - 开发者技术标签同步 Mixin

从 os_collection_service.py 拆出；作为采集服务 Mixin 链的基类，
声明 session/repo 属性供后续 Mixin 使用。
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.open_source.repositories.open_source import OpenSourceRepository

logger = logging.getLogger(__name__)


class TechTagSyncMixin:
    """开发者 tech_tags 同步能力（按仓库全量重算并集）。"""

    session: AsyncSession
    repo: OpenSourceRepository

    async def sync_developer_tech_tags(self, repo_full_name: str) -> int:
        """Recalculate tech_tags for all developers involved with a repo.

        For each developer (contributors + owner), the new tech_tags is the
        union of tech_element arrays across ALL configured repos they
        contribute to or own — not just this repo.

        Returns the number of developers updated.
        """
        developer_ids = await self.repo.get_developer_ids_by_repo_full_name(repo_full_name)
        if not developer_ids:
            return 0

        updated_count = 0
        for dev_id in developer_ids:
            union = await self.repo.get_union_tech_elements_for_developer(dev_id)
            count = await self.repo.batch_update_tech_tags([dev_id], union)
            updated_count += count
        return updated_count
