"""
OS Collection Service - 开源人才仓库采集业务逻辑层（门面聚合）

实现已按职能拆分为同目录 Mixin 模块，本文件聚合为原 OSCollectionService：
- os_repo_config_mixin.py: 仓库配置 CRUD（含 tech_element 校验）
- os_collect_task_mixin.py: 采集任务 CRUD、采集触发与后台执行
- os_batch_ops_mixin.py: 批量操作（batch create、batch tech_element、purge）
- os_tech_tag_sync_mixin.py: 开发者技术标签同步
- os_collection_common.py: 仓库输入解析与按仓库串行锁

公共接口（OSCollectionService、parse_repo_input、REPO_FULL_NAME_PATTERN、
_get_repo_lock）经本模块 re-export 保持，调用方零改动。

遵循架构规范：Endpoint -> Service -> Repository
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.open_source.repositories.open_source import OpenSourceRepository
from app.domains.open_source.services.os_batch_ops_mixin import BatchOpsMixin
from app.domains.open_source.services.os_collect_task_mixin import CollectTaskMixin
from app.domains.open_source.services.os_collection_common import (
    _REPO_LOCKS,
    REPO_FULL_NAME_PATTERN,
    _get_repo_lock,
    parse_repo_input,
)

__all__ = [
    "OSCollectionService",
    "parse_repo_input",
    "REPO_FULL_NAME_PATTERN",
    "_get_repo_lock",
    "_REPO_LOCKS",
]


class OSCollectionService(CollectTaskMixin, BatchOpsMixin):
    """
    开源采集服务 - 封装仓库采集相关的业务逻辑

    职责：
    - 仓库配置管理（RepoConfigMixin）
    - 采集任务管理、采集触发与后台执行（CollectTaskMixin）
    - 批量操作与数据清理（BatchOpsMixin）
    - 开发者技术标签同步（TechTagSyncMixin）
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = OpenSourceRepository(session)
