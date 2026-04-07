"""
Repository for collect configuration operations - Simplified for MVP v1.1
采集配置数据访问层 - 简化版

采集逻辑简化：
- 移除 Scope 和 Strategy 概念
- 任务直接关联技术要素
- 数据类型固定：学者+论文+机构
- 时间范围固定：2010.1.1至今
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.sync import CollectTask
from app.models.tech_element import TechElement


class CollectTaskRepository:
    """Repository for CollectTask operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_tasks(
        self,
        status: str | None = None,
        tech_element_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[CollectTask], int]:
        """List collect tasks with pagination."""
        query = select(CollectTask).options(selectinload(CollectTask.tech_element))

        if status:
            query = query.where(CollectTask.status == status)
        if tech_element_id:
            query = query.where(CollectTask.tech_element_id == tech_element_id)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Paginate
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size).order_by(CollectTask.task_id.desc())

        result = await self.session.execute(query)
        tasks = list(result.scalars().all())

        return tasks, total

    async def get_by_id(self, task_id: int) -> CollectTask | None:
        """Get collect task by ID."""
        result = await self.session.execute(
            select(CollectTask)
            .options(selectinload(CollectTask.tech_element))
            .where(CollectTask.task_id == task_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, task_code: str) -> CollectTask | None:
        """Get collect task by code."""
        result = await self.session.execute(
            select(CollectTask).where(CollectTask.task_code == task_code)
        )
        return result.scalar_one_or_none()

    async def create_task(
        self,
        task_code: str,
        tech_element_id: int,
        collect_mode: str,
        triggered_by: int | None = None,
        time_window_start: datetime | None = None,
        time_window_end: datetime | None = None,
    ) -> CollectTask:
        """Create a new collect task."""
        task = CollectTask(
            task_code=task_code,
            tech_element_id=tech_element_id,
            collect_mode=collect_mode,
            task_type="manual",  # 兼容旧字段
            triggered_by=triggered_by,
            triggered_at=datetime.utcnow(),
            status="pending",
            time_window_start=time_window_start,
            time_window_end=time_window_end,
        )
        self.session.add(task)
        await self.session.flush()
        return task

    async def update_task_status(
        self,
        task_id: int,
        status: str,
        progress_percent: int | None = None,
        current_step: str | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        error_message: str | None = None,
        error_details: dict | None = None,
    ) -> CollectTask | None:
        """Update task status and progress."""
        task = await self.get_by_id(task_id)
        if not task:
            return None

        task.status = status
        if progress_percent is not None:
            task.progress_percent = progress_percent
        if current_step is not None:
            task.current_step = current_step
        if started_at is not None:
            task.started_at = started_at
        if completed_at is not None:
            task.completed_at = completed_at
        if error_message is not None:
            task.error_message = error_message
        if error_details is not None:
            task.error_details = error_details

        return task

    async def update_task_counts(
        self,
        task_id: int,
        total_records: int | None = None,
        processed_records: int | None = None,
        success_records: int | None = None,
        failed_records: int | None = None,
        skipped_records: int | None = None,
    ) -> CollectTask | None:
        """Update task record counts."""
        task = await self.get_by_id(task_id)
        if not task:
            return None

        if total_records is not None:
            task.total_records = total_records
        if processed_records is not None:
            task.processed_records = processed_records
        if success_records is not None:
            task.success_records = success_records
        if failed_records is not None:
            task.failed_records = failed_records
        if skipped_records is not None:
            task.skipped_records = skipped_records

        return task

    async def complete_task(
        self,
        task_id: int,
        success: bool,
        result_summary: dict | None = None,
        error_message: str | None = None,
    ) -> CollectTask | None:
        """Mark task as completed."""
        task = await self.get_by_id(task_id)
        if not task:
            return None

        task.status = "completed" if success else "failed"
        task.completed_at = datetime.utcnow()
        task.progress_percent = 100

        if result_summary:
            task.result_summary = result_summary
        if error_message:
            task.error_message = error_message

        return task

    async def get_active_tasks(self) -> list[CollectTask]:
        """Get all currently active (pending or running) tasks."""
        result = await self.session.execute(
            select(CollectTask).where(
                CollectTask.status.in_(["pending", "running"])
            ).order_by(CollectTask.task_id)
        )
        return list(result.scalars().all())


class TechElementCollectRepository:
    """Repository for TechElement collect configuration."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_with_collect_config(self) -> list[TechElement]:
        """List all tech elements with their collect configuration."""
        result = await self.session.execute(
            select(TechElement)
            .where(TechElement.is_enabled.is_(True))
            .order_by(TechElement.sort_order)
        )
        return list(result.scalars().all())

    async def get_by_id(self, tech_element_id: int) -> TechElement | None:
        """Get tech element by ID."""
        result = await self.session.execute(
            select(TechElement).where(TechElement.tech_element_id == tech_element_id)
        )
        return result.scalar_one_or_none()

    async def update_last_collect_time(
        self,
        tech_element_id: int,
        collect_at: datetime | None = None,
    ) -> TechElement | None:
        """Update last collect time for a tech element."""
        element = await self.get_by_id(tech_element_id)
        if not element:
            return None

        element.last_collect_at = collect_at or datetime.utcnow()
        return element
