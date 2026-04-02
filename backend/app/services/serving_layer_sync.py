"""
Serving Layer Synchronization Service.
服务层同步器 - 从标准化层同步数据到服务层(Talent/School)

DEPRECATED: This class is a facade that delegates to specialized services.
For new code, use ServingLayerOrchestrator directly.
"""
from __future__ import annotations

import logging
import warnings

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.raw_data import AuthorTechBelong
from app.models.school import School
from app.models.standardized import StdAuthor, StdSchool
from app.models.talent import Talent
from app.services.sync.author_sync import AuthorSyncService
from app.services.sync.orchestrator import ServingLayerOrchestrator
from app.services.sync.school_sync import SchoolSyncService
from app.services.sync.tech_tag_sync import TechTagSyncService

logger = logging.getLogger(__name__)


class ServingLayerSync:
    """
    服务层同步器 - 负责将标准化层数据同步到服务层

    DEPRECATED: This class is a facade for backward compatibility.
    Use ServingLayerOrchestrator for new implementations.

    数据流:
    StdAuthor → Talent (core_talent)
    StdSchool → School (core_school)
    AuthorTechBelong → TalentTechTag (core_talent_tech_tag)
    """

    def __init__(self, session: AsyncSession):
        warnings.warn(
            "ServingLayerSync is deprecated. Use ServingLayerOrchestrator instead.",
            DeprecationWarning,
            stacklevel=2
        )
        self.session = session

        # Initialize specialized services
        self._author_sync = AuthorSyncService(session)
        self._school_sync = SchoolSyncService(session)
        self._tech_tag_sync = TechTagSyncService(session)
        self._orchestrator = ServingLayerOrchestrator(session)

    async def sync_author_to_talent(
        self,
        std_author: StdAuthor,
        update_existing: bool = True
    ) -> tuple[Talent, bool]:
        """Sync standardized author to serving layer Talent table"""
        return await self._author_sync.sync_author_to_talent(std_author, update_existing)

    async def sync_school_to_school(
        self,
        std_school: StdSchool,
        update_existing: bool = True
    ) -> tuple[School, bool]:
        """Sync standardized school to serving layer School table"""
        return await self._school_sync.sync_school_to_school(std_school, update_existing)

    async def sync_talent_tech_tags(
        self,
        talent: Talent,
        belongs: list[AuthorTechBelong],
        default_tech_direction_id: int | None = None
    ) -> int:
        """Create TalentTechTag records based on AuthorTechBelong"""
        return await self._tech_tag_sync.sync_talent_tech_tags(talent, belongs, default_tech_direction_id)

    async def sync_all_for_task(
        self,
        task_id: int,
        tech_element_id: int,
        default_tech_direction_id: int | None = None
    ) -> dict:
        """Sync all standardized data for a task to serving layer"""
        return await self._orchestrator.sync_all_for_task(task_id, tech_element_id, default_tech_direction_id)
