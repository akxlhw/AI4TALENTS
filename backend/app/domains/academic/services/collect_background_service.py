"""
Collect background service.

Encapsulates background task execution for collection,
including AsyncSessionLocal usage and CollectionOrchestrator invocation.
"""

from __future__ import annotations

import logging

from app.core.database import AsyncSessionLocal
from app.domains.academic.repositories.collect_repository import CollectTaskRepository
from app.domains.academic.repositories.venue_repository import VenueSubTaskRepository
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

    async def run_single_sub_task(self, task_id: int, sub_task_id: int) -> None:
        """Re-execute a single venue sub-task (e.g. after a failure retry)."""
        from app.domains.academic.models.sync import CollectTask
        from app.domains.academic.services.collect.venue_executor import VenueSubTaskExecutor

        async with AsyncSessionLocal() as session:
            from sqlalchemy import select

            task_result = await session.execute(
                select(CollectTask).where(CollectTask.task_id == task_id)
            )
            task = task_result.scalar_one_or_none()
            if not task:
                logger.error(f"Task {task_id} not found for sub-task retry")
                return

            work_fetcher = WorkFetcher(session)
            executor = VenueSubTaskExecutor(session, work_fetcher)

            sub_task_repo = VenueSubTaskRepository(session)
            sub_task = await sub_task_repo.get_by_id(sub_task_id)
            if not sub_task:
                logger.error(f"Sub-task {sub_task_id} not found")
                return

            try:
                works_fetched = await executor.execute(task, sub_task, type("P", (), {})())
                logger.info(
                    f"Sub-task {sub_task_id} retry completed: {works_fetched} works fetched"
                )
                await session.commit()
            except Exception as e:
                logger.error(f"Sub-task {sub_task_id} retry failed: {e}")
                await sub_task_repo.update_status(sub_task_id, "failed", error_message=str(e))
                await session.commit()
