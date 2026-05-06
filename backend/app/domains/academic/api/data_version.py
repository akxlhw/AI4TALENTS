"""
Data version management API endpoints.
数据版本管理相关接口
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.academic.schemas.data_version import (
    ACTION_TYPE_OPTIONS,
    CORRECTION_TYPE_OPTIONS,
    TARGET_TYPE_OPTIONS,
    VERSION_TYPE_OPTIONS,
    CorrectionListResponse,
    CorrectionResponse,
    CreateCorrectionRequest,
    CreateVersionRequest,
    DataVersionListResponse,
    DataVersionResponse,
    PublishRecordListResponse,
    PublishRecordResponse,
    PublishVersionRequest,
    QualityMetricsResponse,
    QualitySummaryResponse,
)
from app.domains.academic.services.data_version_service import DataVersionService
from app.domains.shared.api.auth import require_admin, require_user

router = APIRouter(prefix="/data-version", tags=["Data Version Management"])


# ============ Version Endpoints ============


@router.get(
    "/versions",
    response_model=DataVersionListResponse,
    summary="获取数据版本列表",
    description="获取所有数据版本（分页）",
)
async def list_versions(
    is_published: bool | None = Query(None, description="按发布状态筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin),
):
    """List data versions."""
    service = DataVersionService(session)
    versions, total = await service.list_versions(
        is_published=is_published,
        page=page,
        page_size=page_size,
    )

    items = [DataVersionResponse.model_validate(v) for v in versions]
    return DataVersionListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get(
    "/versions/active",
    response_model=DataVersionResponse,
    summary="获取当前生效版本",
    description="获取当前正在使用的数据版本",
)
async def get_active_version(
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_user),
):
    """Get the currently active version."""
    service = DataVersionService(session)
    version = await service.get_active_version()

    if not version:
        raise HTTPException(status_code=404, detail="No active version found")

    return DataVersionResponse.model_validate(version)


@router.post(
    "/versions",
    response_model=DataVersionResponse,
    summary="创建数据版本",
    description="创建新的数据版本快照",
)
async def create_version(
    request: CreateVersionRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin),
):
    """Create a new data version."""
    service = DataVersionService(session)

    if await service.check_version_code_exists(request.version_code):
        raise HTTPException(status_code=400, detail="Version code already exists")

    version = await service.create_version(
        version_code=request.version_code,
        version_name=request.version_name,
        version_type=request.version_type,
        base_version_id=request.base_version_id,
        source_task_id=request.source_task_id,
        description=request.description,
    )

    return DataVersionResponse.model_validate(version)


@router.get(
    "/versions/{version_id}",
    response_model=DataVersionResponse,
    summary="获取版本详情",
    description="获取指定数据版本的详细信息",
)
async def get_version(
    version_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin),
):
    """Get data version details."""
    service = DataVersionService(session)
    version = await service.get_version_by_id(version_id)

    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    return DataVersionResponse.model_validate(version)


@router.post(
    "/versions/{version_id}/publish",
    response_model=DataVersionResponse,
    summary="发布版本",
    description="发布指定版本，使其成为当前生效版本",
)
async def publish_version(
    version_id: int,
    request: PublishVersionRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin),
):
    """Publish a version to make it active."""
    service = DataVersionService(session)

    version = await service.publish_version(
        version_id=version_id,
        published_by=current_user["user_id"],
        notes=request.notes,
    )

    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    return DataVersionResponse.model_validate(version)


# ============ Publish Record Endpoints ============


@router.get(
    "/publish-records",
    response_model=PublishRecordListResponse,
    summary="获取发布记录列表",
    description="获取数据发布操作记录",
)
async def list_publish_records(
    version_id: int | None = Query(None, description="按版本筛选"),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin),
):
    """List publish records."""
    service = DataVersionService(session)
    records, total = await service.list_publish_records(version_id=version_id)

    items = [PublishRecordResponse.model_validate(r) for r in records]
    return PublishRecordListResponse(items=items, total=total)


# ============ Correction Endpoints ============


@router.get(
    "/corrections",
    response_model=CorrectionListResponse,
    summary="获取纠偏记录列表",
    description="获取数据纠偏记录（分页）",
)
async def list_corrections(
    target_type: str | None = Query(None, description="按目标类型筛选"),
    status: str | None = Query(None, description="按状态筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin),
):
    """List corrections."""
    service = DataVersionService(session)
    corrections, total = await service.list_corrections(
        target_type=target_type,
        status=status,
        page=page,
        page_size=page_size,
    )

    items = [CorrectionResponse.model_validate(c) for c in corrections]
    return CorrectionListResponse(items=items, total=total, page=page, page_size=page_size)


@router.post(
    "/corrections",
    response_model=CorrectionResponse,
    summary="创建纠偏记录",
    description="记录数据纠偏操作",
)
async def create_correction(
    request: CreateCorrectionRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin),
):
    """Create a correction record."""
    service = DataVersionService(session)

    correction = await service.create_correction(
        target_type=request.target_type,
        target_id=request.target_id,
        field_name=request.field_name,
        original_value=request.original_value,
        corrected_value=request.corrected_value,
        correction_type=request.correction_type,
        corrected_by=current_user["user_id"],
        reason=request.reason,
        source=request.source,
    )

    return CorrectionResponse.model_validate(correction)


@router.post(
    "/corrections/{correction_id}/revert",
    response_model=CorrectionResponse,
    summary="撤销纠偏",
    description="撤销之前的数据纠偏操作",
)
async def revert_correction(
    correction_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin),
):
    """Revert a correction."""
    service = DataVersionService(session)
    correction = await service.revert_correction(correction_id)

    if not correction:
        raise HTTPException(status_code=404, detail="Correction not found")

    return CorrectionResponse.model_validate(correction)


# ============ Quality Endpoints ============


@router.get(
    "/quality/summary",
    response_model=QualitySummaryResponse,
    summary="获取质量摘要",
    description="获取最新的数据质量摘要",
)
async def get_quality_summary(
    version_id: int | None = Query(None, description="指定版本ID"),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin),
):
    """Get the latest quality summary."""
    service = DataVersionService(session)

    summary = await service.get_quality_summary(version_id)

    if not summary:
        raise HTTPException(status_code=404, detail="No quality summary found")

    return QualitySummaryResponse.model_validate(summary)


@router.get(
    "/quality/metrics",
    response_model=QualityMetricsResponse,
    summary="获取质量指标",
    description="获取数据质量指标概览",
)
async def get_quality_metrics(
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin),
):
    """Get quality metrics for dashboard."""
    service = DataVersionService(session)

    try:
        return await service.get_quality_metrics()
    except ValueError:
        raise HTTPException(status_code=404, detail="No active version found") from None


# ============ Options Endpoints ============


@router.get(
    "/options/version-types",
    response_model=list[dict[str, str]],
    summary="获取版本类型选项",
    description="获取所有可用的版本类型选项",
)
async def get_version_types():
    """Get version type options."""
    return VERSION_TYPE_OPTIONS


@router.get(
    "/options/action-types",
    response_model=list[dict[str, str]],
    summary="获取操作类型选项",
    description="获取所有可用的操作类型选项",
)
async def get_action_types():
    """Get action type options."""
    return ACTION_TYPE_OPTIONS


@router.get(
    "/options/correction-types",
    response_model=list[dict[str, str]],
    summary="获取纠偏类型选项",
    description="获取所有可用的纠偏类型选项",
)
async def get_correction_types():
    """Get correction type options."""
    return CORRECTION_TYPE_OPTIONS


@router.get(
    "/options/target-types",
    response_model=list[dict[str, str]],
    summary="获取目标类型选项",
    description="获取所有可用的目标类型选项",
)
async def get_target_types():
    """Get target type options."""
    return TARGET_TYPE_OPTIONS
