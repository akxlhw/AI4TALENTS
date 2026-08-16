"""Phase 10: Update school professor_count and student_count."""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import case, func, select, text
from sqlalchemy.exc import DatabaseError, OperationalError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.domains.academic.models.school import School
from app.domains.academic.models.talent import Talent
from app.domains.academic.services.collect.phases.base import PhaseContext, PhaseHandler
from app.domains.shared.services.cache_keys import CacheKeys
from app.domains.shared.services.cache_service import CacheService

logger = logging.getLogger(__name__)


class PhaseSchoolStatsHandler(PhaseHandler):
    """Phase 10: Update school statistics incrementally.

    Only updates schools affected by this task to avoid unnecessary work.
    Falls back to a full update when no affected schools are tracked.

    Uses coalesce(education_school_id, company_school_id, school_id) as the
    primary school affiliation to ensure scholars matched via the new primary
    institution fields are also counted.
    """

    phase_code = "phase_10_school_stats"
    phase_name = "更新学校统计"
    phase_progress = 90
    is_critical = True

    async def execute(self, context: PhaseContext) -> None:
        progress = context.progress
        progress.current_step = "Updating school statistics"
        self.progress_tracker.add_log("info", "开始更新学校统计")

        affected_school_ids = progress.affected_school_ids

        if affected_school_ids:
            self.progress_tracker.add_log(
                "info", f"增量更新 {len(affected_school_ids)} 所受影响的学校"
            )
            await self._incremental_update(affected_school_ids)
        else:
            self.progress_tracker.add_log("info", "执行全量学校统计更新")
            await self._full_update()

    @staticmethod
    def _primary_school_id_expr():
        """SQL expression for primary school id (education -> company -> legacy)."""
        return func.coalesce(Talent.education_school_id, Talent.company_school_id, Talent.school_id)

    async def _incremental_update(self, affected_school_ids: set[int]) -> None:
        SCHOOL_BATCH_SIZE = 5000
        school_id_list = list(affected_school_ids)
        updated_schools = 0
        primary_school = self._primary_school_id_expr()

        for batch_start in range(0, len(school_id_list), SCHOOL_BATCH_SIZE):
            batch_ids = school_id_list[batch_start : batch_start + SCHOOL_BATCH_SIZE]

            await self.session.execute(
                School.__table__.update()
                .where(School.school_id.in_(batch_ids))
                .values(professor_count=0, student_count=0)
            )

            result = await self.session.execute(
                select(
                    primary_school.label("primary_school_id"),
                    func.count(case((Talent.role_type == "professor", 1))).label("professor_count"),
                    func.count(case((Talent.role_type.in_(["student", "graduate"]), 1))).label(
                        "student_count"
                    ),
                )
                .where(primary_school.in_(batch_ids), Talent.is_visible.is_(True))
                .group_by(primary_school)
            )

            for row in result:
                school_id, prof_count, stu_count = row
                if school_id:
                    await self.session.execute(
                        School.__table__.update()
                        .where(School.school_id == school_id)
                        .values(professor_count=prof_count, student_count=stu_count)
                    )
                    updated_schools += 1

        await self.session.flush()
        await self._refresh_materialized_view()
        self.progress_tracker.add_log("info", f"更新了 {updated_schools} 所学校的统计")

    async def _full_update(self) -> None:
        await self.session.execute(
            School.__table__.update().values(professor_count=0, student_count=0)
        )

        primary_school = self._primary_school_id_expr()

        result = await self.session.execute(
            select(
                primary_school.label("primary_school_id"),
                func.count(case((Talent.role_type == "professor", 1))).label("professor_count"),
                func.count(case((Talent.role_type.in_(["student", "graduate"]), 1))).label(
                    "student_count"
                ),
            )
            .where(primary_school.isnot(None), Talent.is_visible.is_(True))
            .group_by(primary_school)
        )

        updated_schools = 0
        for _i, row in enumerate(result):
            school_id, prof_count, stu_count = row
            if school_id:
                await self.session.execute(
                    School.__table__.update()
                    .where(School.school_id == school_id)
                    .values(professor_count=prof_count, student_count=stu_count)
                )
                updated_schools += 1
        await self.session.flush()
        await self._refresh_materialized_view()
        self.progress_tracker.add_log("info", f"更新了 {updated_schools} 所学校的统计")

    async def _refresh_materialized_view(self) -> None:
        """Refresh the materialized view for school talent counts.

        Resilience features:
        - Checks unique index existence before CONCURRENTLY refresh; falls back
          to blocking refresh if the index is missing.
        - Retries up to 3 times with exponential backoff on transient DB errors.
        - Applies a 300-second timeout to prevent indefinite hangs.
        - Prometheus metrics: duration histogram + success/failure counters.
        """
        import time

        from app.core.metrics import MV_REFRESH_DURATION, MV_REFRESH_FAILURES, MV_REFRESH_SUCCESSES

        start_time = time.perf_counter()

        # Check whether the unique index required by CONCURRENTLY exists.
        idx_result = await self.session.execute(text("""
                SELECT 1 FROM pg_indexes
                WHERE indexname = 'idx_mv_school_talent_count_school_id'
                LIMIT 1
                """))
        has_index = idx_result.scalar() is not None

        refresh_sql = (
            "REFRESH MATERIALIZED VIEW CONCURRENTLY mv_school_talent_count"
            if has_index
            else "REFRESH MATERIALIZED VIEW mv_school_talent_count"
        )

        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, max=30),
            retry=retry_if_exception_type((OperationalError, DatabaseError)),
            reraise=True,
        )
        async def _do_refresh() -> None:
            await asyncio.wait_for(
                self.session.execute(text(refresh_sql)),
                timeout=settings.MV_REFRESH_TIMEOUT,
            )

        try:
            await _do_refresh()
        except TimeoutError:
            self.progress_tracker.add_log(
                "error",
                f"刷新学校人才数物化视图超时（{settings.MV_REFRESH_TIMEOUT}s），后续查询可能返回旧数据",
            )
            logger.warning(
                f"Materialized view refresh timed out after {settings.MV_REFRESH_TIMEOUT}s"
            )
            MV_REFRESH_FAILURES.inc()
            MV_REFRESH_DURATION.observe(time.perf_counter() - start_time)
            raise
        except Exception as exc:
            self.progress_tracker.add_log("error", f"刷新物化视图失败（已重试3次）: {exc}")
            logger.exception("Materialized view refresh failed after retries")
            MV_REFRESH_FAILURES.inc()
            MV_REFRESH_DURATION.observe(time.perf_counter() - start_time)
            raise

        duration = time.perf_counter() - start_time
        MV_REFRESH_SUCCESSES.inc()
        MV_REFRESH_DURATION.observe(duration)
        self.progress_tracker.add_log("info", "已刷新学校人才数物化视图")

        # Invalidate homepage cache so the next request sees fresh data.
        try:
            from app.core.cache import get_cache_connection

            cache_conn = await get_cache_connection()
            cache_service = CacheService(cache_conn)
            await cache_service.delete(CacheKeys.STATS_HOME_HIGHLIGHTS)
            self.progress_tracker.add_log("info", "已清除首页统计缓存")
        except Exception:
            # Cache invalidation is best-effort; don't fail the phase for it.
            logger.warning("Failed to invalidate homepage cache after MV refresh", exc_info=True)
