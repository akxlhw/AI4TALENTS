"""
OS Collection Service - 开源人才仓库采集业务逻辑层

从 OpenSourceService 中提取的采集相关方法，包括：
- 仓库配置 CRUD (list_repo_configs, get_repo_config, create_repo_config, update_repo_config, delete_repo_config)
- 采集任务 CRUD (list_collect_tasks, get_collect_task, create_collect_task, cancel_collect_task, delete_collect_task)
- 采集触发 (collect_single_repo, collect_batch_repos)
- 后台采集执行 (run_repo_collection_background)

遵循架构规范：Endpoint -> Service -> Repository
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any
from typing import cast as tcast

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.domains.open_source.models.open_source import (
    OSCollectTask,
    OSRepoConfig,
)
from app.domains.open_source.repositories.open_source import OpenSourceRepository
from app.domains.open_source.schemas.open_source import OSPurgePreview

logger = logging.getLogger(__name__)

# Regex to extract owner/repo from various GitHub URL formats or plain owner/repo
_REPO_URL_RE = re.compile(
    r"(?:https?://github\.com/)?"  # optional URL prefix
    r"([\w.-]+)/([\w.-]+?)"  # owner/repo (non-greedy repo to allow trailing path)
    r"(?:\.git)?(?:/.*)?$"  # optional .git suffix and/or trailing path (/tree/main, /blob/...)
)


def parse_repo_input(raw: str) -> str | None:
    """Parse a user-provided repo input into 'owner/repo' format.

    Accepts:
      https://github.com/owner/repo
      https://github.com/owner/repo.git
      https://github.com/owner/repo/tree/main
      owner/repo
      owner/repo.git

    Returns 'owner/repo' or None if the input cannot be parsed.
    """
    raw = raw.strip()
    if not raw:
        return None
    m = _REPO_URL_RE.match(raw)
    if m:
        return f"{m.group(1)}/{m.group(2)}"
    return None


VALID_TECH_ELEMENTS = {"ai", "robotics", "data_science", "networks", "systems", "security"}
REPO_FULL_NAME_PATTERN = re.compile(r"^[\w.-]+/[\w.-]+$")

# Per-repository collection locks: the same repo collects serially, different
# repos may run in parallel. (Previously a single global Semaphore(1) forced
# all collections to serialize; combined with in-request rate-limit sleeps
# that deadlocked the whole pipeline. Rate-limit waits now fail fast, so
# parallel repos are safe — the token pool itself throttles aggregate load.)
_REPO_LOCKS: dict[str, asyncio.Lock] = {}
_REPO_LOCKS_GUARD = asyncio.Lock()


async def _get_repo_lock(repo_full_name: str) -> asyncio.Lock:
    """Get (or create) the lock serializing collection of one repository."""
    async with _REPO_LOCKS_GUARD:
        lock = _REPO_LOCKS.get(repo_full_name)
        if lock is None:
            lock = asyncio.Lock()
            _REPO_LOCKS[repo_full_name] = lock
        return lock


class OSCollectionService:
    """
    开源采集服务 - 封装仓库采集相关的业务逻辑

    职责：
    - 仓库配置管理
    - 采集任务管理
    - 采集触发与后台执行
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = OpenSourceRepository(session)

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
        """
        创建仓库配置

        Args:
            repo_full_name: GitHub 仓库全名，如 'pytorch/pytorch'
            tech_element: 技术要素编码
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
        if tech_element not in VALID_TECH_ELEMENTS:
            raise BadRequestError(
                f"Invalid tech_element: {tech_element}. Must be one of: {', '.join(sorted(VALID_TECH_ELEMENTS))}"
            )

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
                "tech_element": tech_element,
                "display_name": display_name or repo_full_name.split("/")[-1],
                "description": description,
                "tech_direction_id": tech_direction_id,
                "language": language,
                "notes": notes,
                "created_by": created_by,
                "stars_count": stars_count,
            }
        )

    async def batch_create_repo_configs(
        self,
        repo_inputs: list[str],
        tech_element: str,
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

        if tech_element not in VALID_TECH_ELEMENTS:
            raise BadRequestError(
                f"Invalid tech_element: {tech_element}. Must be one of: {', '.join(sorted(VALID_TECH_ELEMENTS))}"
            )

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
                        "tech_element": tech_element,
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
        if "tech_element" in update_data and update_data["tech_element"] not in VALID_TECH_ELEMENTS:
            raise BadRequestError("Invalid tech_element")

        return await self.repo.update_repo_config(repo_config_id, update_data)

    async def delete_repo_config(self, repo_config_id: int) -> bool:
        """
        删除仓库配置

        Args:
            repo_config_id: 配置ID

        Returns:
            bool: 是否删除成功
        """
        return await self.repo.delete_repo_config(repo_config_id)

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
        tech_element: str,
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
            # (terminal, retryable — not pending/running, so the user can
            # re-trigger collection once the reset window passes) and record
            # retry_after instead of blocking the pipeline.
            logger.warning(f"Task {task_id} rate-limited: {e}")
            async with AsyncSessionLocal() as session:
                inner_service = OSCollectionService(session)
                task = await inner_service.get_collect_task(task_id)
                if task:
                    task.status = "rate_limited"  # type: ignore[assignment]
                    task.current_step = "rate_limited"  # type: ignore[assignment]
                    task.error_message = (  # type: ignore[assignment]
                        f"GitHub rate limit exhausted for all tokens; "
                        f"retry after {e.retry_after}s"
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
