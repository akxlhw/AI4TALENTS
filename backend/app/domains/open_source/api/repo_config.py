"""
Open Source — Repo Config endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.exceptions import NotFoundError
from app.domains.open_source.api.auth import get_current_user, require_super_admin
from app.domains.open_source.schemas.open_source import (
    OSBatchRepoCreateRequest,
    OSBatchRepoCreateResponse,
    OSPurgePreview,
    OSRepoConfigCreate,
    OSRepoConfigResponse,
    OSRepoConfigUpdate,
)
from app.domains.open_source.services.open_source_service import OpenSourceService
from app.domains.shared.schemas.common import PaginatedResponse, SuccessResponse
from app.domains.shared.services.audit_service import AuditService

router = APIRouter(prefix="/open-source", tags=["Open Source Talent"])


@router.get("/repo-configs", response_model=PaginatedResponse[OSRepoConfigResponse])
async def list_repo_configs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    tech_elements: list[str] | None = Query(None),
    is_active: bool | None = Query(None),
    collect_enabled: bool | None = Query(None),
    sort_by: str = Query("id_desc", description="id_desc | stars"),
    collected_only: bool = Query(False, description="Only repos with completed collect tasks"),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    service = OpenSourceService(session)
    items, total = await service.list_repo_configs(
        page=page,
        page_size=page_size,
        tech_elements=tech_elements,
        is_active=is_active,
        collect_enabled=collect_enabled,
        sort_by=sort_by,
        collected_only=collected_only,
    )
    return PaginatedResponse.create(
        items=[OSRepoConfigResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/repo-configs", response_model=OSRepoConfigResponse, status_code=201)
async def create_repo_config(
    data: OSRepoConfigCreate,
    session: AsyncSession = Depends(get_async_session),
    user: dict = Depends(require_super_admin),
):
    service = OpenSourceService(session)
    config = await service.create_repo_config(
        repo_full_name=data.repo_full_name,
        tech_element=data.tech_element,
        display_name=data.display_name,
        description=data.description,
        tech_direction_id=data.tech_direction_id,
        language=data.language,
        notes=data.notes,
        created_by=int(user.get("sub")) if user.get("sub") else None,
    )
    return OSRepoConfigResponse.model_validate(config)


@router.post(
    "/repo-configs/batch",
    response_model=OSBatchRepoCreateResponse,
    status_code=201,
)
async def batch_create_repo_configs(
    data: OSBatchRepoCreateRequest,
    session: AsyncSession = Depends(get_async_session),
    user: dict = Depends(require_super_admin),
):
    """Batch create repo configs from GitHub URLs.

    Each input is parsed (URL or owner/repo), then GitHub API is called
    to auto-fill display name, description, language, and stars. Existing
    repos are skipped, invalid repos go to failed.
    """
    service = OpenSourceService(session)
    result = await service.batch_create_repo_configs(
        repo_inputs=data.repo_inputs,
        tech_element=data.tech_element,
        created_by=int(user.get("sub")) if user.get("sub") else None,
    )
    return OSBatchRepoCreateResponse(**result)


@router.get("/repo-configs/{repo_config_id}", response_model=OSRepoConfigResponse)
async def get_repo_config(
    repo_config_id: int,
    session: AsyncSession = Depends(get_async_session),
    _user: dict = Depends(get_current_user),
):
    service = OpenSourceService(session)
    config = await service.get_repo_config(repo_config_id)
    if not config:
        raise NotFoundError("Repo config", repo_config_id)
    return OSRepoConfigResponse.model_validate(config)


@router.put("/repo-configs/{repo_config_id}", response_model=OSRepoConfigResponse)
async def update_repo_config(
    repo_config_id: int,
    data: OSRepoConfigUpdate,
    session: AsyncSession = Depends(get_async_session),
    _user: dict = Depends(require_super_admin),
):
    service = OpenSourceService(session)
    config = await service.update_repo_config(repo_config_id, data.model_dump(exclude_unset=True))
    if not config:
        raise NotFoundError("Repo config", repo_config_id)
    return OSRepoConfigResponse.model_validate(config)


@router.delete("/repo-configs/{repo_config_id}")
async def delete_repo_config(
    repo_config_id: int,
    session: AsyncSession = Depends(get_async_session),
    _user: dict = Depends(require_super_admin),
):
    service = OpenSourceService(session)
    success = await service.delete_repo_config(repo_config_id)
    if not success:
        raise NotFoundError("Repo config", repo_config_id)
    return SuccessResponse(message="Deleted")


@router.post("/repo-configs/{repo_config_id}/purge", response_model=OSPurgePreview)
async def purge_repo_config_data(
    repo_config_id: int,
    dry_run: bool = Query(True, description="仅预览影响范围，不执行删除"),
    delete_config: bool = Query(False, description="执行删除时同时删除仓库配置行"),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_super_admin),
    request: Request = None,  # type: ignore[assignment]
) -> OSPurgePreview:
    """清理仓库采集数据：删除该仓库的贡献记录与独占人才，保护共享/收藏/入池人才。"""
    service = OpenSourceService(session)
    if dry_run:
        return await service.preview_repo_purge(repo_config_id)

    result = await service.purge_repo(repo_config_id, delete_config=delete_config)
    await AuditService.log_data_operation(
        user_id=int(current_user["sub"]) if current_user.get("sub") else None,
        operation="purge",
        resource_type="os_repo_config",
        resource_id=str(repo_config_id),
        status="success",
        user_ip=request.client.host if request and request.client else None,
        request_id=getattr(request.state, "request_id", None) if request else None,
        detail={
            "repo_full_name": result.repo_full_name,
            "delete_config": delete_config,
            "contributions": result.contributions,
            "developers_total": result.developers_total,
            "developers_exclusive": result.developers_exclusive,
            "developers_protected": result.developers_protected,
            "developers_shared": result.developers_shared,
            "skills": result.skills,
            "embeddings": result.embeddings,
            "raw": result.raw,
        },
    )
    return result
