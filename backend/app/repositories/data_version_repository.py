"""
Repository for data version operations.
数据版本管理数据访问层
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sync import DataCorrectionRecord, DataPublishRecord, DataQualitySummary, DataVersion


class DataVersionRepository:
    """Repository for DataVersion operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_versions(
        self,
        is_published: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[DataVersion], int]:
        """List data versions with pagination."""
        query = select(DataVersion)

        if is_published is not None:
            query = query.where(DataVersion.is_published == is_published)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Paginate
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size).order_by(DataVersion.version_id.desc())

        result = await self.session.execute(query)
        versions = list(result.scalars().all())

        return versions, total

    async def get_by_id(self, version_id: int) -> DataVersion | None:
        """Get data version by ID."""
        result = await self.session.execute(
            select(DataVersion).where(DataVersion.version_id == version_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, version_code: str) -> DataVersion | None:
        """Get data version by code."""
        result = await self.session.execute(
            select(DataVersion).where(DataVersion.version_code == version_code)
        )
        return result.scalar_one_or_none()

    async def get_active_version(self) -> DataVersion | None:
        """Get the currently active version."""
        result = await self.session.execute(
            select(DataVersion).where(DataVersion.is_active.is_(True))
        )
        return result.scalar_one_or_none()

    async def create_version(
        self,
        version_code: str,
        version_name: str,
        version_type: str = "snapshot",
        base_version_id: int | None = None,
        source_task_id: int | None = None,
        description: str | None = None,
    ) -> DataVersion:
        """Create a new data version."""
        version = DataVersion(
            version_code=version_code,
            version_name=version_name,
            version_type=version_type,
            base_version_id=base_version_id,
            source_task_id=source_task_id,
            description=description,
            is_active=False,
            is_published=False,
        )
        self.session.add(version)
        await self.session.flush()
        return version

    async def update_statistics(
        self,
        version_id: int,
        total_talents: int,
        total_schools: int,
        total_works: int,
    ) -> DataVersion | None:
        """Update version statistics."""
        version = await self.get_by_id(version_id)
        if not version:
            return None

        version.total_talents = total_talents
        version.total_schools = total_schools
        version.total_works = total_works
        return version

    async def publish_version(
        self,
        version_id: int,
        published_by: int,
    ) -> DataVersion | None:
        """Publish a version (make it active)."""
        # Deactivate current active version
        active_version = await self.get_active_version()

        if active_version:
            active_version.is_active = False

        # Activate new version
        version = await self.get_by_id(version_id)
        if not version:
            return None

        version.is_active = True
        version.is_published = True
        version.published_at = datetime.now()
        version.published_by = published_by

        return version


class DataPublishRecordRepository:
    """Repository for DataPublishRecord operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_records(
        self,
        version_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[DataPublishRecord], int]:
        """List publish records with pagination."""
        query = select(DataPublishRecord)

        if version_id:
            query = query.where(DataPublishRecord.version_id == version_id)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Paginate
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size).order_by(DataPublishRecord.publish_id.desc())

        result = await self.session.execute(query)
        records = list(result.scalars().all())

        return records, total

    async def create_record(
        self,
        version_id: int,
        action: str,
        operated_by: int,
        previous_version_id: int | None = None,
        notes: str | None = None,
    ) -> DataPublishRecord:
        """Create a publish record."""
        record = DataPublishRecord(
            version_id=version_id,
            action=action,
            previous_version_id=previous_version_id,
            operated_by=operated_by,
            operated_at=datetime.now(),
            notes=notes,
        )
        self.session.add(record)
        await self.session.flush()
        return record


class DataCorrectionRepository:
    """Repository for DataCorrectionRecord operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_corrections(
        self,
        target_type: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[DataCorrectionRecord], int]:
        """List corrections with pagination."""
        query = select(DataCorrectionRecord)

        if target_type:
            query = query.where(DataCorrectionRecord.target_type == target_type)
        if status:
            query = query.where(DataCorrectionRecord.status == status)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Paginate
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size).order_by(DataCorrectionRecord.correction_id.desc())

        result = await self.session.execute(query)
        corrections = list(result.scalars().all())

        return corrections, total

    async def get_by_id(self, correction_id: int) -> DataCorrectionRecord | None:
        """Get correction by ID."""
        result = await self.session.execute(
            select(DataCorrectionRecord).where(DataCorrectionRecord.correction_id == correction_id)
        )
        return result.scalar_one_or_none()

    async def create_correction(
        self,
        target_type: str,
        target_id: int,
        field_name: str,
        original_value: str | None,
        corrected_value: str | None,
        correction_type: str,
        corrected_by: int,
        reason: str | None = None,
        source: str | None = None,
    ) -> DataCorrectionRecord:
        """Create a correction record."""
        correction = DataCorrectionRecord(
            target_type=target_type,
            target_id=target_id,
            field_name=field_name,
            original_value=original_value,
            corrected_value=corrected_value,
            correction_type=correction_type,
            reason=reason,
            source=source,
            corrected_by=corrected_by,
            status="applied",
        )
        self.session.add(correction)
        await self.session.flush()
        return correction

    async def revert_correction(self, correction_id: int) -> DataCorrectionRecord | None:
        """Revert a correction."""
        correction = await self.get_by_id(correction_id)
        if not correction:
            return None

        correction.status = "reverted"
        return correction


