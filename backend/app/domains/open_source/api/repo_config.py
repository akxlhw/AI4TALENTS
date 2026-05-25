"""
Open Source — Repo Config endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.exceptions import NotFoundError
from app.domains.open_source.api.auth import require_admin
from app.domains.open_source.schemas.open_source import (
    OSRepoConfigCreate,
    OSRepoConfigResponse,
    OSRepoConfigUpdate,
)
from app.domains.open_source.services.open_source_service import OpenSourceService
from app.domains.shared.schemas.common import PaginatedResponse, SuccessResponse

router = APIRouter(prefix="/open-source", tags=["Open Source Talent"])


@router.get("/repo-configs", response_model=PaginatedResponse[OSRepoConfigResponse])
async def list_repo_configs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    tech_element: str | None = Query(None),
    is_active: bool | None = Query(None),
    collect_enabled: bool | None = Query(None),
    sort_by: str = Query("id_desc", description="id_desc | stars"),
    collected_only: bool = Query(False, description="Only repos with completed collect tasks"),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin),
):
    service = OpenSourceService(session)
    items, total = await service.list_repo_configs(
        page=page,
        page_size=page_size,
        tech_element=tech_element,
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
    user: dict = Depends(require_admin),
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


@router.get("/repo-configs/{repo_config_id}", response_model=OSRepoConfigResponse)
async def get_repo_config(
    repo_config_id: int,
    session: AsyncSession = Depends(get_async_session),
    _user: dict = Depends(require_admin),
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
    _user: dict = Depends(require_admin),
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
    _user: dict = Depends(require_admin),
):
    service = OpenSourceService(session)
    success = await service.delete_repo_config(repo_config_id)
    if not success:
        raise NotFoundError("Repo config", repo_config_id)
    return SuccessResponse(message="Deleted")
