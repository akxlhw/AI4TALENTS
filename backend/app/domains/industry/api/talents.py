"""Industry talent endpoints — list, detail, per-position status management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.industry.schemas.industry import (
    CandidateStatusPatch,
    IndustryPositionMatchDetail,
    IndustryTalentDetail,
    IndustryTalentSummary,
)
from app.domains.industry.services.industry_talent_service import IndustryTalentService
from app.domains.shared.api.auth import get_current_user, require_super_admin, require_user
from app.domains.shared.schemas.common import PaginatedResponse

router = APIRouter(prefix="/industry", tags=["Industry Talent"])


@router.get(
    "/talents",
    response_model=PaginatedResponse[IndustryTalentSummary],
    summary="Search and list industry talents",
)
async def list_industry_talents(
    keyword: str | None = Query(None, description="Keyword (name/org/title fuzzy)"),
    position_id: int | None = Query(None, description="Filter by matched position"),
    min_score: float | None = Query(None, ge=0, le=100, description="Minimum match score"),
    status: str | None = Query(
        None, description="Recruiting status: new/contacted/interviewed/rejected/hired"
    ),
    source_platform: str | None = Query(None, description="Source: maimai/linkedin"),
    tech_direction: str | None = Query(
        None, description="Tech direction code (matched position's directions)"
    ),
    sort_by: str = Query(
        "match_score_desc",
        description="Sort key: match_score_desc | match_score_asc | created_desc | name_asc",
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
    _user: dict | None = Depends(get_current_user),
) -> PaginatedResponse[IndustryTalentSummary]:
    """Global talent pool with multi-dimension filtering.

    Summary rows carry the best match score and matched positions, aggregated
    by a single GROUP BY subquery (no N+1).
    """
    service = IndustryTalentService(session)
    items, total = await service.list_talents(
        keyword=keyword,
        position_id=position_id,
        min_score=min_score,
        status=status,
        source_platform=source_platform,
        tech_direction=tech_direction,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse.create(items=items, total=total, page=page, page_size=page_size)


@router.get(
    "/talents/{talent_id}",
    response_model=IndustryTalentDetail,
    summary="Get industry talent detail",
)
async def get_industry_talent_detail(
    talent_id: int,
    session: AsyncSession = Depends(get_async_session),
    _user: dict | None = Depends(get_current_user),
) -> IndustryTalentDetail:
    """Full profile: experiences + three-dimension scores + per-position comparison."""
    service = IndustryTalentService(session)
    return await service.get_talent_detail(talent_id)


@router.get(
    "/talents/{talent_id}/positions",
    response_model=list[IndustryPositionMatchDetail],
    summary="Get a talent's position matches",
)
async def get_industry_talent_positions(
    talent_id: int,
    session: AsyncSession = Depends(get_async_session),
    _user: dict | None = Depends(get_current_user),
) -> list[IndustryPositionMatchDetail]:
    """Which positions this talent matched, with per-position scores and state."""
    service = IndustryTalentService(session)
    return await service.get_talent_positions(talent_id)


@router.patch(
    "/talents/{talent_id}/positions/{position_id}",
    response_model=IndustryPositionMatchDetail,
    summary="Update recruiting status of a candidate under a position",
)
async def patch_candidate_status(
    talent_id: int,
    position_id: int,
    patch: CandidateStatusPatch,
    session: AsyncSession = Depends(get_async_session),
    _user: dict = Depends(require_user),
) -> IndustryPositionMatchDetail:
    """Update status/touched/notes and/or scores of a talent under one position."""
    service = IndustryTalentService(session)
    return await service.patch_candidate_status(talent_id, position_id, patch)


@router.delete(
    "/talents/{talent_id}/positions/{position_id}",
    summary="Remove a talent from a position (super_admin)",
)
async def remove_talent_from_position(
    talent_id: int,
    position_id: int,
    session: AsyncSession = Depends(get_async_session),
    _admin: dict = Depends(require_super_admin),
) -> dict:
    """Delete the (talent_id, position_id) link.

    If the talent no longer has any position association after this removal,
    the talent record itself is also cleaned up (orphan cleanup, same logic
    as batch deletion).
    """
    service = IndustryTalentService(session)
    link_deleted, orphan_deleted = await service.remove_from_position(talent_id, position_id)
    return {
        "link_deleted": link_deleted,
        "orphan_talent_deleted": orphan_deleted,
    }
