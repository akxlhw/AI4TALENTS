"""
Unified collection service with layered architecture.
统一采集服务 - 基于分层架构的采集编排器

DEPRECATED: This class is a facade that delegates to specialized services.
For new code, use CollectionOrchestrator directly.
"""
import warnings
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sync import CollectTask
from app.services.common.progress import CollectionProgress
from app.services.collect.task_creation import TaskCreationService
from app.services.collect.orchestrator import CollectionOrchestrator
from app.services.data_fetchers import WorkFetcher, AuthorFetcher, InstitutionFetcher


class CollectMode(str, Enum):
    FULL = "full"
    INCREMENTAL = "incremental"


class UnifiedCollectService:
    """
    统一采集服务 - 协调数据采集、存储和标准化

    DEPRECATED: This class is a facade for backward compatibility.
    Use CollectionOrchestrator for new implementations.
    """

    # Time window defaults (delegated to TaskCreationService)
    FULL_COLLECTION_START_YEAR = 2015
    INCREMENTAL_LOOKBACK_DAYS = 30

    def __init__(self, session: AsyncSession, email: Optional[str] = None):
        warnings.warn(
            "UnifiedCollectService is deprecated. Use CollectionOrchestrator instead.",
            DeprecationWarning,
            stacklevel=2
        )
        self.session = session
        self.email = email

        # Initialize fetchers
        self.work_fetcher = WorkFetcher(session)
        self.author_fetcher = AuthorFetcher(session)
        self.institution_fetcher = InstitutionFetcher(session)

        # Initialize specialized services
        self._task_creator = TaskCreationService(session)
        self._orchestrator = CollectionOrchestrator(
            session,
            work_fetcher=self.work_fetcher,
            author_fetcher=self.author_fetcher,
            institution_fetcher=self.institution_fetcher
        )

    async def create_task(
        self,
        tech_element_id: int,
        mode: str = "full",
        triggered_by: Optional[int] = None
    ) -> CollectTask:
        """Create a new collection task"""
        return await self._task_creator.create_task(tech_element_id, mode, triggered_by)

    async def execute_task(self, task_id: int) -> CollectionProgress:
        """Execute a collection task through all layers"""
        return await self._orchestrator.execute_task(task_id)

    async def get_task_progress(self, task_id: int) -> Dict[str, Any]:
        """Get progress for a task"""
        return await self._orchestrator.get_task_progress(task_id)

    # Backward-compatible aliases for internal methods (used by tests)
    def _get_time_window(self, mode: str, last_collect_at=None):
        """Backward-compatible alias for time window calculation"""
        return self._task_creator.get_time_window(mode, last_collect_at)

    def _add_log(self, level: str, message: str, details: Optional[Dict] = None):
        """Backward-compatible alias for log tracking"""
        return self._orchestrator.progress_tracker.add_log(level, message, details)

    @property
    def _logs(self):
        """Backward-compatible alias for logs"""
        return self._orchestrator.progress_tracker.get_logs()

    async def _get_default_tech_direction(self, tech_element_id: int):
        """Backward-compatible alias for default tech direction"""
        return await self._orchestrator._get_default_tech_direction(tech_element_id)
