"""Phase 7: Sync normalized data to the serving layer."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.academic.models.sync import CollectTask
from app.domains.academic.models.tech_domain import TechDirection, TechDomain
from app.domains.academic.services.collect.phases.base import PhaseContext, PhaseHandler
from app.domains.academic.services.collect.progress_tracker import ProgressTracker
from app.domains.academic.services.sync import ServingLayerOrchestrator

logger = logging.getLogger(__name__)


class PhaseSyncServingHandler(PhaseHandler):
    """Phase 7: Sync to serving layer.

    Delegates to :class:`ServingLayerOrchestrator` and returns the list of
    newly-created talents so that Phase 8 can fetch their selected works.
    """

    phase_name = "同步到服务层"
    phase_progress = 70

    async def execute(self, context: PhaseContext) -> list[dict]:
        progress = context.progress
        progress.current_step = "Syncing to serving layer"

        sync = ServingLayerOrchestrator(self.session)
        default_direction_id = await self._get_or_create_default_tech_direction(
            context.task.tech_domain_id
        )

        stats = await sync.sync_all_for_task(
            task_id=context.task.task_id,
            tech_domain_id=context.task.tech_domain_id,
            default_tech_direction_id=default_direction_id,
        )

        progress.synced_authors = stats.get("authors_synced", 0)
        progress.created_talents = stats.get("authors_created", 0)
        progress.updated_talents = stats.get("authors_updated", 0)
        progress.created_tech_tags = stats.get("tags_created", 0)

        affected_school_ids = stats.get("affected_school_ids", set())
        progress.affected_school_ids.update(affected_school_ids)

        for error in stats.get("errors", []):
            progress.errors.append(error)

        if progress.created_talents > 0 or progress.synced_authors > 0:
            self.progress_tracker.add_log(
                "info",
                f"入库人才: {progress.created_talents}, 更新: {progress.updated_talents}",
            )

        return stats.get("new_talents_for_works", [])

    async def _get_or_create_default_tech_direction(self, tech_domain_id: int) -> int | None:
        """Get existing default direction or create one."""
        direction_id = await self._get_default_tech_direction(tech_domain_id)
        if direction_id:
            return direction_id
        return await self._create_default_tech_direction(tech_domain_id)

    async def _get_default_tech_direction(self, tech_domain_id: int) -> int | None:
        result = await self.session.execute(
            select(TechDirection.tech_direction_id)
            .where(
                TechDirection.tech_domain_id == tech_domain_id,
                TechDirection.is_enabled.is_(True),
            )
            .order_by(TechDirection.sort_order)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _create_default_tech_direction(self, tech_domain_id: int) -> int | None:
        td_result = await self.session.execute(
            select(TechDomain).where(TechDomain.tech_domain_id == tech_domain_id)
        )
        tech_domain = td_result.scalar_one_or_none()
        if not tech_domain:
            logger.warning(
                f"Tech domain {tech_domain_id} not found, cannot create default direction"
            )
            return None

        new_direction = TechDirection(
            direction_code=f"{tech_domain.domain_code}-DEFAULT",
            direction_name=f"{tech_domain.domain_name}（默认）",
            tech_domain_id=tech_domain_id,
            sort_order=0,
            is_enabled=True,
        )
        self.session.add(new_direction)
        await self.session.flush()
        logger.info(f"Created default tech direction for {tech_domain.domain_name}")
        return new_direction.tech_direction_id
