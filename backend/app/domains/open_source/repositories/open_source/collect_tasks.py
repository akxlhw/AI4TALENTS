"""
Open Source Repository - collect tasks queries.

Split from core.py; methods are mixed into OpenSourceCoreRepository.
"""

from __future__ import annotations

from typing import Any
from typing import cast as tcast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.open_source.models.open_source import (
    OSCollectTask,
)


class CollectTasksMixin:
    """Collect task CRUD operations."""

    session: AsyncSession

    async def list_collect_tasks(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[OSCollectTask], int]:
        """List collect tasks with pagination."""
        stmt = select(OSCollectTask).order_by(OSCollectTask.created_at.desc())
        total = await self.session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_collect_task(
        self,
        task_id: int,
    ) -> OSCollectTask | None:
        """Get collect task by ID."""
        result = await self.session.execute(
            select(OSCollectTask).where(OSCollectTask.task_id == task_id)
        )
        return tcast(OSCollectTask | None, result.scalar_one_or_none())

    async def create_collect_task(
        self,
        data: dict[str, Any],
    ) -> OSCollectTask:
        """Create a new collect task."""
        task = OSCollectTask(**data)
        self.session.add(task)
        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def get_active_collect_task(
        self,
        repo_full_name: str,
    ) -> OSCollectTask | None:
        """Get active (pending or running) collect task by repo full name."""
        result = await self.session.execute(
            select(OSCollectTask).where(
                OSCollectTask.task_name == repo_full_name,
                OSCollectTask.status.in_(["pending", "running"]),
            )
        )
        return tcast(OSCollectTask | None, result.scalar_one_or_none())

    async def get_last_collection_status(
        self,
        repo_full_names: list[str],
    ) -> dict[str, dict[str, Any]]:
        """For each repo_full_name, return the latest non-active collection task.

        Skips pending/running tasks (those are concurrent guards, not history).
        Returns {repo_full_name: {"status": str, "completed_at": str|None, "records": int}}.
        """
        if not repo_full_names:
            return {}
        result = await self.session.execute(
            select(OSCollectTask)
            .where(
                OSCollectTask.task_name.in_(repo_full_names),
                ~OSCollectTask.status.in_(["pending", "running"]),
            )
            .order_by(OSCollectTask.created_at.desc())
        )
        rows = result.scalars().all()
        # Keep only the latest per repo (rows are already DESC by created_at)
        latest: dict[str, dict[str, Any]] = {}
        for row in rows:
            if row.task_name not in latest:
                latest[row.task_name] = {
                    "status": row.status,
                    "completed_at": (
                        row.completed_at.isoformat()
                        if row.completed_at
                        else row.created_at.isoformat() if row.created_at else None
                    ),
                    "records": row.processed_records or 0,
                }
        return latest

    async def cancel_collect_task(self, task_id: int) -> OSCollectTask | None:
        """Cancel a collect task by setting status to cancelled."""
        task = await self.get_collect_task(task_id)
        if task is None:
            return None
        task.status = tcast(Any, "cancelled")
        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def delete_collect_task(self, task_id: int) -> bool:
        """Delete a collect task permanently."""
        task = await self.get_collect_task(task_id)
        if task is None:
            return False
        await self.session.delete(task)
        await self.session.flush()
        await self.session.commit()
        return True
