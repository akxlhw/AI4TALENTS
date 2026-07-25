"""Competition contest endpoints — list and detail (leaderboard)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.competition.schemas.competition import CompContestDetail, CompContestSummary
from app.domains.competition.services.comp_contest_service import CompContestService
from app.domains.shared.api.auth import get_current_user
from app.domains.shared.schemas.common import PaginatedResponse

router = APIRouter(prefix="/comp", tags=["Competition Talent"])


@router.get(
    "/contests",
    response_model=PaginatedResponse[CompContestSummary],
    summary="List contests",
)
async def list_comp_contests(
    series_code: str | None = Query(None, description="Series code filter (e.g. icpc, ioi)"),
    season: str | None = Query(None, description="Season filter (e.g. 2024)"),
    keyword: str | None = Query(None, description="Contest name keyword (fuzzy)"),
    year_gte: int | None = Query(None, ge=1990, le=2100, description="Start-year lower bound"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
    _user: dict = Depends(get_current_user),
) -> PaginatedResponse[CompContestSummary]:
    """List contests, most recent first."""
    service = CompContestService(session)
    items, total = await service.list_contests(
        series_code=series_code,
        season=season,
        keyword=keyword,
        year_gte=year_gte,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse.create(items=items, total=total, page=page, page_size=page_size)


@router.get(
    "/contests/{contest_id}",
    response_model=CompContestDetail,
    summary="Get contest detail with leaderboards",
)
async def get_comp_contest(
    contest_id: int,
    session: AsyncSession = Depends(get_async_session),
    _user: dict = Depends(get_current_user),
) -> CompContestDetail:
    """Return contest info plus personal and team leaderboards."""
    service = CompContestService(session)
    detail = await service.get_detail(contest_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Contest not found")
    return detail
