"""
Collect background service.

Encapsulates background task execution for collection,
including AsyncSessionLocal usage and CollectionOrchestrator invocation.
"""

from __future__ import annotations

import logging

from app.core.database import AsyncSessionLocal
from app.domains.academic.repositories.collect_repository import CollectTaskRepository
from app.domains.academic.services.collect.orchestrator import CollectionOrchestrator
from app.domains.academic.services.data_fetchers import (
    AuthorFetcher,
    InstitutionFetcher,
    WorkFetcher,
)

logger = logging.getLogger(__name__)


class CollectBackgroundService:
    """Service for running collect tasks in the background."""

    async def start_task_if_pending(self, task_id: int) -> None:
        """Update task status to running if it is currently pending."""
        async with AsyncSessionLocal() as session:
            repo = CollectTaskRepository(session)
            task = await repo.get_by_id(task_id)
            if task and task.status == "pending":
                await repo.start_task_and_commit(task_id)
                logger.info(f"Task {task_id} status updated to running")

    async def fail_task_if_running(self, task_id: int, error_message: str) -> None:
        """Update task status to failed if it is currently running."""
        async with AsyncSessionLocal() as session:
            repo = CollectTaskRepository(session)
            task = await repo.get_by_id(task_id)
            if task and task.status == "running":
                await repo.fail_task_and_commit(task_id, error_message)
                logger.error(f"Task {task_id} marked as failed: {error_message}")

    async def run_unified_collect(self, task_id: int):
        """Execute the full collection pipeline for a task."""
        async with AsyncSessionLocal() as session:
            work_fetcher = WorkFetcher(session)
            author_fetcher = AuthorFetcher(session)
            institution_fetcher = InstitutionFetcher(session)

            orchestrator = CollectionOrchestrator(
                session,
                work_fetcher=work_fetcher,
                author_fetcher=author_fetcher,
                institution_fetcher=institution_fetcher,
            )
            return await orchestrator.execute_task(task_id)
