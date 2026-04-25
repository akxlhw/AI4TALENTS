"""Phase 9: Update talent topic_tags from OpenAlex topics."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sync import CollectTask
from app.models.talent import Talent
from app.models.tech_domain import TalentTechTag
from app.services.collect.phases.base import PhaseContext, PhaseHandler
from app.services.collect.progress_tracker import ProgressTracker
from app.services.common.batch_utils import batch_in_query_flat


class PhaseTopicTagsHandler(PhaseHandler):
    """Phase 9: Update talent topic_tags from OpenAlex topics.

    Uses OpenAlex topics as the authoritative source instead of auto-tagging
    based on venue.
    """

    phase_name = "更新技术标签"
    phase_progress = 80

    async def execute(self, context: PhaseContext) -> None:
        progress = context.progress
        progress.current_step = "Updating topic tags"
        self.progress_tracker.add_log("info", "开始更新人才技术标签")

        task_result = await self.session.execute(
            select(CollectTask).where(CollectTask.task_id == context.task.task_id)
        )
        task = task_result.scalar_one_or_none()
        if not task:
            self.progress_tracker.add_log("warning", f"任务 {context.task.task_id} 不存在")
            return

        tech_domain_id = task.tech_domain_id

        distinct_ids_result = await self.session.execute(
            select(TalentTechTag.talent_id)
            .where(TalentTechTag.tech_domain_id == tech_domain_id)
            .distinct()
        )
        talent_ids = [row[0] for row in distinct_ids_result.all()]

        if not talent_ids:
            return

        talents = await batch_in_query_flat(
            self.session,
            lambda batch: select(Talent).where(Talent.talent_id.in_(batch)),
            talent_ids,
        )

        updated_count = 0
        for talent in talents:
            if talent.openalex_topics:
                talent.topic_tags = list(talent.openalex_topics)
                updated_count += 1
            else:
                talent.topic_tags = []

        await self.session.flush()
        self.progress_tracker.add_log("info", f"更新了 {updated_count} 个人才的技术标签")
