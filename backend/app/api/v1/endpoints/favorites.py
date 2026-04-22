"""
Favorites API endpoints.
Provides favorite talent management.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import require_user
from app.core.database import get_async_session
from app.repositories.favorite_repository import FavoriteRepository
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/favorites", tags=["Favorites"])


# Request/Response schemas
class AddFavoriteRequest(BaseModel):
    """Request to add a talent to favorites."""
    talent_id: int = Field(..., description="Talent ID to favorite")
    notes: str | None = Field(None, description="Optional notes about the talent")


class UpdateFavoriteRequest(BaseModel):
    """Request to update favorite notes."""
    notes: str | None = Field(None, description="Updated notes")


class FavoriteTalentResponse(BaseModel):
    """Response for a favorite talent."""
    favorite_id: int
    talent_id: int
    name: str
    name_en: str | None = None
    role_type: str
    school_id: int | None = None
    school_name: str | None = None
    current_title: str | None = None
    works_count: int
    cited_by_count: int
    h_index: int
    notes: str | None = None
    created_at: str

    class Config:
        from_attributes = True


class CheckFavoriteResponse(BaseModel):
    """Response for checking if a talent is favorited."""
    is_favorited: bool
    favorite_id: int | None = None
    notes: str | None = None


@router.post(
    "",
    response_model=FavoriteTalentResponse,
    summary="添加收藏",
    description="将一个人才添加到用户的收藏列表",
)
async def add_favorite(
    request: AddFavoriteRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_user),
):
    """
    Add a talent to user's favorites.

    Requires authentication.
    """
    user_id = current_user["user_id"]
    repo = FavoriteRepository(session)

    # Check if already favorited
    existing = await repo.get_by_user_and_talent(user_id, request.talent_id)
    if existing:
        raise HTTPException(status_code=400, detail="该人才已在收藏列表中")

    # Add favorite
    favorite = await repo.add_favorite(
        user_id=user_id,
        talent_id=request.talent_id,
        notes=request.notes,
    )

    # Load talent relationship
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.models.iam import FavoriteTalent
    from app.models.talent import Talent

    result = await session.execute(
        select(FavoriteTalent)
        .options(
            selectinload(FavoriteTalent.talent),
            selectinload(FavoriteTalent.talent).selectinload(Talent.education_school),
            selectinload(FavoriteTalent.talent).selectinload(Talent.company_school),
            selectinload(FavoriteTalent.talent).selectinload(Talent.school),
        )
        .where(FavoriteTalent.favorite_id == favorite.favorite_id)
    )
    favorite = result.scalar_one()

    await session.commit()
    return _build_favorite_response(favorite)


@router.get(
    "",
    response_model=PaginatedResponse[FavoriteTalentResponse],
    summary="获取收藏列表",
    description="分页获取用户收藏的人才列表",
)
async def list_favorites(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    role_type: str | None = Query(None, description="按角色类型筛选"),
    keyword: str | None = Query(None, description="搜索关键词"),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_user),
):
    """
    Get paginated list of user's favorite talents.

    Supports filtering by role type and keyword search.
    """
    user_id = current_user["user_id"]
    repo = FavoriteRepository(session)
    favorites, total = await repo.list_user_favorites(
        user_id=user_id,
        page=page,
        page_size=page_size,
        role_type=role_type,
        keyword=keyword,
    )

    items = [_build_favorite_response(fav) for fav in favorites]

    return PaginatedResponse.create(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/ids",
    response_model=list[int],
    summary="获取已收藏的人才ID列表",
    description="获取用户已收藏的所有人才ID，用于前端标记收藏状态",
)
async def get_favorite_ids(
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_user),
):
    """
    Get all favorited talent IDs for the current user.

    Useful for front-end to mark favorite status in lists.
    """
    user_id = current_user["user_id"]
    repo = FavoriteRepository(session)
    return await repo.get_user_favorite_ids(user_id)


@router.get(
    "/{talent_id}/check",
    response_model=CheckFavoriteResponse,
    summary="检查是否已收藏",
    description="检查指定人才是否已被当前用户收藏",
)
async def check_favorite(
    talent_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_user),
):
    """
    Check if a specific talent is favorited by the current user.
    """
    user_id = current_user["user_id"]
    repo = FavoriteRepository(session)
    favorite = await repo.get_by_user_and_talent(user_id, talent_id)

    if favorite:
        return CheckFavoriteResponse(
            is_favorited=True,
            favorite_id=favorite.favorite_id,
            notes=favorite.notes,
        )
    return CheckFavoriteResponse(is_favorited=False)


@router.put(
    "/{talent_id}",
    response_model=FavoriteTalentResponse,
    summary="更新收藏备注",
    description="更新对指定人才的收藏备注",
)
async def update_favorite(
    talent_id: int,
    request: UpdateFavoriteRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_user),
):
    """
    Update notes for a favorited talent.
    """
    user_id = current_user["user_id"]
    repo = FavoriteRepository(session)
    favorite = await repo.get_by_user_and_talent(user_id, talent_id)

    if not favorite:
        raise HTTPException(status_code=404, detail="未找到该收藏记录")

    updated = await repo.update_favorite(favorite.favorite_id, request.notes)

    # Reload with relationships
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.models.iam import FavoriteTalent
    from app.models.talent import Talent

    result = await session.execute(
        select(FavoriteTalent)
        .options(
            selectinload(FavoriteTalent.talent),
            selectinload(FavoriteTalent.talent).selectinload(Talent.school),
        )
        .where(FavoriteTalent.favorite_id == updated.favorite_id)
    )
    updated = result.scalar_one()

    await session.commit()
    return _build_favorite_response(updated)


@router.delete(
    "/{talent_id}",
    summary="取消收藏",
    description="将指定人才从用户的收藏列表中移除",
)
async def remove_favorite(
    talent_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_user),
):
    """
    Remove a talent from user's favorites.
    """
    user_id = current_user["user_id"]
    repo = FavoriteRepository(session)
    removed = await repo.remove_favorite(user_id, talent_id)

    if not removed:
        raise HTTPException(status_code=404, detail="未找到该收藏记录")

    await session.commit()
    return {"success": True, "message": "已取消收藏"}


def _build_favorite_response(favorite) -> FavoriteTalentResponse:
    """Build response object from FavoriteTalent."""
    talent = favorite.talent
    return FavoriteTalentResponse(
        favorite_id=favorite.favorite_id,
        talent_id=talent.talent_id,
        name=talent.name,
        name_en=talent.name_en,
        role_type=talent.role_type,
        school_id=talent.education_school_id or talent.company_school_id or talent.school_id,
        # 优先显示教育机构，其次公司机构，最后 legacy school
        school_name=(
            talent.education_school.school_name if talent.education_school else
            talent.company_school.school_name if talent.company_school else
            talent.school.school_name if talent.school else None
        ),
        current_title=talent.current_title,
        works_count=talent.works_count,
        cited_by_count=talent.cited_by_count,
        h_index=talent.h_index,
        notes=favorite.notes,
        created_at=favorite.created_at.isoformat() if favorite.created_at else None,
    )
