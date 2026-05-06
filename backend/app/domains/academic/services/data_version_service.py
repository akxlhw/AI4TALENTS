"""
Data Version Service — 封装数据版本管理业务逻辑

遵循 Endpoint → Service → Repository 分层架构
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.academic.models.sync import (
    DataCorrectionRecord,
    DataPublishRecord,
    DataQualitySummary,
    DataVersion,
)
from app.domains.academic.repositories.data_version_repository import (
    DataCorrectionRepository,
    DataPublishRecordRepository,
    DataQualityRepository,
    DataVersionRepository,
)
from app.domains.academic.schemas.data_version import QualityMetricsResponse


class DataVersionService:
    """Service for data version management operations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.version_repo = DataVersionRepository(session)
        self.publish_repo = DataPublishRecordRepository(session)
        self.correction_repo = DataCorrectionRepository(session)
        self.quality_repo = DataQualityRepository(session)

    # ============ Version Operations ============

    async def list_versions(
        self,
        is_published: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[DataVersion], int]:
        """List data versions with pagination."""
        return await self.version_repo.list_versions(
            is_published=is_published,
            page=page,
            page_size=page_size,
        )

    async def get_active_version(self) -> DataVersion | None:
        """Get the currently active version."""
        return await self.version_repo.get_active_version()

    async def get_version_by_id(self, version_id: int) -> DataVersion | None:
        """Get data version by ID."""
        return await self.version_repo.get_by_id(version_id)

    async def create_version(
        self,
        version_code: str,
        version_name: str,
        version_type: str,
        base_version_id: int | None,
        source_task_id: int | None,
        description: str | None,
    ) -> DataVersion:
        """Create a new data version."""
        return await self.version_repo.create_version_and_commit(
            version_code=version_code,
            version_name=version_name,
            version_type=version_type,
            base_version_id=base_version_id,
            source_task_id=source_task_id,
            description=description,
        )

    async def check_version_code_exists(self, version_code: str) -> bool:
        """Check if a version code already exists."""
        existing = await self.version_repo.get_by_code(version_code)
        return existing is not None

    async def publish_version(
        self,
        version_id: int,
        published_by: int,
        notes: str | None,
    ) -> DataVersion | None:
        """Publish a version to make it active."""
        active_version = await self.version_repo.get_active_version()
        previous_version_id = active_version.version_id if active_version else None

        return await self.version_repo.publish_version_with_record(
            version_id=version_id,
            published_by=published_by,
            previous_version_id=previous_version_id,
            notes=notes,
        )

    # ============ Publish Record Operations ============

    async def list_publish_records(
        self,
        version_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[DataPublishRecord], int]:
        """List publish records with pagination."""
        return await self.publish_repo.list_records(
            version_id=version_id,
            page=page,
            page_size=page_size,
        )

    # ============ Correction Operations ============

    async def list_corrections(
        self,
        target_type: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[DataCorrectionRecord], int]:
        """List corrections with pagination."""
        return await self.correction_repo.list_corrections(
            target_type=target_type,
            status=status,
            page=page,
            page_size=page_size,
        )

    async def create_correction(
        self,
        target_type: str,
        target_id: int,
        field_name: str,
        original_value: str | None,
        corrected_value: str | None,
        correction_type: str,
        corrected_by: int,
        reason: str | None,
        source: str | None,
    ) -> DataCorrectionRecord:
        """Create a correction record."""
        return await self.correction_repo.create_correction_and_commit(
            target_type=target_type,
            target_id=target_id,
            field_name=field_name,
            original_value=original_value,
            corrected_value=corrected_value,
            correction_type=correction_type,
            corrected_by=corrected_by,
            reason=reason,
            source=source,
        )

    async def revert_correction(
        self,
        correction_id: int,
    ) -> DataCorrectionRecord | None:
        """Revert a correction."""
        return await self.correction_repo.revert_correction_and_commit(correction_id)

    # ============ Quality Operations ============

    async def get_quality_summary(
        self,
        version_id: int | None = None,
    ) -> DataQualitySummary | None:
        """Get the latest quality summary for a version."""
        if not version_id:
            active = await self.version_repo.get_active_version()
            if active:
                version_id = active.version_id
        return await self.quality_repo.get_latest_summary(version_id)

    async def get_quality_metrics(self) -> QualityMetricsResponse:
        """Get computed quality metrics for dashboard."""
        active = await self.version_repo.get_active_version()
        if not active:
            raise ValueError("No active version found")

        summary = await self.quality_repo.get_latest_summary(active.version_id)
        if not summary:
            return QualityMetricsResponse(
                talent_total=0,
                talent_orcid_rate=0.0,
                talent_affiliation_rate=0.0,
                talent_works_rate=0.0,
                talent_completeness_avg=0.0,
                school_total=0,
                school_ror_rate=0.0,
                school_country_rate=0.0,
                work_total=0,
                work_doi_rate=0.0,
                tech_tag_total=0,
                tech_tag_confirmed_rate=0.0,
                tech_tag_auto_rate=0.0,
                tech_tag_pending=0,
                issues_critical=0,
                issues_warning=0,
                issues_info=0,
            )

        # Calculate rates
        talent_total = summary.talent_total or 1
        school_total = summary.school_total or 1
        work_total = summary.work_total or 1
        tech_tag_total = summary.tech_tag_total or 1

        return QualityMetricsResponse(
            talent_total=summary.talent_total,
            talent_orcid_rate=round(summary.talent_with_orcid / talent_total * 100, 2),
            talent_affiliation_rate=round(summary.talent_with_affiliation / talent_total * 100, 2),
            talent_works_rate=round(summary.talent_with_works / talent_total * 100, 2),
            talent_completeness_avg=summary.talent_completeness_avg,
            school_total=summary.school_total,
            school_ror_rate=round(summary.school_with_ror / school_total * 100, 2),
            school_country_rate=round(summary.school_with_country / school_total * 100, 2),
            work_total=summary.work_total,
            work_doi_rate=round(summary.work_with_doi / work_total * 100, 2),
            tech_tag_total=summary.tech_tag_total,
            tech_tag_confirmed_rate=round(summary.tech_tag_confirmed / tech_tag_total * 100, 2),
            tech_tag_auto_rate=round(summary.tech_tag_auto_identified / tech_tag_total * 100, 2),
            tech_tag_pending=summary.tech_tag_pending_confirm,
            issues_critical=summary.issues_critical,
            issues_warning=summary.issues_warning,
            issues_info=summary.issues_info,
        )
