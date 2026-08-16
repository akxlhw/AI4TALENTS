"""
OS Collection - 采集任务触发与后台执行 Mixin

从 os_collection_service.py 拆出：采集任务 CRUD、单仓/批量采集触发、
后台采集执行（含取消监听、限流快速失败、按仓库串行锁）。
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.domains.open_source.models.open_source import OSCollectTask
from app.domains.open_source.repositories.open_source import OpenSourceRepository
from app.domains.open_source.services.os_collection_common import _get_repo_lock

logger = logging.getLogger(__name__)


class CollectTaskMixin:
    """采集任务管理与触发能力。"""

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

    # ============= Background Collection =============

    async def run_repo_collection_background(
        self,
        task_id: int,
        repo_config_id: int,
        repo_full_name: str,
        tech_element: list[str] | str,
        contributors_per_repo: int,
    ) -> None:
        """Run single-repo collection in background.

        Encapsulates GitHubClient + GitHubCollector lifecycle.
        """
        from app.domains.open_source.services.background_state import cancelled_task_ids
        from app.domains.open_source.services.collectors.github_collector import (
            CollectContext,
            GitHubCollector,
        )
        from app.domains.open_source.services.github_client import (
            GitHubClient,
            RateLimitExhaustedError,
        )
        from app.domains.open_source.services.os_collection_service import OSCollectionService
        from app.domains.shared.services.config_service import ConfigService

        try:
            # Serialize per repository: same repo runs one collection at a
            # time, different repos run in parallel.
            repo_lock = await _get_repo_lock(repo_full_name)
            async with repo_lock:
                async with AsyncSessionLocal() as session:
                    inner_service = OSCollectionService(session)
                    task = await inner_service.get_collect_task(task_id)
                    if not task or task.status != "pending":
                        return
                    task.status = "running"
                    task.started_at = datetime.now(timezone.utc).replace(tzinfo=None)
                    await session.commit()

                    config_service = ConfigService(session)
                    github_config = await config_service.get_github_config()
                    token = github_config.tokens if github_config.tokens else None

                ctx = CollectContext(
                    task_id=task_id,
                    repo_config_id=repo_config_id,
                    repo_full_name=repo_full_name,
                    tech_element=tech_element,
                    contributors_per_repo=contributors_per_repo,
                )

                async def _watch_cancel() -> None:
                    while not ctx.cancelled.is_set():
                        await asyncio.sleep(1)
                        if task_id in cancelled_task_ids:
                            ctx.cancelled.set()
                            break

                async with GitHubClient(token=token) as client:
                    collector = GitHubCollector(client)
                    collect_task = asyncio.create_task(collector.collect(ctx))
                    watch_task = asyncio.create_task(_watch_cancel())
                    done, pending = await asyncio.wait(
                        [collect_task, watch_task],
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                    for t in pending:
                        t.cancel()
                    if collect_task in done:
                        await collect_task

        except asyncio.CancelledError:
            logger.info(f"Task {task_id} cancelled")
            async with AsyncSessionLocal() as session:
                inner_service = OSCollectionService(session)
                task = await inner_service.get_collect_task(task_id)
                if task:
                    task.status = "cancelled"
                    await session.commit()
        except RateLimitExhaustedError as e:
            # Fast-fail path: token pool exhausted. Mark the task rate_limited
            # with resume_at = now + retry_after; a background loop restarts
            # it automatically once the reset window passes (manual re-trigger
            # also works since rate_limited is not pending/running).
            logger.warning(f"Task {task_id} rate-limited: {e}")
            async with AsyncSessionLocal() as session:
                inner_service = OSCollectionService(session)
                task = await inner_service.get_collect_task(task_id)
                if task:
                    task.status = "rate_limited"  # type: ignore[assignment]
                    task.current_step = "rate_limited"  # type: ignore[assignment]
                    retry_after = e.retry_after or 3600
                    task.resume_at = datetime.now(timezone.utc).replace(  # type: ignore[assignment]
                        tzinfo=None
                    ) + timedelta(seconds=retry_after)
                    task.error_message = (  # type: ignore[assignment]
                        f"GitHub rate limit exhausted for all tokens; "
                        f"retry after {retry_after}s"
                    )[: settings.COLLECT_ERROR_MAX_LENGTH]
                    await session.commit()
        except Exception as e:
            logger.exception(f"Task {task_id} failed: {e}")
            async with AsyncSessionLocal() as session:
                inner_service = OSCollectionService(session)
                task = await inner_service.get_collect_task(task_id)
                if task:
                    task.status = "failed"
                    task.error_message = str(e)[: settings.COLLECT_ERROR_MAX_LENGTH]
                    await session.commit()
        finally:
            cancelled_task_ids.discard(task_id)

    # ============= Rate-limit Auto-resume =============

    async def resume_due_rate_limited_tasks(self) -> int:
        """Restart rate_limited tasks whose reset window has passed.

        Called periodically by ``rate_limit_resume_loop``. Returns the number
        of tasks resumed.
        """
        from sqlalchemy import select

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        result = await self.session.execute(
            select(OSCollectTask).where(
                OSCollectTask.status == "rate_limited",
                OSCollectTask.resume_at.is_not(None),
                OSCollectTask.resume_at <= now,
            )
        )
        due = result.scalars().all()
        if not due:
            return 0

        launch: list[tuple[int, dict[str, Any]]] = []
        for task in due:
            cfg: dict[str, Any] = dict(task.config_json or {})
            task.status = "pending"  # type: ignore[assignment]
            task.resume_at = None  # type: ignore[assignment]
            task.error_message = None  # type: ignore[assignment]
            launch.append((cast(int, task.task_id), cfg))
        await self.session.commit()

        for task_id, cfg in launch:
            logger.info(f"Auto-resuming rate-limited task {task_id}")
            asyncio.create_task(
                self.run_repo_collection_background(
                    task_id=task_id,
                    repo_config_id=cast(int, cfg.get("repo_config_id")),
                    repo_full_name=cfg.get("repo_full_name") or "",
                    tech_element=cfg.get("tech_element") or [],
                    contributors_per_repo=cfg.get("contributors_per_repo") or 0,
                )
            )
        return len(launch)


async def rate_limit_resume_loop(interval_seconds: int = 60) -> None:
    """Background loop: auto-resume rate_limited tasks past their resume_at.

    Started from the application lifespan; cancelled on shutdown.
    """
    from app.domains.open_source.services.os_collection_service import OSCollectionService

    while True:
        await asyncio.sleep(interval_seconds)
        try:
            async with AsyncSessionLocal() as session:
                service = OSCollectionService(session)
                resumed = await service.resume_due_rate_limited_tasks()
                if resumed:
                    logger.info(f"Rate-limit resume loop restarted {resumed} task(s)")
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("rate_limit_resume_loop iteration failed")
