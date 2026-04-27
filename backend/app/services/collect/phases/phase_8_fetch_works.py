"""Phase 8: Compute selected works for newly created talents from local RawWork."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.talent import SelectedWork
from app.services.collect.phases.base import PhaseContext, PhaseHandler
from app.services.collect.progress_tracker import ProgressTracker
from app.services.data_fetchers import WorkFetcher

logger = logging.getLogger(__name__)


class PhaseFetchWorksHandler(PhaseHandler):
    """Phase 8: Compute top-cited works for new talents from local RawWork.

    Replaces external API calls with local database computation for better
    reliability in enterprise intranet environments.
    """

    phase_name = "计算代表作品"
    phase_progress = 75

    def __init__(
        self,
        session: AsyncSession,
        progress_tracker: ProgressTracker,
        work_fetcher: WorkFetcher | None = None,
    ) -> None:
        super().__init__(session, progress_tracker)
        self.work_fetcher = work_fetcher

    async def execute(self, context: PhaseContext) -> None:
        new_talents = context.new_talents
        progress = context.progress

        if not new_talents:
            self.progress_tracker.add_log("info", "无需计算代表作品（无新增学者）")
            return

        if not self.work_fetcher:
            self.progress_tracker.add_log("warning", "Work fetcher not configured")
            return

        progress.current_step = "Computing selected works from local data"
        self.progress_tracker.add_log(
            "info", f"开始为 {len(new_talents)} 位学者从本地论文计算代表作品"
        )

        # 从当前任务已采集的 RawWork 中一次性计算所有学者的代表作
        task_id = getattr(context.task, "task_id", None) if context.task else None
        author_works_map = await self.work_fetcher.compute_selected_works_for_all_authors(
            task_id=task_id, max_works=10
        )

        total_inserted = 0
        total_authors = 0

        for talent_info in new_talents:
            try:
                talent_id = talent_info["talent_id"]
                openalex_author_id = talent_info["openalex_author_id"]
                works_count = talent_info.get("works_count", 0)

                # 论文数过少的学者跳过，避免无意义的代表作展示
                if works_count <= 5:
                    continue

                works = author_works_map.get(openalex_author_id, [])
                if not works:
                    continue

                for order, work in enumerate(works):
                    selected_work = SelectedWork(
                        talent_id=talent_id,
                        title=work["title"][:500],
                        publication_year=work["publication_year"],
                        venue_name=work["venue_name"][:255] if work["venue_name"] else None,
                        citation_count=work["citation_count"],
                        source_work_id=work["source_work_id"][:100] if work["source_work_id"] else None,
                        doi=work["doi"][:100] if work["doi"] else None,
                        display_order=order,
                    )
                    self.session.add(selected_work)
                    total_inserted += 1

                total_authors += 1

            except Exception as e:
                self.progress_tracker.add_log(
                    "warning",
                    f"计算代表作品失败: talent_id={talent_info.get('talent_id')}, error={e}",
                )

        await self.session.flush()

        self.progress_tracker.add_log(
            "info", f"代表作品计算完成: {total_authors} 位学者，{total_inserted} 篇作品"
        )
