"""
Progress tracking for collection tasks.
"""
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Union

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
    """Progress tracking and logging for collection tasks"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self._logs: List[Dict] = []

    def add_log(self, level: Union[LogLevel, str], message: str, details: Optional[Dict] = None):
        """Add a log entry

        Args:
            level: 日志级别，推荐使用 LogLevel 枚举
            message: 日志消息
            details: 可选的详细信息
        """
        # 支持 str 类型以保持向后兼容
        level_value = level.value if isinstance(level, LogLevel) else level

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level_value,
            "message": message,
        }
        if details:
            entry["details"] = details
        self._logs.append(entry)

        # Also log to standard logger
        if level_value == LogLevel.ERROR.value:
            logger.error(message)
        elif level_value == LogLevel.WARNING.value:
            logger.warning(message)
        elif level_value == LogLevel.DEBUG.value:
            logger.debug(message)
        else:
            logger.info(message)

    def reset_logs(self):
        """Reset logs for a new task"""
        self._logs = []

    def get_logs(self) -> List[Dict]:
        """Get all logs"""
        return self._logs.copy()

    async def save_logs(self, task: CollectTask):
        """Save logs to task"""
        task.execution_logs = self._logs.copy()
        await self.session.flush()

    def create_progress(self, task_id: int) -> CollectionProgress:
        """Create a new progress object"""
        return CollectionProgress(task_id=task_id)

    async def update_task_status(
        self,
        task: CollectTask,
        status: str,
        error_message: Optional[str] = None
    ):
        """Update task status"""
        task.status = status
        if status == "running":
            task.started_at = datetime.now(timezone.utc)
            task.progress_percent = 0
        elif status == "completed":
            task.completed_at = datetime.now(timezone.utc)
            task.progress_percent = 100
        elif status == "failed":
            task.completed_at = datetime.now(timezone.utc)
        if error_message:
            task.error_message = error_message
        await self.session.flush()

    async def update_progress(
        self,
        task: CollectTask,
        current_step: Optional[str] = None,
        progress_percent: Optional[int] = None
    ):
        """Update task progress in real-time.

        This should be called during task execution to update the frontend display.
        Note: This method only flushes changes without committing. The transaction
        boundary is managed by CollectionOrchestrator.execute_task() to ensure
        atomicity of the entire pipeline.
        """
        if current_step:
            task.current_step = current_step
        if progress_percent is not None:
            task.progress_percent = progress_percent
        await self.session.flush()
        # 不再 commit，由 orchestrator 统一管理事务边界
        # 前端通过轮询获取进度，flush 后数据对同一 session 可见
