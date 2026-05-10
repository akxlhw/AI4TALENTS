"""
Tests for StatBuilder.
Covers: overview stats, school stats, research topic stats.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.academic.builders.stat_builder import StatBuilder
from app.domains.academic.models.school import School
from app.domains.academic.models.statistics import OverviewStatSnapshot, SchoolStatSnapshot
from app.domains.academic.models.talent import Talent
from app.domains.shared.models.enums import RoleType, VisibilityStatus


class TestStatBuilder:
    """Tests for StatBuilder."""

    @pytest.fixture
    async def builder(self, test_session: AsyncSession):
        """Create StatBuilder instance."""
        return StatBuilder(session=test_session, batch_id=1, version="v1.0-test")

    @pytest.fixture
    async def sample_data(self, test_session: AsyncSession):
        """Create sample school and talents for stat builder tests."""
        school = School(
            school_name="Test University",
            country_code="US",
            is_visible=True,
        )
        test_session.add(school)
        await test_session.flush()

        professor = Talent(
            name="Prof A",
            school_id=school.school_id,
            role_type=RoleType.PROFESSOR.value,
            is_visible=True,
            works_count=50,
            cited_by_count=1000,
        )
        student = Talent(
            name="Student B",
            school_id=school.school_id,
            role_type=RoleType.STUDENT.value,
            is_visible=True,
            works_count=5,
        )
        graduate = Talent(
            name="Graduate C",
            school_id=school.school_id,
            role_type=RoleType.GRADUATE.value,
            is_visible=True,
            works_count=10,
        )
        unknown = Talent(
            name="Unknown D",
            school_id=school.school_id,
            role_type=RoleType.UNKNOWN.value,
            is_visible=True,
            works_count=1,
        )
        test_session.add_all([professor, student, graduate, unknown])
        await test_session.commit()
        return school, [professor, student, graduate, unknown]

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_build_overview_stats(self, builder: StatBuilder, sample_data, test_session: AsyncSession):
        """Test _build_overview_stats creates snapshot with correct counts."""
        result = await builder._build_overview_stats()

        assert result["total_talents"] == 4
        assert result["total_professors"] == 1
        assert result["total_students"] == 2  # student + graduate
        assert result["total_schools"] == 1

        # Verify snapshot in DB
        snapshots = await test_session.execute(select(OverviewStatSnapshot))
        snapshot = snapshots.scalar_one()
        assert snapshot.talent_count == 4
        assert snapshot.professor_count == 1
        assert snapshot.is_active == 1

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_build_school_stats(self, builder: StatBuilder, sample_data, test_session: AsyncSession):
        """Test _build_school_stats creates per-school snapshots."""
        school, _ = sample_data
        result = await builder._build_school_stats()

        assert result["schools_processed"] == 1

        # Verify school snapshot in DB
        snapshots = await test_session.execute(
            select(SchoolStatSnapshot).where(SchoolStatSnapshot.school_id == school.school_id)
        )
        snapshot = snapshots.scalar_one()
        assert snapshot.professor_count == 1
        assert snapshot.student_count == 1
        assert snapshot.graduate_count == 1
        assert snapshot.unknown_count == 1
        assert snapshot.talent_count == 4
        assert snapshot.is_active == 1

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_build_full(self, builder: StatBuilder, sample_data):
        """Test build() returns successful BuildResult."""
        result = await builder.build()

        assert result.success is True
        assert result.records_processed == 4
        assert result.records_created >= 2  # overview + school snapshots
        assert result.records_failed == 0
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_build_no_data(self, builder: StatBuilder):
        """Test build() with no visible talents still succeeds."""
        result = await builder.build()

        assert result.success is True
        assert result.records_processed == 0
        assert result.records_created >= 1  # overview snapshot still created

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_build_deactivates_old_overview(self, builder: StatBuilder, sample_data, test_session: AsyncSession):
        """Test that new build deactivates old overview snapshots."""
        # Create an old active snapshot
        old = OverviewStatSnapshot(
            stat_version="v0.9",
            generated_at="2024-01-01T00:00:00",
            talent_count=100,
            is_active=1,
        )
        test_session.add(old)
        await test_session.commit()

        await builder.build()

        # Old snapshot should be deactivated
        await test_session.refresh(old)
        assert old.is_active == 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_build_deactivates_old_school_stats(self, builder: StatBuilder, sample_data, test_session: AsyncSession):
        """Test that new build deactivates old school snapshots."""
        school, _ = sample_data

        # Create an old active school snapshot
        old = SchoolStatSnapshot(
            school_id=school.school_id,
            stat_version="v0.9",
            generated_at="2024-01-01T00:00:00",
            talent_count=100,
            is_active=1,
        )
        test_session.add(old)
        await test_session.commit()

        await builder.build()

        # Old snapshot should be deactivated
        await test_session.refresh(old)
        assert old.is_active == 0
