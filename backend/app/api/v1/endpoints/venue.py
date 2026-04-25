"""
Venue configuration API endpoints.
顶会顶刊配置管理接口
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.exceptions import BadRequestError, NotFoundError
from app.repositories.venue_repository import VenueRepository, VenueTechBindingRepository
from app.schemas.common import SuccessResponse
from app.schemas.venue import (
    BatchUpdateBindingsResponse,
    MigrateCollectSourcesRequest,
    MigrateCollectSourcesResponse,
    VenueCreate,
    VenueListResponse,
    VenueResponse,
    VenueTechBindingBatchCreate,
    VenueTechBindingCreate,
    VenueTechBindingListResponse,
    VenueTechBindingResponse,
    VenueTechBindingUpdate,
    VenueUpdate,
)
from app.services.venue_service import VenueService

router = APIRouter(prefix="/venues", tags=["Venue Configuration"])


# ============================================
# Batch operations (must be before /{venue_id} routes)
# ============================================


@router.post(
    "/bindings/batch",
    response_model=BatchUpdateBindingsResponse,
    summary="批量更新技术领域绑定",
    description="批量更新指定技术领域的 Venue 绑定启用状态。传入的 venue_ids 会被标记为启用，该技术领域的其他绑定会被标记为禁用。",
)
async def batch_create_bindings(
    data: VenueTechBindingBatchCreate, session: AsyncSession = Depends(get_async_session)
):
    """更新技术领域的Venue绑定启用状态

    传入的 venue_ids 会被标记为启用(is_enabled=True)，
    该技术领域的其他绑定会被标记为禁用(is_enabled=False)
    """
    service = VenueService(session)
    try:
        result = await service.batch_update_bindings(data)
        return BatchUpdateBindingsResponse(message="配置更新成功", **result)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise NotFoundError(str(e)) from e
        raise BadRequestError(str(e)) from e


# ============================================
# Venue CRUD
# ============================================


@router.get(
    "",
    response_model=VenueListResponse,
    summary="获取Venue列表",
    description="获取顶会顶刊列表，支持按类型、启用状态筛选，支持关键词搜索和分页。",
)
async def list_venues(
    venue_type: str | None = Query(None, description="Venue类型: conference/journal/workshop"),
    is_enabled: bool | None = Query(None, description="是否启用"),
    keyword: str | None = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    session: AsyncSession = Depends(get_async_session),
):
    """获取Venue列表"""
    repo = VenueRepository(session)
    venues, total = await repo.get_list(
        venue_type=venue_type,
        is_enabled=is_enabled,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return VenueListResponse(total=total, items=[VenueResponse.model_validate(v) for v in venues])


@router.post(
    "",
    response_model=VenueResponse,
    summary="创建Venue",
    description="创建新的顶会顶刊配置。venue_code 必须唯一，openalex_source_id 如有也需唯一。",
)
async def create_venue(data: VenueCreate, session: AsyncSession = Depends(get_async_session)):
    """创建Venue"""
    service = VenueService(session)
    try:
        venue = await service.create_venue(data)
        return VenueResponse.model_validate(venue)
    except ValueError as e:
        raise BadRequestError(str(e)) from e


@router.get(
    "/{venue_id}",
    response_model=VenueResponse,
    summary="获取Venue详情",
    description="根据 ID 获取单个顶会顶刊的详细信息。",
)
async def get_venue(venue_id: int, session: AsyncSession = Depends(get_async_session)):
    """获取Venue详情"""
    repo = VenueRepository(session)
    venue = await repo.get_by_id(venue_id)
    if not venue:
        raise NotFoundError("Venue not found")
    return VenueResponse.model_validate(venue)


@router.put(
    "/{venue_id}",
    response_model=VenueResponse,
    summary="更新Venue",
    description="更新指定顶会顶刊的信息。只更新请求中提供的字段。",
)
async def update_venue(
    venue_id: int, data: VenueUpdate, session: AsyncSession = Depends(get_async_session)
):
    """更新Venue"""
    service = VenueService(session)
    try:
        venue = await service.update_venue(venue_id, data)
        return VenueResponse.model_validate(venue)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise NotFoundError(str(e)) from e
        raise BadRequestError(str(e)) from e


@router.delete(
    "/{venue_id}",
    response_model=SuccessResponse,
    summary="删除Venue",
    description="删除指定的顶会顶刊。如果存在技术领域绑定则无法删除，需先删除绑定。",
)
async def delete_venue(venue_id: int, session: AsyncSession = Depends(get_async_session)):
    """删除Venue"""
    service = VenueService(session)
    try:
        await service.delete_venue(venue_id)
        return SuccessResponse(message="Venue deleted successfully")
    except ValueError as e:
        if "not found" in str(e).lower():
            raise NotFoundError(str(e)) from e
        raise BadRequestError(str(e)) from e


# ============================================
# Venue-TechDomain Binding
# ============================================


@router.get(
    "/{venue_id}/bindings",
    response_model=VenueTechBindingListResponse,
    summary="获取Venue的技术领域绑定",
    description="获取指定 Venue 关联的所有技术领域绑定列表。",
)
async def get_venue_bindings(
    venue_id: int,
    is_enabled: bool | None = Query(None, description="按启用状态筛选"),
    session: AsyncSession = Depends(get_async_session),
):
    """获取Venue的所有技术领域绑定"""
    repo = VenueTechBindingRepository(session)
    bindings = await repo.get_by_venue(venue_id, is_enabled)

    return VenueTechBindingListResponse(
        total=len(bindings), items=[VenueTechBindingResponse.model_validate(b) for b in bindings]
    )


@router.post(
    "/bindings",
    response_model=VenueTechBindingResponse,
    summary="创建Venue-TechDomain绑定",
    description="创建顶会顶刊与技术领域的关联绑定。同一 Venue 和 TechDomain 组合只能有一个绑定。",
)
async def create_binding(
    data: VenueTechBindingCreate, session: AsyncSession = Depends(get_async_session)
):
    """创建Venue-TechDomain绑定"""
    service = VenueService(session)
    try:
        binding = await service.create_binding(data)
        return VenueTechBindingResponse.model_validate(binding)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise NotFoundError(str(e)) from e
        raise BadRequestError(str(e)) from e


@router.put(
    "/bindings/{binding_id}",
    response_model=VenueTechBindingResponse,
    summary="更新绑定",
    description="更新指定的 Venue-TechDomain 绑定信息，如优先级或启用状态。",
)
async def update_binding(
    binding_id: int,
    data: VenueTechBindingUpdate,
    session: AsyncSession = Depends(get_async_session),
):
    """更新绑定"""
    service = VenueService(session)
    try:
        update_data = data.model_dump(exclude_unset=True)
        binding = await service.update_binding(binding_id, update_data)
        return VenueTechBindingResponse.model_validate(binding)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise NotFoundError(str(e)) from e
        raise BadRequestError(str(e)) from e


@router.delete(
    "/bindings/{binding_id}",
    response_model=SuccessResponse,
    summary="删除绑定",
    description="删除指定的 Venue-TechDomain 绑定关系。",
)
async def delete_binding(binding_id: int, session: AsyncSession = Depends(get_async_session)):
    """删除绑定"""
    service = VenueService(session)
    try:
        await service.delete_binding(binding_id)
        return SuccessResponse(message="Binding deleted successfully")
    except ValueError as e:
        if "not found" in str(e).lower():
            raise NotFoundError(str(e)) from e
        raise BadRequestError(str(e)) from e


# ============================================
# Tech Domain Bindings
# ============================================


@router.get(
    "/tech-domains/{tech_domain_id}/bindings",
    response_model=VenueTechBindingListResponse,
    summary="获取技术领域的Venue绑定",
    description="获取指定技术领域关联的所有顶会顶刊绑定列表，支持按启用状态筛选。",
)
async def get_tech_domain_bindings(
    tech_domain_id: int,
    is_enabled: bool | None = Query(None, description="按启用状态筛选"),
    session: AsyncSession = Depends(get_async_session),
):
    """获取技术领域的所有Venue绑定"""
    repo = VenueTechBindingRepository(session)
    bindings = await repo.get_list_with_venue(tech_domain_id, is_enabled)

    return VenueTechBindingListResponse(
        total=len(bindings), items=[VenueTechBindingResponse.model_validate(b) for b in bindings]
    )


# ============================================
# Migration
# ============================================


@router.post(
    "/migrate-collect-sources",
    response_model=MigrateCollectSourcesResponse,
    summary="迁移采集源数据",
    description="将 TechDomain.collect_sources JSON 字段中的采集源迁移到 Venue 表，并创建绑定关系。支持 dry_run 模式预览。",
)
async def migrate_collect_sources(
    data: MigrateCollectSourcesRequest, session: AsyncSession = Depends(get_async_session)
):
    """迁移 TechDomain.collect_sources JSON 到 Venue 表"""
    service = VenueService(session)
    try:
        result = await service.migrate_collect_sources(
            tech_domain_id=data.tech_domain_id, dry_run=data.dry_run
        )
        return MigrateCollectSourcesResponse(**result)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise NotFoundError(str(e)) from e
        raise BadRequestError(str(e)) from e
