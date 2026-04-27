"""
Statistics builder.
Generates statistics snapshots for overview and school-level metrics.
"""

import logging
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.builders.base import BaseBuilder, BuildResult
from app.models.enums import RoleType
from app.models.school import School
from app.models.statistics import OverviewStatSnapshot, SchoolStatSnapshot
from app.models.talent import Talent

logger = logging.getLogger(__name__)


class StatBuilder(BaseBuilder):
    """
    Builder for statistics snapshots.

    Generates:
    - Overview statistics (total counts)
    - Per-school statistics
    """

    def __init__(self, session: AsyncSession, batch_id: int, version: str):
        super().__init__(batch_id)
        self.session = session
        self.version = version

    async def build(self) -> BuildResult:
        """
        Build all statistics snapshots.

        Returns:
            BuildResult with statistics
        """
        started_at = datetime.now()

        try:
            # Build overview stats
            overview_result = await self._build_overview_stats()

            # Build school stats
            school_result = await self._build_school_stats()

            await self.session.commit()

            records_created = 1 + school_result["schools_processed"]
            completed_at = datetime.now()

            return BuildResult(
                success=True,
                records_processed=overview_result["total_talents"],
                records_created=records_created,
                records_updated=0,
                records_failed=0,
                errors=self.errors,
                started_at=started_at,
                completed_at=completed_at,
            )

        except Exception as e:
            self.log_error(str(e))
            return BuildResult(
                success=False,
                records_processed=0,
                records_created=0,
                records_updated=0,
                records_failed=1,
                errors=self.errors,
                started_at=started_at,
                completed_at=datetime.now(),
            )

    async def _build_overview_stats(self) -> dict[str, int]:
        """
        Build overview statistics snapshot.

        Returns:
            Dictionary with counts
        """
        logger.info("Building overview statistics")

        # Count schools with visible talents (using primary school affiliation)
        primary_school = func.coalesce(Talent.education_school_id, Talent.company_school_id, Talent.school_id)
        school_result = await self.session.execute(
            select(func.count(func.distinct(primary_school))).where(
                Talent.is_visible.is_(True),
                primary_school.isnot(None),
            )
        )
        school_count = school_result.scalar() or 0

        # Count professors
        professor_result = await self.session.execute(
            select(func.count(Talent.talent_id)).where(
                Talent.is_visible.is_(True),
                Talent.role_type == RoleType.PROFESSOR.value,
            )
        )
        professor_count = professor_result.scalar() or 0

        # Count students (student + graduated)
        student_result = await self.session.execute(
            select(func.count(Talent.talent_id)).where(
                Talent.is_visible.is_(True),
                Talent.role_type.in_(
                    [
                        RoleType.STUDENT.value,
                        RoleType.GRADUATE.value,
                    ]
                ),
            )
        )
        student_count = student_result.scalar() or 0

        # Total talents
        total_result = await self.session.execute(
            select(func.count(Talent.talent_id)).where(Talent.is_visible.is_(True))
        )
        total_count = total_result.scalar() or 0

        # Deactivate old snapshots
        await self.session.execute(OverviewStatSnapshot.__table__.update().values(is_active=0))

        # Create new snapshot
        snapshot = OverviewStatSnapshot(
            stat_version=self.version,
            generated_at=datetime.now().isoformat(),
            school_count=school_count,
            professor_count=professor_count,
            student_count=student_count,
            talent_count=total_count,
            generated_by_batch_id=self.batch_id,
            is_active=1,
        )

        self.session.add(snapshot)

        logger.info(
            f"Overview stats: {school_count} schools, "
            f"{professor_count} professors, {student_count} students"
        )

        return {
            "total_schools": school_count,
            "total_professors": professor_count,
            "total_students": student_count,
            "total_talents": total_count,
        }

    async def _build_school_stats(self) -> dict[str, int]:
        """
        Build per-school statistics snapshots.

        Returns:
            Dictionary with processing results
        """
        logger.info("Building school statistics")

        # Get all schools with talents (using primary school affiliation)
        primary_school = func.coalesce(Talent.education_school_id, Talent.company_school_id, Talent.school_id)
        result = await self.session.execute(
            select(School.school_id, School.school_name)
            .join(Talent, School.school_id == primary_school)
            .where(Talent.is_visible.is_(True))
            .distinct()
        )
        schools = result.all()

        schools_processed = 0

        for school_id, _school_name in schools:
            try:
                await self._build_single_school_stats(school_id)
                schools_processed += 1
            except Exception as e:
                self.log_error(f"Failed to build stats for school {school_id}: {e}")

        return {"schools_processed": schools_processed}

    async def _build_single_school_stats(self, school_id: int) -> None:
        """Build statistics for a single school."""
        primary_school = func.coalesce(Talent.education_school_id, Talent.company_school_id, Talent.school_id)

        # Count professors
        professor_result = await self.session.execute(
            select(func.count(Talent.talent_id)).where(
                primary_school == school_id,
                Talent.is_visible.is_(True),
                Talent.role_type == RoleType.PROFESSOR.value,
            )
        )
        professor_count = professor_result.scalar() or 0

        # Count students
        student_result = await self.session.execute(
            select(func.count(Talent.talent_id)).where(
                primary_school == school_id,
                Talent.is_visible.is_(True),
                Talent.role_type == RoleType.STUDENT.value,
            )
        )
        student_count = student_result.scalar() or 0

        # Count graduates
        graduate_result = await self.session.execute(
            select(func.count(Talent.talent_id)).where(
                primary_school == school_id,
                Talent.is_visible.is_(True),
                Talent.role_type == RoleType.GRADUATE.value,
            )
        )
        graduate_count = graduate_result.scalar() or 0

        # Count unknown
        unknown_result = await self.session.execute(
            select(func.count(Talent.talent_id)).where(
                primary_school == school_id,
                Talent.is_visible.is_(True),
                Talent.role_type == RoleType.UNKNOWN.value,
            )
        )
        unknown_count = unknown_result.scalar() or 0

        # Total
        total_count = professor_count + student_count + graduate_count + unknown_count

        # Deactivate old snapshots for this school
        await self.session.execute(
            SchoolStatSnapshot.__table__.update()
            .where(SchoolStatSnapshot.school_id == school_id)
            .values(is_active=0)
        )

        # Create new snapshot
        snapshot = SchoolStatSnapshot(
            school_id=school_id,
            stat_version=self.version,
            generated_at=datetime.now().isoformat(),
            professor_count=professor_count,
            student_count=student_count,
            talent_count=total_count,
            graduate_count=graduate_count,
            unknown_count=unknown_count,
            generated_by_batch_id=self.batch_id,
            is_active=1,
        )

        self.session.add(snapshot)

        # Update school's cached counts
        await self.session.execute(
            School.__table__.update()
            .where(School.school_id == school_id)
            .values(
                professor_count=professor_count,
                student_count=student_count + graduate_count,
            )
        )
