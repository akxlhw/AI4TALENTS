"""
Open Source — Favourite and Talent Pool endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.open_source.api.auth import get_current_user
from app.domains.open_source.schemas.open_source import (
    OSDeveloperSummary,
    OSFavoriteCreate,
    OSFavoriteIdsResponse,
    OSFavoriteResponse,
    OSFavoriteUpdate,
    OSPoolMemberResponse,
    OSTalentPoolCreate,
    OSTalentPoolResponse,
    OSTalentPoolUpdate,
)
from app.domains.open_source.services.open_source_service import OpenSourceService
from app.domains.shared.schemas.common import PaginatedResponse, SuccessResponse

router = APIRouter(prefix="/open-source", tags=["Open Source Talent"])


# ============= Favorites =============


@router.post("/favourites", response_model=OSFavoriteResponse)
async def add_favorite(
    data: OSFavoriteCreate,
    session: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    user_id = int(user.get("sub", 0))
    service = OpenSourceService(session)
    favorite = await service.add_favourite(user_id, data.developer_id, notes=data.notes)
    dev = await service.get_developer(data.developer_id)
    resp = OSFavoriteResponse.model_validate(favorite)
    resp.developer = OSDeveloperSummary.model_validate(dev) if dev else None
    return resp


@router.get("/favourites", response_model=PaginatedResponse[OSFavoriteResponse])
async def list_favorites(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = Query(None),
    session: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    user_id = int(user.get("sub", 0))
    service = OpenSourceService(session)
    favourites, total = await service.list_favourites(
        user_id=user_id, page=page, page_size=page_size, keyword=keyword
    )
    # Load developer details for each favourite
    dev_ids = [f.developer_id for f in favourites]
    developers = {d.developer_id: d for d in await service.get_developers_by_ids(dev_ids)}
    items = []
    for fav in favourites:
        resp = OSFavoriteResponse.model_validate(fav)
        dev = developers.get(fav.developer_id)
        resp.developer = OSDeveloperSummary.model_validate(dev) if dev else None
        items.append(resp)

    return PaginatedResponse.create(items=items, total=total, page=page, page_size=page_size)


@router.get("/favourites/ids", response_model=OSFavoriteIdsResponse)
async def get_favorite_ids(
    session: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    user_id = int(user.get("sub", 0))
    service = OpenSourceService(session)
    ids = await service.get_favourite_ids(user_id)
    return OSFavoriteIdsResponse(developer_ids=ids)


@router.put("/favourites/{developer_id}", response_model=OSFavoriteResponse)
async def update_favorite(
    developer_id: int,
    data: OSFavoriteUpdate,
    session: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    user_id = int(user.get("sub", 0))
    service = OpenSourceService(session)
    favourite = await service.update_favourite(
        user_id=user_id,
        developer_id=developer_id,
        notes=data.notes,
        followup_status=data.followup_status,
    )
    if not favourite:
        raise HTTPException(status_code=404, detail="Favorite not found")
    dev = await service.get_developer(developer_id)
    resp = OSFavoriteResponse.model_validate(favourite)
    resp.developer = OSDeveloperSummary.model_validate(dev) if dev else None
    return resp


@router.delete("/favourites/{developer_id}")
async def remove_favorite(
    developer_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    user_id = int(user.get("sub", 0))
    service = OpenSourceService(session)
    success = await service.remove_favourite(user_id, developer_id)
    if not success:
        raise HTTPException(status_code=404, detail="Favorite not found")
    return SuccessResponse(message="Removed from favorites")


# ============= Talent Pools =============


@router.get("/talent-pools", response_model=list[OSTalentPoolResponse])
async def list_talent_pools(
    session: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    user_id = int(user.get("sub", 0))
    service = OpenSourceService(session)
    pools = await service.list_talent_pools(user_id)
    return [OSTalentPoolResponse.model_validate(i) for i in pools]


@router.post("/talent-pools", response_model=OSTalentPoolResponse, status_code=201)
async def create_talent_pool(
    data: OSTalentPoolCreate,
    session: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    user_id = int(user.get("sub", 0))
    service = OpenSourceService(session)
    pool = await service.create_talent_pool(
        user_id=user_id,
        pool_name=data.pool_name,
        pool_type=data.pool_type,
        scope_desc=data.scope_desc,
    )
    return OSTalentPoolResponse.model_validate(pool)


@router.put("/talent-pools/{pool_id}", response_model=OSTalentPoolResponse)
async def update_talent_pool(
    pool_id: int,
    data: OSTalentPoolUpdate,
    session: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    user_id = int(user.get("sub", 0))
    service = OpenSourceService(session)
    # Verify ownership
    pool = await service.get_talent_pool(pool_id)
    if not pool or pool.owner_user_id != user_id:
        raise HTTPException(status_code=404, detail="Pool not found")

    updated = await service.update_talent_pool(pool_id, data.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Pool not found")
    return OSTalentPoolResponse.model_validate(updated)


@router.delete("/talent-pools/{pool_id}")
async def delete_talent_pool(
    pool_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    user_id = int(user.get("sub", 0))
    service = OpenSourceService(session)
    pool = await service.get_talent_pool(pool_id)
    if not pool or pool.owner_user_id != user_id:
        raise HTTPException(status_code=404, detail="Pool not found")
    success = await service.delete_talent_pool(pool_id)
    if not success:
        raise HTTPException(status_code=404, detail="Pool not found")
    return SuccessResponse(message="Deleted")


@router.post("/talent-pools/{pool_id}/members/{developer_id}")
async def add_pool_member(
    pool_id: int,
    developer_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    user_id = int(user.get("sub", 0))
    service = OpenSourceService(session)
    pool = await service.get_talent_pool(pool_id)
    if not pool or pool.owner_user_id != user_id:
        raise HTTPException(status_code=404, detail="Pool not found")

    await service.add_pool_member(pool_id, developer_id)
    return SuccessResponse(message="Added to pool")


@router.delete("/talent-pools/{pool_id}/members/{developer_id}")
async def remove_pool_member(
    pool_id: int,
    developer_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    user_id = int(user.get("sub", 0))
    service = OpenSourceService(session)
    pool = await service.get_talent_pool(pool_id)
    if not pool or pool.owner_user_id != user_id:
        raise HTTPException(status_code=404, detail="Pool not found")

    success = await service.remove_pool_member(pool_id, developer_id)
    if not success:
        raise HTTPException(status_code=404, detail="Member not found")
    return SuccessResponse(message="Removed from pool")


@router.get(
    "/talent-pools/{pool_id}/members", response_model=PaginatedResponse[OSPoolMemberResponse]
)
async def list_pool_members(
    pool_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    user_id = int(user.get("sub", 0))
    service = OpenSourceService(session)
    pool = await service.get_talent_pool(pool_id)
    if not pool or pool.owner_user_id != user_id:
        raise HTTPException(status_code=404, detail="Pool not found")

    members, total = await service.list_pool_members(pool_id, page=page, page_size=page_size)
    dev_ids = [m.developer_id for m in members]
    developers = {d.developer_id: d for d in await service.get_developers_by_ids(dev_ids)}
    items = []
    for member in members:
        resp = OSPoolMemberResponse.model_validate(member)
        dev = developers.get(member.developer_id)
        resp.developer = OSDeveloperSummary.model_validate(dev) if dev else None
        items.append(resp)

    return PaginatedResponse.create(items=items, total=total, page=page, page_size=page_size)
