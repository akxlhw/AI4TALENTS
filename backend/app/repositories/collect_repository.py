"""
Repository for collect configuration operations.
采集配置数据访问层
"""
from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sync import CollectScope, CollectStrategy, CollectTask


class CollectScopeRepository:
    """Repository for CollectScope operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_scopes(
        self,
        scope_type: Optional[str] = None,
        is_enabled: Optional[bool] = None,
    ) -> List[CollectScope]:
        """List all collect scopes with optional filters."""
        query = select(CollectScope)

        if scope_type:
            query = query.where(CollectScope.scope_type == scope_type)
        if is_enabled is not None:
            query = query.where(CollectScope.is_enabled == is_enabled)

        query = query.order_by(CollectScope.scope_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, scope_id: int) -> Optional[CollectScope]:
        """Get collect scope by ID."""
        result = await self.session.execute(
            select(CollectScope).where(CollectScope.scope_id == scope_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, scope_code: str) -> Optional[CollectScope]:
        """Get collect scope by code."""
        result = await self.session.execute(
            select(CollectScope).where(CollectScope.scope_code == scope_code)
        )
        return result.scalar_one_or_none()

    async def create_scope(
        self,
        scope_code: str,
        scope_name: str,
        scope_type: str,
        scope_value: List,
        description: Optional[str] = None,
        created_by: Optional[int] = None,
    ) -> CollectScope:
        """Create a new collect scope."""
        scope = CollectScope(
            scope_code=scope_code,
            scope_name=scope_name,
            scope_type=scope_type,
            scope_value=scope_value,
            description=description,
            created_by=created_by,
            is_enabled=True,
        )
        self.session.add(scope)
        await self.session.flush()
        return scope

    async def update_scope(
        self,
        scope_id: int,
        scope_name: Optional[str] = None,
        scope_value: Optional[List] = None,
        is_enabled: Optional[bool] = None,
        description: Optional[str] = None,
    ) -> Optional[CollectScope]:
        """Update collect scope."""
        scope = await self.get_by_id(scope_id)
        if not scope:
            return None

        if scope_name is not None:
            scope.scope_name = scope_name
        if scope_value is not None:
            scope.scope_value = scope_value
        if is_enabled is not None:
            scope.is_enabled = is_enabled
        if description is not None:
            scope.description = description

        return scope

    async def delete_scope(self, scope_id: int) -> bool:
        """Delete collect scope."""
        scope = await self.get_by_id(scope_id)
        if not scope:
            return False

        await self.session.delete(scope)
        return True


class CollectStrategyRepository:
    """Repository for CollectStrategy operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_strategies(
        self,
        strategy_type: Optional[str] = None,
        is_enabled: Optional[bool] = None,
    ) -> List[CollectStrategy]:
        """List all collect strategies with optional filters."""
        query = select(CollectStrategy)

        if strategy_type:
            query = query.where(CollectStrategy.strategy_type == strategy_type)
        if is_enabled is not None:
            query = query.where(CollectStrategy.is_enabled == is_enabled)

        query = query.order_by(CollectStrategy.strategy_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, strategy_id: int) -> Optional[CollectStrategy]:
        """Get collect strategy by ID."""
        result = await self.session.execute(
            select(CollectStrategy).where(CollectStrategy.strategy_id == strategy_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, strategy_code: str) -> Optional[CollectStrategy]:
        """Get collect strategy by code."""
        result = await self.session.execute(
            select(CollectStrategy).where(CollectStrategy.strategy_code == strategy_code)
        )
        return result.scalar_one_or_none()

    async def create_strategy(
        self,
        strategy_code: str,
        strategy_name: str,
        strategy_type: str,
        data_types: List[str],
        scope_ids: Optional[List[int]] = None,
        schedule_cron: Optional[str] = None,
        fetch_config: Optional[dict] = None,
        description: Optional[str] = None,
        created_by: Optional[int] = None,
    ) -> CollectStrategy:
        """Create a new collect strategy."""
        strategy = CollectStrategy(
            strategy_code=strategy_code,
            strategy_name=strategy_name,
            strategy_type=strategy_type,
            schedule_cron=schedule_cron,
            scope_ids=scope_ids,
            data_types=data_types,
            fetch_config=fetch_config,
            description=description,
            created_by=created_by,
            is_enabled=True,
        )
        self.session.add(strategy)
        await self.session.flush()
        return strategy

    async def update_strategy(
        self,
        strategy_id: int,
        strategy_name: Optional[str] = None,
        scope_ids: Optional[List[int]] = None,
        data_types: Optional[List[str]] = None,
        schedule_cron: Optional[str] = None,
        fetch_config: Optional[dict] = None,
        is_enabled: Optional[bool] = None,
        description: Optional[str] = None,
    ) -> Optional[CollectStrategy]:
        """Update collect strategy."""
        strategy = await self.get_by_id(strategy_id)
        if not strategy:
            return None

        if strategy_name is not None:
            strategy.strategy_name = strategy_name
        if scope_ids is not None:
            strategy.scope_ids = scope_ids
        if data_types is not None:
            strategy.data_types = data_types
        if schedule_cron is not None:
            strategy.schedule_cron = schedule_cron
        if fetch_config is not None:
            strategy.fetch_config = fetch_config
        if is_enabled is not None:
            strategy.is_enabled = is_enabled
        if description is not None:
            strategy.description = description

        return strategy

    async def update_last_run(
        self,
        strategy_id: int,
        status: str,
        run_at: Optional[datetime] = None,
    ) -> bool:
        """Update last run info for strategy."""
        strategy = await self.get_by_id(strategy_id)
        if not strategy:
            return False

        strategy.last_run_at = run_at or datetime.now()
        strategy.last_run_status = status
        return True

    async def delete_strategy(self, strategy_id: int) -> bool:
        """Delete collect strategy."""
        strategy = await self.get_by_id(strategy_id)
        if not strategy:
            return False

        await self.session.delete(strategy)
        return True


class CollectTaskRepository:
    """Repository for CollectTask operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_tasks(
        self,
        status: Optional[str] = None,
        strategy_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[CollectTask], int]:
        """List collect tasks with pagination."""
        query = select(CollectTask)

        if status:
            query = query.where(CollectTask.status == status)
        if strategy_id:
            query = query.where(CollectTask.strategy_id == strategy_id)

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

    async def get_by_id(self, task_id: int) -> Optional[CollectTask]:
        """Get collect task by ID."""
        result = await self.session.execute(
            select(CollectTask).where(CollectTask.task_id == task_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, task_code: str) -> Optional[CollectTask]:
        """Get collect task by code."""
        result = await self.session.execute(
            select(CollectTask).where(CollectTask.task_code == task_code)
        )
        return result.scalar_one_or_none()

    async def create_task(
        self,
        task_code: str,
        task_type: str,
        strategy_id: Optional[int] = None,
        triggered_by: Optional[int] = None,
    ) -> CollectTask:
        """Create a new collect task."""
        task = CollectTask(
            task_code=task_code,
            strategy_id=strategy_id,
            task_type=task_type,
            triggered_by=triggered_by,
            triggered_at=datetime.now(),
            status="pending",
        )
        self.session.add(task)
        await self.session.flush()
        return task

    async def update_task_status(
        self,
        task_id: int,
        status: str,
        progress_percent: Optional[int] = None,
        current_step: Optional[str] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        error_message: Optional[str] = None,
        error_details: Optional[dict] = None,
    ) -> Optional[CollectTask]:
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
        total_records: Optional[int] = None,
        processed_records: Optional[int] = None,
        success_records: Optional[int] = None,
        failed_records: Optional[int] = None,
        skipped_records: Optional[int] = None,
    ) -> Optional[CollectTask]:
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
        result_summary: Optional[dict] = None,
        error_message: Optional[str] = None,
    ) -> Optional[CollectTask]:
        """Mark task as completed."""
        task = await self.get_by_id(task_id)
        if not task:
            return None

        task.status = "completed" if success else "failed"
        task.completed_at = datetime.now()
        task.progress_percent = 100

        if result_summary:
            task.result_summary = result_summary
        if error_message:
            task.error_message = error_message

        return task

    async def get_active_tasks(self) -> List[CollectTask]:
        """Get all currently active (pending or running) tasks."""
        result = await self.session.execute(
            select(CollectTask).where(
                CollectTask.status.in_(["pending", "running"])
            ).order_by(CollectTask.task_id)
        )
        return list(result.scalars().all())
