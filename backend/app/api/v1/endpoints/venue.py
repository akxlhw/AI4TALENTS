"""
Venue configuration API endpoints.
顶会顶刊配置管理接口
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.tech_domain import TechDomain
from app.models.venue import Venue, VenueTechBinding
from app.repositories.venue_repository import VenueRepository, VenueTechBindingRepository
from app.schemas.venue import (
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

router = APIRouter(prefix="/venues", tags=["Venue Configuration"])


# ============================================
# Batch operations (must be before /{venue_id} routes)
# ============================================

@router.post(
    "/bindings/batch",
    summary="批量更新技术领域绑定",
    description="批量更新指定技术领域的 Venue 绑定启用状态。传入的 venue_ids 会被标记为启用，该技术领域的其他绑定会被标记为禁用。"
)
async def batch_create_bindings(
    data: VenueTechBindingBatchCreate,
    session: AsyncSession = Depends(get_async_session)
):
    """更新技术领域的Venue绑定启用状态

    传入的 venue_ids 会被标记为启用(is_enabled=True)，
    该技术领域的其他绑定会被标记为禁用(is_enabled=False)
    """
    try:
        binding_repo = VenueTechBindingRepository(session)

        # Check tech domain exists
        tech_result = await session.execute(
            select(TechDomain).where(TechDomain.tech_domain_id == data.tech_domain_id)
        )
        tech_domain = tech_result.scalar_one_or_none()
        if not tech_domain:
            raise HTTPException(status_code=404, detail="Tech domain not found")

        # 获取该技术领域的所有绑定
        all_bindings = await binding_repo.get_by_tech_domain(data.tech_domain_id)

        selected_venue_ids = set(data.venue_ids)

        # 更新绑定状态
        updated_bindings = []
        for binding in all_bindings:
            new_enabled = binding.venue_id in selected_venue_ids
            if binding.is_enabled != new_enabled:
                binding.is_enabled = new_enabled
                updated_bindings.append(binding)

        await session.commit()

        # 同步更新 TechDomain.collect_sources 字段
        # 只包含启用的 venues
        enabled_bindings = await binding_repo.get_list_with_venue(data.tech_domain_id, is_enabled=True)
        collect_sources = [
            {
                "id": b.venue.openalex_source_id or b.venue.venue_code,
                "name": b.venue.venue_name,
                "type": b.venue.venue_type
            }
            for b in enabled_bindings if b.venue
        ]
        tech_domain.collect_sources = collect_sources
        await session.commit()

        # 返回更新后的绑定数量
        enabled_count = len([b for b in all_bindings if b.is_enabled])
        return {
            "message": "配置更新成功",
            "total_bindings": len(all_bindings),
            "enabled_bindings": enabled_count,
            "updated_count": len(updated_bindings)
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================
# Venue CRUD
# ============================================

@router.get(
    "",
    response_model=VenueListResponse,
    summary="获取Venue列表",
    description="获取顶会顶刊列表，支持按类型、启用状态筛选，支持关键词搜索和分页。"
)
async def list_venues(
    venue_type: str | None = Query(None, description="Venue类型: conference/journal/workshop"),
    is_enabled: bool | None = Query(None, description="是否启用"),
    keyword: str | None = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    session: AsyncSession = Depends(get_async_session)
):
    """获取Venue列表"""
    repo = VenueRepository(session)
    venues, total = await repo.get_list(
        venue_type=venue_type,
        is_enabled=is_enabled,
        keyword=keyword,
        page=page,
        page_size=page_size
    )
    return VenueListResponse(
        total=total,
        items=[VenueResponse.model_validate(v) for v in venues]
    )


@router.post(
    "",
    response_model=VenueResponse,
    summary="创建Venue",
    description="创建新的顶会顶刊配置。venue_code 必须唯一，openalex_source_id 如有也需唯一。"
)
async def create_venue(
    data: VenueCreate,
    session: AsyncSession = Depends(get_async_session)
):
    """创建Venue"""
    repo = VenueRepository(session)

    # Check if code exists
    existing = await repo.get_by_code(data.venue_code)
    if existing:
        raise HTTPException(status_code=400, detail="Venue code already exists")

    # Check if openalex_source_id exists
    if data.openalex_source_id:
        existing = await repo.get_by_openalex_id(data.openalex_source_id)
        if existing:
            raise HTTPException(status_code=400, detail="OpenAlex Source ID already exists")

    venue = Venue(**data.model_dump())
    venue = await repo.create(venue)
    await session.commit()

    return VenueResponse.model_validate(venue)


@router.get(
    "/{venue_id}",
    response_model=VenueResponse,
    summary="获取Venue详情",
    description="根据 ID 获取单个顶会顶刊的详细信息。"
)
async def get_venue(
    venue_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """获取Venue详情"""
    repo = VenueRepository(session)
    venue = await repo.get_by_id(venue_id)
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    return VenueResponse.model_validate(venue)


@router.put(
    "/{venue_id}",
    response_model=VenueResponse,
    summary="更新Venue",
    description="更新指定顶会顶刊的信息。只更新请求中提供的字段。"
)
async def update_venue(
    venue_id: int,
    data: VenueUpdate,
    session: AsyncSession = Depends(get_async_session)
):
    """更新Venue"""
    repo = VenueRepository(session)
    venue = await repo.get_by_id(venue_id)
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(venue, key, value)

    venue = await repo.update(venue)
    await session.commit()

    return VenueResponse.model_validate(venue)


@router.delete(
    "/{venue_id}",
    summary="删除Venue",
    description="删除指定的顶会顶刊。如果存在技术领域绑定则无法删除，需先删除绑定。"
)
async def delete_venue(
    venue_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """删除Venue"""
    repo = VenueRepository(session)
    binding_repo = VenueTechBindingRepository(session)

    # Check if has bindings
    bindings = await binding_repo.get_by_venue(venue_id)
    if bindings:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete venue with {len(bindings)} bindings. Delete bindings first."
        )

    success = await repo.delete(venue_id)
    if not success:
        raise HTTPException(status_code=404, detail="Venue not found")

    await session.commit()
    return {"message": "Venue deleted successfully"}


# ============================================
# Venue-TechDomain Binding
# ============================================

@router.get(
    "/{venue_id}/bindings",
    response_model=VenueTechBindingListResponse,
    summary="获取Venue的技术领域绑定",
    description="获取指定 Venue 关联的所有技术领域绑定列表。"
)
async def get_venue_bindings(
    venue_id: int,
    is_enabled: bool | None = Query(None, description="按启用状态筛选"),
    session: AsyncSession = Depends(get_async_session)
):
    """获取Venue的所有技术领域绑定"""
    repo = VenueTechBindingRepository(session)
    bindings = await repo.get_by_venue(venue_id, is_enabled)

    return VenueTechBindingListResponse(
        total=len(bindings),
        items=[VenueTechBindingResponse.model_validate(b) for b in bindings]
    )


@router.post(
    "/bindings",
    response_model=VenueTechBindingResponse,
    summary="创建Venue-TechDomain绑定",
    description="创建顶会顶刊与技术领域的关联绑定。同一 Venue 和 TechDomain 组合只能有一个绑定。"
)
async def create_binding(
    data: VenueTechBindingCreate,
    session: AsyncSession = Depends(get_async_session)
):
    """创建Venue-TechDomain绑定"""
    venue_repo = VenueRepository(session)
    binding_repo = VenueTechBindingRepository(session)

    # Check venue exists
    venue = await venue_repo.get_by_id(data.venue_id)
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    # Check tech domain exists
    tech_result = await session.execute(
        select(TechDomain).where(TechDomain.tech_domain_id == data.tech_domain_id)
    )
    if not tech_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Tech domain not found")

    # Check if binding already exists
    existing = await binding_repo.get_by_venue_and_tech(data.venue_id, data.tech_domain_id)
    if existing:
        raise HTTPException(status_code=400, detail="Binding already exists")

    binding = VenueTechBinding(**data.model_dump())
    binding = await binding_repo.create(binding)
    await session.commit()

    return VenueTechBindingResponse.model_validate(binding)


@router.put(
    "/bindings/{binding_id}",
    response_model=VenueTechBindingResponse,
    summary="更新绑定",
    description="更新指定的 Venue-TechDomain 绑定信息，如优先级或启用状态。"
)
async def update_binding(
    binding_id: int,
    data: VenueTechBindingUpdate,
    session: AsyncSession = Depends(get_async_session)
):
    """更新绑定"""
    repo = VenueTechBindingRepository(session)
    binding = await repo.get_by_id(binding_id)
    if not binding:
        raise HTTPException(status_code=404, detail="Binding not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(binding, key, value)

    binding = await repo.update(binding)
    await session.commit()

    return VenueTechBindingResponse.model_validate(binding)


@router.delete(
    "/bindings/{binding_id}",
    summary="删除绑定",
    description="删除指定的 Venue-TechDomain 绑定关系。"
)
async def delete_binding(
    binding_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """删除绑定"""
    repo = VenueTechBindingRepository(session)
    success = await repo.delete(binding_id)
    if not success:
        raise HTTPException(status_code=404, detail="Binding not found")

    await session.commit()
    return {"message": "Binding deleted successfully"}


# ============================================
# Tech Domain Bindings
# ============================================

@router.get(
    "/tech-domains/{tech_domain_id}/bindings",
    response_model=VenueTechBindingListResponse,
    summary="获取技术领域的Venue绑定",
    description="获取指定技术领域关联的所有顶会顶刊绑定列表，支持按启用状态筛选。"
)
async def get_tech_domain_bindings(
    tech_domain_id: int,
    is_enabled: bool | None = Query(None, description="按启用状态筛选"),
    session: AsyncSession = Depends(get_async_session)
):
    """获取技术领域的所有Venue绑定"""
    repo = VenueTechBindingRepository(session)
    bindings = await repo.get_list_with_venue(tech_domain_id, is_enabled)

    return VenueTechBindingListResponse(
        total=len(bindings),
        items=[
            VenueTechBindingResponse.model_validate(b) for b in bindings
        ]
    )


# ============================================
# Migration
# ============================================

@router.post(
    "/migrate-collect-sources",
    response_model=MigrateCollectSourcesResponse,
    summary="迁移采集源数据",
    description="将 TechDomain.collect_sources JSON 字段中的采集源迁移到 Venue 表，并创建绑定关系。支持 dry_run 模式预览。"
)
async def migrate_collect_sources(
    data: MigrateCollectSourcesRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """迁移 TechDomain.collect_sources JSON 到 Venue 表"""
    venue_repo = VenueRepository(session)
    binding_repo = VenueTechBindingRepository(session)

    # Get tech domain
    tech_result = await session.execute(
        select(TechDomain).where(TechDomain.tech_domain_id == data.tech_domain_id)
    )
    tech_domain = tech_result.scalar_one_or_none()
    if not tech_domain:
        raise HTTPException(status_code=404, detail="Tech domain not found")

    collect_sources = tech_domain.collect_sources or []
    if not collect_sources:
        return MigrateCollectSourcesResponse(
            tech_domain_id=data.tech_domain_id,
            tech_domain_name=tech_domain.domain_name,
            venues_found=0,
            venues_created=0,
            bindings_created=0,
            venues=[],
            message="No collect_sources to migrate"
        )

    venues_created = 0
    bindings_created = 0
    venue_infos = []

    for source in collect_sources:
        source_id = source.get("id")
        source_name = source.get("name", source_id)
        source_type = source.get("type", "conference")

        if not source_id:
            continue

        # Check if venue exists by openalex_source_id
        venue = None
        if source_id:
            venue = await venue_repo.get_by_openalex_id(source_id)

        # Check by code
        if not venue:
            venue = await venue_repo.get_by_code(source_id)

        if not venue and not data.dry_run:
            # Create new venue
            venue = Venue(
                venue_code=source_id,
                venue_name=source_name,
                openalex_source_id=source_id,
                venue_type=source_type,
                is_enabled=True
            )
            venue = await venue_repo.create(venue)
            venues_created += 1

        if venue:
            venue_infos.append({
                "venue_id": venue.venue_id,
                "venue_code": venue.venue_code,
                "venue_name": venue.venue_name,
                "openalex_source_id": venue.openalex_source_id,
                "is_new": venues_created > 0
            })

            # Create binding if not exists
            if not data.dry_run:
                existing_binding = await binding_repo.get_by_venue_and_tech(
                    venue.venue_id, data.tech_domain_id
                )
                if not existing_binding:
                    binding = VenueTechBinding(
                        venue_id=venue.venue_id,
                        tech_domain_id=data.tech_domain_id,
                        priority=0,
                        is_enabled=True
                    )
                    await binding_repo.create(binding)
                    bindings_created += 1

    if not data.dry_run:
        await session.commit()

    return MigrateCollectSourcesResponse(
        tech_domain_id=data.tech_domain_id,
        tech_domain_name=tech_domain.domain_name,
        venues_found=len(collect_sources),
        venues_created=venues_created,
        bindings_created=bindings_created,
        venues=venue_infos,
        message=f"Migration {'simulated' if data.dry_run else 'completed'}: {venues_created} venues, {bindings_created} bindings"
    )
