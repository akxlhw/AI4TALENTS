"""
Talent Pool API endpoints.
人才池相关接口
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import require_user
from app.core.database import get_async_session
from app.repositories.talent_pool_repository import FavoriteRepository, TalentPoolRepository
from app.schemas.common import PaginatedResponse, SuccessResponse
from app.schemas.talent_pool import (
    FOLLOWUP_STATUS_OPTIONS,
    AddMemberRequest,
    CreatePoolRequest,
    PoolListResponse,
    PoolMemberResponse,
    TalentPoolResponse,
    UpdateFollowupRequest,
    UpdatePoolRequest,
)

router = APIRouter(prefix="/talent-pools", tags=["Talent Pools"])


@router.post(
    "",
    response_model=TalentPoolResponse,
    summary="创建人才池",
    description="创建新的人才池"
)
async def create_pool(
    request: CreatePoolRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_user),
):
    """Create a new talent pool."""
    repo = TalentPoolRepository(session)
    pool = await repo.create_pool_and_commit(
        user_id=current_user["user_id"],
        name=request.pool_name,
        pool_type=request.pool_type,
        desc=request.scope_desc,
    )

    return TalentPoolResponse(
        pool_id=pool.pool_id,
        pool_name=pool.pool_name,
        pool_type=pool.pool_type,
        owner_user_id=pool.owner_user_id,
        scope_desc=pool.scope_desc,
        pool_status=pool.pool_status,
        member_count=0,
        created_at=pool.created_at,
    )


@router.get(
    "",
    response_model=PoolListResponse,
    summary="获取人才池列表",
    description="获取当前用户的所有人才池"
)
async def list_pools(
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_user),
):
    """List all talent pools for current user."""
    repo = TalentPoolRepository(session)
    pools = await repo.list_user_pools(current_user["user_id"])

    items = []
    for pool in pools:
        # Get member count
        members, _ = await repo.get_pool_members(pool.pool_id, page=1, page_size=1)
        items.append(TalentPoolResponse(
            pool_id=pool.pool_id,
            pool_name=pool.pool_name,
            pool_type=pool.pool_type,
            owner_user_id=pool.owner_user_id,
            scope_desc=pool.scope_desc,
            pool_status=pool.pool_status,
            member_count=len(members) if members else 0,
            created_at=pool.created_at,
        ))

    return PoolListResponse(items=items, total=len(items))


@router.get(
    "/{pool_id}",
    response_model=TalentPoolResponse,
    summary="获取人才池详情",
    description="获取指定人才池的详细信息"
)
async def get_pool(
    pool_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_user),
):
    """Get talent pool details."""
    repo = TalentPoolRepository(session)
    pool = await repo.get_pool_by_id(pool_id)

    if not pool:
        raise HTTPException(status_code=404, detail="Talent pool not found")

    if pool.owner_user_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    members, total = await repo.get_pool_members(pool_id, page=1, page_size=1)

    return TalentPoolResponse(
        pool_id=pool.pool_id,
        pool_name=pool.pool_name,
        pool_type=pool.pool_type,
        owner_user_id=pool.owner_user_id,
        scope_desc=pool.scope_desc,
        pool_status=pool.pool_status,
        member_count=total,
        created_at=pool.created_at,
    )


@router.put(
    "/{pool_id}",
    response_model=TalentPoolResponse,
    summary="更新人才池",
    description="更新人才池信息"
)
async def update_pool(
    pool_id: int,
    request: UpdatePoolRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_user),
):
    """Update talent pool."""
    repo = TalentPoolRepository(session)
    pool = await repo.get_pool_by_id(pool_id)

    if not pool:
        raise HTTPException(status_code=404, detail="Talent pool not found")

    if pool.owner_user_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    updated_pool = await repo.update_pool_and_commit(
        pool_id,
        name=request.pool_name,
        desc=request.scope_desc,
        status=request.pool_status,
    )

    members, total = await repo.get_pool_members(pool_id, page=1, page_size=1)

    return TalentPoolResponse(
        pool_id=updated_pool.pool_id,
        pool_name=updated_pool.pool_name,
        pool_type=updated_pool.pool_type,
        owner_user_id=updated_pool.owner_user_id,
        scope_desc=updated_pool.scope_desc,
        pool_status=updated_pool.pool_status,
        member_count=total,
        created_at=updated_pool.created_at,
    )


@router.delete(
    "/{pool_id}",
    summary="删除人才池",
    description="删除人才池（归档）"
)
async def delete_pool(
    pool_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_user),
):
    """Delete talent pool (archive)."""
    repo = TalentPoolRepository(session)
    pool = await repo.get_pool_by_id(pool_id)

    if not pool:
        raise HTTPException(status_code=404, detail="Talent pool not found")

    if pool.owner_user_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    await repo.delete_pool_and_commit(pool_id)

    return SuccessResponse(message="Talent pool archived")


@router.post(
    "/{pool_id}/members",
    summary="添加成员",
    description="将人才添加到人才池"
)
async def add_member(
    pool_id: int,
    request: AddMemberRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_user),
):
    """Add talent to pool."""
    repo = TalentPoolRepository(session)
    pool = await repo.get_pool_by_id(pool_id)

    if not pool:
        raise HTTPException(status_code=404, detail="Talent pool not found")

    if pool.owner_user_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    # Check if already a member
    if await repo.is_member(pool_id, request.talent_id):
        raise HTTPException(status_code=400, detail="Talent already in pool")

    await repo.add_member_and_commit(
        pool_id=pool_id,
        talent_id=request.talent_id,
        added_by=current_user["user_id"],
        notes=request.notes,
    )

    return SuccessResponse(message="Talent added to pool")


@router.delete(
    "/{pool_id}/members/{talent_id}",
    summary="移除成员",
    description="从人才池中移除人才"
)
async def remove_member(
    pool_id: int,
    talent_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_user),
):
    """Remove talent from pool."""
    repo = TalentPoolRepository(session)
    pool = await repo.get_pool_by_id(pool_id)

    if not pool:
        raise HTTPException(status_code=404, detail="Talent pool not found")

    if pool.owner_user_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    removed = await repo.remove_member_and_commit(pool_id, talent_id)

    if not removed:
        raise HTTPException(status_code=404, detail="Talent not in pool")

    return SuccessResponse(message="Talent removed from pool")


@router.get(
    "/{pool_id}/members",
    response_model=PaginatedResponse[PoolMemberResponse],
    summary="获取成员列表",
    description="获取人才池成员列表"
)
async def list_members(
    pool_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_user),
):
    """List members of a talent pool."""
    repo = TalentPoolRepository(session)
    pool = await repo.get_pool_by_id(pool_id)

    if not pool:
        raise HTTPException(status_code=404, detail="Talent pool not found")

    if pool.owner_user_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    items, total = await repo.get_pool_members(pool_id, page, page_size)

    return PaginatedResponse.create(
        items=[PoolMemberResponse(**item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.put(
    "/favorites/{talent_id}/followup",
    summary="更新跟进状态",
    description="更新收藏人才的跟进状态"
)
async def update_followup_status(
    talent_id: int,
    request: UpdateFollowupRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_user),
):
    """Update followup status for a favorite talent."""
    # Validate status
    valid_statuses = [opt["value"] for opt in FOLLOWUP_STATUS_OPTIONS]
    if request.followup_status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Valid options: {valid_statuses}")

    repo = FavoriteRepository(session)
    favorite = await repo.update_followup_status_and_commit(
        user_id=current_user["user_id"],
        talent_id=talent_id,
        status=request.followup_status,
    )

    if not favorite:
        raise HTTPException(status_code=404, detail="Favorite not found")

    return SuccessResponse(message="Followup status updated")


@router.get(
    "/followup-statuses",
    summary="获取跟进状态选项",
    description="获取所有可用的跟进状态选项"
)
async def get_followup_statuses():
    """Get all followup status options."""
    return FOLLOWUP_STATUS_OPTIONS
