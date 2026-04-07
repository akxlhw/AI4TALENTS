"""
Progress tracking for collection tasks.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sync import CollectTask
from app.services.common.progress import CollectionProgress

logger = logging.getLogger(__name__)


class LogLevel(str, Enum):
    """日志级别枚举

    用于类型安全的日志级别定义，避免字符串拼写错误。
    继承 str 使其可以直接用于 JSON 序列化。
    """
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    DEBUG = "debug"


class ProgressTracker:
    """Progress tracking and logging for collection tasks

    Uses independent database connections for progress updates to avoid
    blocking other operations during long-running collection tasks.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self._logs: list[dict] = []
        self._task_id: int | None = None

    def add_log(self, level: LogLevel | str, message: str, details: dict | None = None):
        """Add a log entry

        Args:
            level: 日志级别，推荐使用 LogLevel 枚举
            message: 日志消息
            details: 可选的详细信息
        """
        # 支持 str 类型以保持向后兼容
        level_value = level.value if isinstance(level, LogLevel) else level

        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level_value,
            "message": message,
        }
        if details:
            entry["details"] = details
        self._logs.append(entry)

        # Only log WARNING and ERROR to standard logger to reduce I/O overhead
        # INFO and DEBUG logs are saved to database for later review
        if level_value == LogLevel.ERROR.value:
            logger.error(message)
        elif level_value == LogLevel.WARNING.value:
            logger.warning(message)
        # Removed INFO/DEBUG console output for performance

    def reset_logs(self):
        """Reset logs for a new task"""
        self._logs = []

    def get_logs(self) -> list[dict]:
        """Get all logs"""
        return self._logs.copy()

    async def save_logs(self, task: CollectTask):
        """Save logs to task"""
        task.execution_logs = self._logs.copy()
        await self.session.flush()

    def create_progress(self, task_id: int) -> CollectionProgress:
        """Create a new progress object"""
        self._task_id = task_id
        return CollectionProgress(task_id=task_id)

    async def update_task_status(
        self,
        task: CollectTask,
        status: str,
        error_message: str | None = None
    ):
        """Update task status"""
        task.status = status
        if status == "running":
            task.started_at = datetime.utcnow()
            task.progress_percent = 0
        elif status == "completed":
            task.completed_at = datetime.utcnow()
            task.progress_percent = 100
        elif status == "failed":
            task.completed_at = datetime.utcnow()
        if error_message:
            task.error_message = error_message
        await self.session.flush()

    async def update_progress(
        self,
        task: CollectTask,
        current_step: str | None = None,
        progress_percent: int | None = None
    ):
        """Update task progress using main session only.

        Uses the main session to avoid SQLAlchemy async state conflicts
        that occur when multiple sessions try to update the same row concurrently.
        """
        # Build update values directly on the task object
        if current_step:
            task.current_step = current_step
        if progress_percent is not None:
            task.progress_percent = progress_percent

        # Flush to database - let the main transaction handle it
        await self.session.flush()

