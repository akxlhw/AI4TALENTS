"""Phase 11: Build statistics snapshots for homepage."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.builders.stat_builder import StatBuilder
from app.services.collect.phases.base import PhaseContext, PhaseHandler
from app.services.collect.progress_tracker import ProgressTracker

logger = logging.getLogger(__name__)


class PhaseBuildStatsHandler(PhaseHandler):
    """Phase 11: Build homepage statistics via :class:`StatBuilder`."""

    phase_name = "构建统计数据"
    phase_progress = 95

    async def execute(self, context: PhaseContext) -> None:
        progress = context.progress
        progress.current_step = "Building statistics"
        self.progress_tracker.add_log("info", "开始生成统计数据")

        try:
            builder = StatBuilder(
                self.session,
                batch_id=context.task.task_id,
                version=f"task-{context.task.task_id}",
            )
            result = await builder.build()

            if result.success:
                self.progress_tracker.add_log(
                    "info", "统计数据生成完成", {"records_created": result.records_created}
                )
            else:
                self.progress_tracker.add_log(
                    "warning", f"统计数据生成失败: {result.errors}"
                )
        except Exception as e:
            self.progress_tracker.add_log("warning", f"统计数据生成异常: {str(e)}")
