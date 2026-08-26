"""
OS Collection Service - 开源人才仓库采集业务逻辑层（门面聚合）

实现按职能拆分为同目录 Mixin 模块，本文件聚合为原 OSCollectionService：
- os_repo_config_mixin.py: 仓库配置 CRUD（含 tech_element 校验）
- os_collect_task_mixin.py: 采集任务 CRUD 与采集触发创建
- os_batch_ops_mixin.py: 批量操作（batch create、batch tech_element、purge）
- os_tech_tag_sync_mixin.py: 开发者技术标签同步
- os_collection_common.py: 仓库输入解析与按仓库串行锁

后台采集执行引擎（run_repo_collection_background / resume_due_rate_limited_tasks /
rate_limit_resume_loop）直接定义在本聚合模块：这些代码需要以新会话实例化
"完整组装后的服务类"，放在任何 Mixin 里都会形成
Mixin -> OSCollectionService -> Mixin 循环依赖（2026-08 审计发现，已解除）。

公共接口（OSCollectionService、parse_repo_input、REPO_FULL_NAME_PATTERN、
_get_repo_lock）经本模块 re-export 保持，调用方零改动。

遵循架构规范：Endpoint -> Service -> Repository
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.domains.open_source.services.background_state as background_state
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.domains.open_source.models.open_source import OSCollectTask
from app.domains.open_source.repositories.open_source import OpenSourceRepository
from app.domains.open_source.services.collectors.github_collector import (
    CollectContext,
    GitHubCollector,
)
from app.domains.open_source.services.github_client import (
    GitHubClient,
    RateLimitExhaustedError,
)
from app.domains.open_source.services.os_batch_ops_mixin import BatchOpsMixin
from app.domains.open_source.services.os_collect_task_mixin import CollectTaskMixin
from app.domains.open_source.services.os_collection_common import (
    _REPO_LOCKS,
    REPO_FULL_NAME_PATTERN,
    _get_collect_semaphore,
    _get_repo_lock,
    parse_repo_input,
)
from app.domains.shared.services.common.circuit_breaker import CircuitBreakerOpenError
from app.domains.shared.services.config_service import ConfigService

logger = logging.getLogger(__name__)

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
    - 采集任务管理、采集触发创建（CollectTaskMixin）
    - 后台采集执行与限流自动恢复（本模块定义）
    - 批量操作与数据清理（BatchOpsMixin）
    - 开发者技术标签同步（TechTagSyncMixin）
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = OpenSourceRepository(session)

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
        try:
            # Global concurrency cap: at most OS_COLLECT_MAX_CONCURRENT
            # collections run at once; extra batch tasks wait here in
            # "pending" until a slot frees (each running task owns a
            # GitHubClient + DB session, so unbounded parallelism trips
            # GitHub abuse detection).
            collect_sem = await _get_collect_semaphore()
            async with collect_sem:
                # Token-pool circuit breaker: if another task already
                # discovered that ALL tokens are exhausted, skip straight to
                # rate_limited instead of waking a fresh GitHubClient to
                # re-discover the exhaustion by failing (tokens are
                # account-scoped, but each task's client tracks them
                # privately — this check is what makes that knowledge global).
                if background_state.is_token_pool_exhausted():
                    resume_at = datetime.fromtimestamp(
                        background_state.token_pool_resume_at or 0, tz=timezone.utc
                    ).replace(tzinfo=None)
                    async with AsyncSessionLocal() as session:
                        inner_service = OSCollectionService(session)
                        task = await inner_service.get_collect_task(task_id)
                        if task and task.status == "pending":
                            task.status = "rate_limited"  # type: ignore[assignment]
                            task.current_step = "rate_limited"  # type: ignore[assignment]
                            task.resume_at = resume_at  # type: ignore[assignment]
                            task.error_message = (  # type: ignore[assignment]
                                "Token pool exhausted (circuit breaker); auto-resume scheduled"
                            )[: settings.COLLECT_ERROR_MAX_LENGTH]
                            await session.commit()
                            logger.info(
                                f"Task {task_id} deferred by token-pool breaker "
                                f"(resume_at={resume_at})"
                            )
                    return

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
                            if task_id in background_state.cancelled_task_ids:
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
                            # The collector writes single-repo tech_tags during
                            # contributor upserts; recompute the union across ALL
                            # configured repos so multi-repo tags survive a
                            # re-collection. Best-effort: the task result above
                            # stands even if this normalization fails.
                            try:
                                async with AsyncSessionLocal() as session:
                                    inner_service = OSCollectionService(session)
                                    await inner_service.sync_developer_tech_tags(repo_full_name)
                                    await session.commit()
                            except Exception:
                                logger.exception(
                                    f"Post-collection tech tag union sync failed "
                                    f"for {repo_full_name}"
                                )

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
            retry_after = e.retry_after or 3600
            # Open the global breaker so QUEUED tasks (still waiting on the
            # semaphore) defer instead of re-discovering the exhaustion.
            background_state.mark_token_pool_exhausted(retry_after)
            async with AsyncSessionLocal() as session:
                inner_service = OSCollectionService(session)
                task = await inner_service.get_collect_task(task_id)
                if task:
                    task.status = "rate_limited"  # type: ignore[assignment]
                    task.current_step = "rate_limited"  # type: ignore[assignment]
                    task.resume_at = datetime.now(timezone.utc).replace(  # type: ignore[assignment]
                        tzinfo=None
                    ) + timedelta(seconds=retry_after)
                    task.error_message = (  # type: ignore[assignment]
                        f"GitHub rate limit exhausted for all tokens; "
                        f"retry after {retry_after}s"
                    )[: settings.COLLECT_ERROR_MAX_LENGTH]
                    await session.commit()
        except CircuitBreakerOpenError as e:
            # Transport circuit breaker OPEN (upstream connectivity failure).
            # Same deferral contract as rate-limit: mark rate_limited with
            # resume_at just past the breaker's recovery window; the resume
            # loop restarts it automatically. Queued tasks re-discover the
            # OPEN state instantly (fail-fast, no HTTP traffic) and defer the
            # same way, so a transient outage no longer kills a whole batch.
            logger.warning(f"Task {task_id} deferred by circuit breaker: {e}")
            retry_after = int(settings.CIRCUIT_BREAKER_RECOVERY_TIMEOUT) + 5
            async with AsyncSessionLocal() as session:
                inner_service = OSCollectionService(session)
                task = await inner_service.get_collect_task(task_id)
                if task:
                    task.status = "rate_limited"  # type: ignore[assignment]
                    task.current_step = "rate_limited"  # type: ignore[assignment]
                    task.resume_at = datetime.now(timezone.utc).replace(  # type: ignore[assignment]
                        tzinfo=None
                    ) + timedelta(seconds=retry_after)
                    task.error_message = (  # type: ignore[assignment]
                        "GitHub circuit breaker OPEN (upstream connectivity); "
                        f"auto-resume in {retry_after}s"
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
            background_state.cancelled_task_ids.discard(task_id)

    # ============= Rate-limit Auto-resume =============

    async def resume_due_rate_limited_tasks(self) -> int:
        """Restart rate_limited tasks whose reset window has passed.

        Called periodically by ``rate_limit_resume_loop``. Returns the number
        of tasks resumed.
        """
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
            # Nothing to resume — close the breaker if its window has passed
            # so new triggers don't get deferred by a stale timestamp.
            if (
                background_state.token_pool_resume_at is not None
                and time.time() >= background_state.token_pool_resume_at
            ):
                background_state.clear_token_pool_breaker()
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
