"""
Collect service layer.
采集任务业务逻辑层
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.academic.models.sync import CollectTask
from app.domains.academic.models.venue import VenueSubTask
from app.domains.academic.repositories.collect_repository import (
    CollectTaskRepository,
    TechDomainCollectRepository,
)
from app.domains.academic.repositories.venue_repository import (
    VenueSubTaskRepository,
    VenueTechBindingRepository,
)


class CollectService:
    """Service for collect task operations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.task_repo = CollectTaskRepository(session)
        self.domain_repo = TechDomainCollectRepository(session)
        self.sub_task_repo = VenueSubTaskRepository(session)
        self.binding_repo = VenueTechBindingRepository(session)

    async def create_task_with_subtasks(
        self,
        tech_domain_id: int,
        user_id: int,
        time_window_start: datetime,
        time_window_end: datetime,
    ) -> CollectTask:
        """
        Create a collect task with venue sub-tasks.

        Args:
            tech_domain_id: Tech domain ID
            user_id: User ID who triggered the task
            time_window_start: Start of time window
            time_window_end: End of time window

        Returns:
            Created CollectTask
        """
        # Generate unique task code
        task_code = (
            f"COLLECT-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
        )

        # Create task
        task = await self.task_repo.create_task(
            task_code=task_code,
            tech_domain_id=tech_domain_id,
            collect_mode="full",
            triggered_by=user_id,
            time_window_start=time_window_start,
            time_window_end=time_window_end,
        )

        # Set initial status
        task.status = "pending"
        task.current_step = "等待执行"

        # Get venue bindings for this tech domain
        bindings = await self.binding_repo.get_by_tech_domain(tech_domain_id, is_enabled=True)

        # Save venue snapshot
        task.venue_snapshot = [
            {"id": b.venue.venue_code, "name": b.venue.venue_name, "type": b.venue.venue_type}
            for b in bindings
            if b.venue
        ]

        # Create sub-tasks for each venue binding
        for binding in bindings:
            sub_task = VenueSubTask(
                task_id=task.task_id,
                venue_id=binding.venue_id,
                status="pending",
                time_window_start=time_window_start,
                time_window_end=time_window_end,
            )
            await self.sub_task_repo.create(sub_task)

        await self.session.commit()
        return task

    async def cancel_task(self, task_id: int) -> bool:
        """
        Cancel a running task.

        Args:
            task_id: Task ID

        Returns:
            True if cancelled, False if task not found
        """
        task = await self.task_repo.get_by_id(task_id)
        if not task:
            return False

        task.status = "cancelled"
        task.completed_at = datetime.utcnow()
        task.current_step = "已取消"

        await self.session.commit()
        return True

    async def delete_task(self, task_id: int) -> bool:
        """
        Delete a completed task record.

        Args:
            task_id: Task ID

        Returns:
            True if deleted, False if task not found
        """
        task = await self.task_repo.get_by_id(task_id)
        if not task:
            return False

        # Clear foreign key references and delete
        await self.task_repo.cleanup_task_references(task_id)
        await self.session.commit()
        return True

    async def retry_sub_task(self, task_id: int, sub_task_id: int) -> bool:
        """
        Reset a failed sub-task for retry.

        Args:
            task_id: Task ID
            sub_task_id: Sub-task ID

        Returns:
            True if reset, False if not found or not failed
        """
        sub_task = await self.sub_task_repo.get_by_id(sub_task_id)
        if not sub_task or sub_task.task_id != task_id:
            return False

        if sub_task.status != "failed":
            return False

        await self.sub_task_repo.update_status(sub_task_id, "pending")
        await self.session.commit()
        return True
