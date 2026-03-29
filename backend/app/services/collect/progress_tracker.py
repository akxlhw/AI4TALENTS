"""
Progress tracking for collection tasks.
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sync import CollectTask
from app.services.common.progress import CollectionProgress

logger = logging.getLogger(__name__)


class ProgressTracker:
    """Progress tracking and logging for collection tasks"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self._logs: List[Dict] = []

    def add_log(self, level: str, message: str, details: Optional[Dict] = None):
        """Add a log entry"""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,  # info, warning, error
            "message": message,
        }
        if details:
            entry["details"] = details
        self._logs.append(entry)

        # Also log to standard logger
        if level == "error":
            logger.error(message)
        elif level == "warning":
            logger.warning(message)
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
        current_step: Optional[str] = None,
        progress_percent: Optional[int] = None
    ):
        """Update task progress in real-time.

        This should be called during task execution to update the frontend display.
        """
        if current_step:
            task.current_step = current_step
        if progress_percent is not None:
            task.progress_percent = progress_percent
        await self.session.flush()
        # Commit to make changes visible to frontend immediately
        await self.session.commit()
