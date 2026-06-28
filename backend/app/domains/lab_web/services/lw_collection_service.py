"""Collection orchestration: the entry point endpoints call.

Creates a task, then runs the lab's collector in the background. Collector
classes are loaded dynamically from lw_lab_registry.collector_class.
"""

from __future__ import annotations

import asyncio
import importlib
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.domains.lab_web.models.lab_web import LWCollectTask, LWLabRegistry
from app.domains.lab_web.repositories.lab_web import LWRepository
from app.domains.lab_web.services.collectors.base_collector import (
    BaseLabCollector,
    CollectContext,
)
from app.domains.lab_web.services.lw_person_service import LWPersonService

if TYPE_CHECKING:
    from app.domains.lab_web.services.collectors.scrapling_fetcher import ScraplingFetcher

logger = logging.getLogger(__name__)

# Limit concurrent lab collection tasks to be polite to target sites.
COLLECTION_SEMAPHORE = asyncio.Semaphore(int(getattr(settings, "LAB_WEB_MAX_CONCURRENT", 2)))


class LWCollectionService:
    """Orchestrates one collection run end-to-end."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = LWRepository(session)

    async def list_labs(self, only_active: bool = False) -> list[LWLabRegistry]:
        return await self.repo.list_labs(only_active=only_active)

    async def get_task_status(self, task_id: int) -> LWCollectTask | None:
        return await self.repo.get_task(task_id)

    async def cancel_collection(self, task_id: int) -> bool:
        # The cancelled Event lives in the in-memory task registry; in v1 we
        # mark the task 'cancelled' and the running loop checks DB status too.
        await self.repo.update_task(task_id, status="cancelled")
        return True

    async def start_collection(self, lab_id: int, created_by: int | None = None) -> int:
        """Create a task and launch background collection. Returns task_id."""
        lab = await self.repo.get_lab(lab_id)
        if lab is None:
            raise LookupError(f"Lab {lab_id} not found")
        if not lab.is_active:
            raise RuntimeError(f"Lab {lab.lab_code} is not active")

        task = await self.repo.create_task(
            task_name=f"lab_web_collect_{lab.lab_code}",
            lab_id=lab_id,
            status="pending",
            config_json={"fetch_mode": lab.fetch_mode},
            created_by=created_by,
        )

        # Fast-fail path for labs without a collector implementation.
        if not lab.collector_class:
            await self.repo.update_task(
                int(task.task_id),
                status="failed",
                error_message=f"Collector for lab {lab.lab_code} not implemented",
                completed_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
            return int(task.task_id)

        asyncio.create_task(self._run_collection(int(task.task_id), lab_id))
        return int(task.task_id)

    async def _run_collection(self, task_id: int, lab_id: int) -> None:
        """Background run. Uses its own session (background tasks may use
        AsyncSessionLocal, per os_collection_service precedent).

        A cancel-watcher coroutine polls task status from the DB and sets
        ctx.cancelled when a cancel request lands (POST /tasks/{id}/cancel
        flips the DB status; the collector loop checks ctx.cancelled between
        pages). Without the watcher, cancel would be a no-op on running tasks.
        """
        async with COLLECTION_SEMAPHORE:
            async with AsyncSessionLocal() as session:
                repo = LWRepository(session)
                person_service = LWPersonService(session)
                try:
                    lab = await repo.get_lab(lab_id)
                    if lab is None:
                        raise LookupError(f"Lab {lab_id} not found during run")
                    await repo.update_task(
                        task_id,
                        status="running",
                        started_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    )
                    ctx = CollectContext(task_id=task_id, lab_id=lab_id)
                    collector = self._load_collector(
                        str(lab.collector_class),
                        fetcher=_make_fetcher(str(lab.fetch_mode)),
                        lab=lab,
                        repo=repo,
                        person_service=person_service,
                    )
                    # Run collector concurrently with a cancel-watcher so that a
                    # cancel request (DB status -> 'cancelled') is observed and
                    # propagated into ctx.cancelled, stopping the scrape loop.
                    watcher = asyncio.create_task(self._watch_cancel(ctx, repo, task_id))
                    try:
                        await collector.collect(ctx)
                    finally:
                        watcher.cancel()
                        # Suppress the CancelledError from the watcher cleanup.
                        try:
                            await watcher
                        except (asyncio.CancelledError, Exception):
                            pass

                    if ctx.cancelled.is_set():
                        # Collector left status as 'cancelled'; nothing more to do.
                        return
                    await repo.update_task(
                        task_id,
                        status="success",
                        progress_percent=100,
                        completed_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    )
                    await repo.update_lab_collected_at(
                        lab_id, datetime.now(timezone.utc).replace(tzinfo=None)
                    )
                except Exception as exc:
                    logger.exception("lab_web collection failed: task=%s", task_id)
                    msg = str(exc)
                    max_len = int(getattr(settings, "COLLECT_ERROR_MAX_LENGTH", 500))
                    await repo.update_task(
                        task_id,
                        status="failed",
                        error_message=(msg[:max_len] if len(msg) > max_len else msg),
                        completed_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    )

    @staticmethod
    async def _watch_cancel(ctx: CollectContext, repo: LWRepository, task_id: int) -> None:
        """Poll task DB status; set ctx.cancelled when status becomes 'cancelled'.

        Polls every CANCEL_POLL_INTERVAL seconds. Exits when cancelled is set
        (so the collector's cooperative check unblocks quickly).
        """
        interval = float(getattr(settings, "LAB_WEB_CANCEL_POLL_INTERVAL", 2.0))
        while not ctx.cancelled.is_set():
            try:
                task = await repo.get_task(task_id)
                if task is not None and str(task.status) == "cancelled":
                    ctx.cancelled.set()
                    return
            except Exception:
                logger.warning("cancel-watch DB poll failed for task %s", task_id, exc_info=True)
            await asyncio.sleep(interval)

    @staticmethod
    def _load_collector(collector_class: str, **kwargs: object) -> BaseLabCollector:
        """Dynamically import and instantiate a collector by dotted path.

        collector_class is stored as e.g. 'labs.stanford_sail.StanfordSailCollector'
        and is resolved relative to the collectors package.
        """
        module_path, _, class_name = collector_class.rpartition(".")
        module = importlib.import_module(f"app.domains.lab_web.services.collectors.{module_path}")
        cls = getattr(module, class_name)
        return cls(**kwargs)  # type: ignore[no-any-return]


def _make_fetcher(fetch_mode: str) -> ScraplingFetcher:
    from app.domains.lab_web.services.collectors.scrapling_fetcher import ScraplingFetcher

    return ScraplingFetcher(fetch_mode=fetch_mode)
