"""Competition talent browse endpoints — list/search and detail."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.competition.schemas.competition import CompTalentDetail, CompTalentSummary
from app.domains.competition.services.comp_talent_service import CompTalentService
from app.domains.shared.api.auth import get_current_user
from app.domains.shared.schemas.common import PaginatedResponse

router = APIRouter(prefix="/comp", tags=["Competition Talent"])


@router.get(
    "/talents",
    response_model=PaginatedResponse[CompTalentSummary],
    summary="Search and list competition talents",
)
async def list_comp_talents(
    keyword: str | None = Query(None, description="Handle or real-name keyword (fuzzy)"),
    country_code: str | None = Query(None, description="Country code filter (ISO two-letter)"),
    school: str | None = Query(None, description="School filter (fuzzy)"),
    min_rating: int | None = Query(None, description="Minimum current rating"),
    rank_title: str | None = Query(None, description="Rank title filter (e.g. grandmaster)"),
    sort_by: str = Query(
        "rating_desc",
        description="Sort key: rating_desc | rating_asc | contests_desc | medals_desc | recent_desc",
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
    _user: dict = Depends(get_current_user),
) -> PaginatedResponse[CompTalentSummary]:
    """List competition talents with filtering, sorting, and pagination."""
    service = CompTalentService(session)
    items, total = await service.list_talents(
        keyword=keyword,
        country_code=country_code,
        school=school,
        min_rating=min_rating,
        rank_title=rank_title,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse.create(items=items, total=total, page=page, page_size=page_size)


@router.get(
    "/talents/{talent_id}",
    response_model=CompTalentDetail,
    summary="Get competition talent detail with contest history",
)
async def get_comp_talent(
    talent_id: int,
    session: AsyncSession = Depends(get_async_session),
    _user: dict = Depends(get_current_user),
) -> CompTalentDetail:
    """Return talent profile, aggregates, and per-contest history."""
    service = CompTalentService(session)
    detail = await service.get_detail(talent_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Talent not found")
    return detail
