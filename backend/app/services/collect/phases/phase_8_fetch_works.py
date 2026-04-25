"""Phase 8: Fetch selected works for newly created talents."""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.talent import SelectedWork
from app.services.collect.phases.base import PhaseContext, PhaseHandler
from app.services.collect.progress_tracker import ProgressTracker
from app.services.data_fetchers import WorkFetcher

logger = logging.getLogger(__name__)


class PhaseFetchWorksHandler(PhaseHandler):
    """Phase 8: Fetch top-cited works for new talents.

    Uses an :class:`asyncio.Semaphore` to limit concurrent API requests.
    """

    phase_name = "获取代表作品"
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
        from app.services.common.openalex_utils import REQUEST_DELAY

        new_talents = context.new_talents
        progress = context.progress

        if not new_talents:
            self.progress_tracker.add_log("info", "无需获取代表作品（无新增教授）")
            return

        if not self.work_fetcher:
            self.progress_tracker.add_log("warning", "Work fetcher not configured")
            return

        progress.current_step = "Fetching selected works"
        self.progress_tracker.add_log(
            "info", f"开始为 {len(new_talents)} 位新入库教授获取代表作品"
        )

        semaphore = asyncio.Semaphore(3)
        total_fetched = 0
        total_inserted = 0
        errors: list[str] = []

        async def fetch_for_talent(talent_info: dict) -> None:
            nonlocal total_fetched, total_inserted
            async with semaphore:
                try:
                    talent_id = talent_info["talent_id"]
                    openalex_author_id = talent_info["openalex_author_id"]
                    works_count = talent_info.get("works_count", 0)

                    # Only fetch for authors with > 5 works
                    if works_count <= 5:
                        return

                    works = await self.work_fetcher.fetch_author_top_works(
                        openalex_author_id=openalex_author_id, max_works=10
                    )
                    if not works:
                        return

                    for order, work in enumerate(works):
                        if not work.get("title"):
                            continue

                        selected_work = SelectedWork(
                            talent_id=talent_id,
                            title=work.get("title", "")[:500],
                            publication_year=work.get("publication_year"),
                            venue_name=(
                                work.get("venue_name", "")[:255]
                                if work.get("venue_name")
                                else None
                            ),
                            citation_count=work.get("citation_count", 0),
                            source_work_id=(
                                work.get("source_work_id", "")[:100]
                                if work.get("source_work_id")
                                else None
                            ),
                            doi=work.get("doi", "")[:100] if work.get("doi") else None,
                            display_order=order,
                        )
                        self.session.add(selected_work)
                        total_inserted += 1

                    total_fetched += 1
                    await asyncio.sleep(REQUEST_DELAY)
                except Exception as e:
                    errors.append(f"talent_id={talent_info.get('talent_id')}: {str(e)}")

        await asyncio.gather(*[fetch_for_talent(t) for t in new_talents])
        await self.session.flush()

        for error in errors:
            self.progress_tracker.add_log("warning", f"获取代表作品失败: {error}")

        self.progress_tracker.add_log(
            "info", f"代表作品获取完成: {total_fetched} 位教授，{total_inserted} 篇作品"
        )
