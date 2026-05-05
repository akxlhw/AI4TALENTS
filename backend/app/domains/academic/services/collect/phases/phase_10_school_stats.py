"""Phase 10: Update school professor_count and student_count."""

from __future__ import annotations

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.academic.models.school import School
from app.domains.academic.models.talent import Talent
from app.domains.academic.services.collect.phases.base import PhaseContext, PhaseHandler
from app.domains.academic.services.collect.progress_tracker import ProgressTracker


class PhaseSchoolStatsHandler(PhaseHandler):
    """Phase 10: Update school statistics incrementally.

    Only updates schools affected by this task to avoid unnecessary work.
    Falls back to a full update when no affected schools are tracked.

    Uses coalesce(education_school_id, company_school_id, school_id) as the
    primary school affiliation to ensure scholars matched via the new primary
    institution fields are also counted.
    """

    phase_name = "更新学校统计"
    phase_progress = 90

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
                    func.count(case((Talent.role_type == "professor", 1))).label(
                        "professor_count"
                    ),
                    func.count(
                        case((Talent.role_type.in_(["student", "graduate"]), 1))
                    ).label("student_count"),
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
        self.progress_tracker.add_log("info", f"更新了 {updated_schools} 所学校的统计")

    async def _full_update(self) -> None:
        await self.session.execute(
            School.__table__.update().values(professor_count=0, student_count=0)
        )

        primary_school = self._primary_school_id_expr()

        result = await self.session.execute(
            select(
                primary_school.label("primary_school_id"),
                func.count(case((Talent.role_type == "professor", 1))).label(
                    "professor_count"
                ),
                func.count(
                    case((Talent.role_type.in_(["student", "graduate"]), 1))
                ).label("student_count"),
            )
            .where(primary_school.isnot(None), Talent.is_visible.is_(True))
            .group_by(primary_school)
        )

        updated_schools = 0
        for i, row in enumerate(result):
            school_id, prof_count, stu_count = row
            if school_id:
                await self.session.execute(
                    School.__table__.update()
                    .where(School.school_id == school_id)
                    .values(professor_count=prof_count, student_count=stu_count)
                )
                updated_schools += 1
                if (i + 1) % 50 == 0:
                    await self.session.commit()

        await self.session.flush()
        self.progress_tracker.add_log("info", f"更新了 {updated_schools} 所学校的统计")
