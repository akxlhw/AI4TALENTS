"""
OS Collection - 采集任务 CRUD 与触发创建 Mixin

后台采集执行、限流自动恢复等执行引擎逻辑位于聚合点
os_collection_service.py —— 组合服务需要在自身模块内实例化完整类，
放在本 Mixin 会形成 CollectTaskMixin -> OSCollectionService -> CollectTaskMixin
循环依赖（2026-08 审计发现，已解除）。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.domains.open_source.models.open_source import OSCollectTask
from app.domains.open_source.repositories.open_source import OpenSourceRepository


class CollectTaskMixin:
    """采集任务管理与触发创建能力。"""

    session: AsyncSession
    repo: OpenSourceRepository

    # ============= Collect Task =============

    async def list_collect_tasks(
        self, page: int = 1, page_size: int = 20
    ) -> tuple[list[OSCollectTask], int]:
        """
        获取采集任务列表

        Args:
            page: 页码
            page_size: 每页数量

        Returns:
            Tuple[List[OSCollectTask], int]: 任务列表和总数
        """
        return await self.repo.list_collect_tasks(page=page, page_size=page_size)

    async def get_collect_task(self, task_id: int) -> OSCollectTask | None:
        """
        获取采集任务详情

        Args:
            task_id: 任务ID

        Returns:
            Optional[OSCollectTask]: 任务详情或None
        """
        return await self.repo.get_collect_task(task_id)

    async def create_collect_task(
        self,
        task_name: str,
        config_json: dict[str, Any],
        created_by: int,
    ) -> OSCollectTask:
        """
        创建采集任务

        Args:
            task_name: 任务名称
            config_json: 任务配置JSON
            created_by: 创建者用户ID

        Returns:
            OSCollectTask: 创建的任务
        """
        return await self.repo.create_collect_task(
            {
                "task_name": task_name,
                "config_json": config_json,
                "created_by": created_by,
            }
        )

    async def cancel_collect_task(self, task_id: int) -> OSCollectTask | None:
        """
        取消采集任务

        Args:
            task_id: 任务ID

        Returns:
            Optional[OSCollectTask]: 取消后的任务或None

        Raises:
            ValueError: 任务状态不允许取消
        """
        task = await self.repo.get_collect_task(task_id)
        if not task:
            return None
        if task.status not in ("pending", "running"):
            raise BadRequestError(f"Cannot cancel task in status: {task.status}")

        return await self.repo.cancel_collect_task(task_id)

    async def delete_collect_task(self, task_id: int) -> bool:
        """删除采集任务记录.

        与学术域保持一致：running / pending 状态的任务不允许删除。
        """
        task = await self.repo.get_collect_task(task_id)
        if task is None:
            return False

        if task.status in ("pending", "running"):
            raise BadRequestError("Cannot delete running or pending task")

        return await self.repo.delete_collect_task(task_id)

    async def collect_single_repo(
        self,
        repo_config_id: int,
        contributors_per_repo: int,
        created_by: int,
    ) -> tuple[OSCollectTask, str, str]:
        """
        为单个仓库创建采集任务

        Args:
            repo_config_id: 仓库配置ID
            contributors_per_repo: 每个仓库采集的contributor数量
            created_by: 创建者用户ID

        Returns:
            Tuple[OSCollectTask, str, str]: 任务、repo_full_name、tech_element

        Raises:
            ValueError: 配置不存在、采集未启用、或已有运行中任务
        """
        config = await self.repo.get_repo_config(repo_config_id)
        if not config:
            raise NotFoundError("Repo config")
        if not config.collect_enabled:
            raise BadRequestError("Repository collection is disabled")

        existing = await self.repo.get_active_collect_task(config.repo_full_name)
        if existing:
            raise ConflictError("A collection task is already running for this repository")

        task = await self.repo.create_collect_task(
            {
                "task_name": config.repo_full_name,
                "status": "pending",
                "config_json": {
                    "repo_config_id": repo_config_id,
                    "repo_full_name": config.repo_full_name,
                    "tech_element": config.tech_element,
                    "contributors_per_repo": contributors_per_repo,
                },
                "created_by": created_by,
            }
        )
        return task, config.repo_full_name, config.tech_element

    async def collect_batch_repos(
        self,
        repo_config_ids: list[int],
        contributors_per_repo: int,
        created_by: int,
    ) -> tuple[list[OSCollectTask], list[dict[str, Any]]]:
        """
        批量为多个仓库创建采集任务

        Args:
            repo_config_ids: 仓库配置ID列表
            contributors_per_repo: 每个仓库采集的contributor数量
            created_by: 创建者用户ID

        Returns:
            Tuple[List[OSCollectTask], List[dict]]: 成功创建的任务列表、跳过的记录列表
        """
        created_tasks: list[OSCollectTask] = []
        skipped: list[dict[str, Any]] = []

        for repo_config_id in repo_config_ids:
            config = await self.repo.get_repo_config(repo_config_id)
            if not config:
                skipped.append(
                    {
                        "repo_config_id": repo_config_id,
                        "repo_full_name": None,
                        "reason": "Repo config not found",
                    }
                )
                continue
            if not config.collect_enabled:
                skipped.append(
                    {
                        "repo_config_id": repo_config_id,
                        "repo_full_name": config.repo_full_name,
                        "reason": "Repository collection is disabled",
                    }
                )
                continue

            existing = await self.repo.get_active_collect_task(config.repo_full_name)
            if existing:
                skipped.append(
                    {
                        "repo_config_id": repo_config_id,
                        "repo_full_name": config.repo_full_name,
                        "reason": "A collection task is already running for this repository",
                    }
                )
                continue

            task = await self.repo.create_collect_task(
                {
                    "task_name": config.repo_full_name,
                    "status": "pending",
                    "config_json": {
                        "repo_config_id": repo_config_id,
                        "repo_full_name": config.repo_full_name,
                        "tech_element": config.tech_element,
                        "contributors_per_repo": contributors_per_repo,
                    },
                    "created_by": created_by,
                }
            )
            created_tasks.append(task)

        return created_tasks, skipped