class DataQualityRepository:
    """Repository for DataQualitySummary operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_latest_summary(self, version_id: int | None = None) -> DataQualitySummary | None:
        """Get the latest quality summary."""
        query = select(DataQualitySummary)

        if version_id:
            query = query.where(DataQualitySummary.version_id == version_id)

        query = query.order_by(DataQualitySummary.summary_date.desc()).limit(1)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_summaries(
        self,
        version_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[DataQualitySummary], int]:
        """List quality summaries with pagination."""
        query = select(DataQualitySummary)

        if version_id:
            query = query.where(DataQualitySummary.version_id == version_id)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Paginate
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size).order_by(DataQualitySummary.summary_date.desc())

        result = await self.session.execute(query)
        summaries = list(result.scalars().all())

        return summaries, total

    async def create_summary(
        self,
        version_id: int,
        summary_date: datetime,
        talent_total: int = 0,
        talent_with_orcid: int = 0,
        talent_with_affiliation: int = 0,
        talent_with_works: int = 0,
        talent_completeness_avg: int = 0,
        school_total: int = 0,
        school_with_ror: int = 0,
        school_with_country: int = 0,
        work_total: int = 0,
        work_with_doi: int = 0,
        tech_tag_total: int = 0,
        tech_tag_confirmed: int = 0,
        tech_tag_auto_identified: int = 0,
        tech_tag_pending_confirm: int = 0,
        issues_critical: int = 0,
        issues_warning: int = 0,
        issues_info: int = 0,
        details: dict | None = None,
    ) -> DataQualitySummary:
        """Create a quality summary."""
        summary = DataQualitySummary(
            version_id=version_id,
            summary_date=summary_date,
            talent_total=talent_total,
            talent_with_orcid=talent_with_orcid,
            talent_with_affiliation=talent_with_affiliation,
            talent_with_works=talent_with_works,
            talent_completeness_avg=talent_completeness_avg,
            school_total=school_total,
            school_with_ror=school_with_ror,
            school_with_country=school_with_country,
            work_total=work_total,
            work_with_doi=work_with_doi,
            tech_tag_total=tech_tag_total,
            tech_tag_confirmed=tech_tag_confirmed,
            tech_tag_auto_identified=tech_tag_auto_identified,
            tech_tag_pending_confirm=tech_tag_pending_confirm,
            issues_critical=issues_critical,
            issues_warning=issues_warning,
            issues_info=issues_info,
            details=details,
        )
        self.session.add(summary)
        await self.session.flush()
        return summary
