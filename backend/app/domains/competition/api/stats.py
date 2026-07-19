"""Competition stats endpoints — overview and series list."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.competition.schemas.competition import CompOverviewOut, CompSeriesOut
from app.domains.competition.services.comp_stats_service import CompStatsService
from app.domains.shared.api.auth import get_current_user

router = APIRouter(prefix="/comp", tags=["Competition Talent"])


@router.get(
    "/overview",
    response_model=CompOverviewOut,
    summary="Competition domain overview stats",
)
async def get_comp_overview(
    session: AsyncSession = Depends(get_async_session),
    _user: dict = Depends(get_current_user),
) -> CompOverviewOut:
    """Counts plus top-rated talents and most recent contests."""
    service = CompStatsService(session)
    return await service.get_overview()


@router.get(
    "/series",
    response_model=list[CompSeriesOut],
    summary="List contest series with counts",
)
async def list_comp_series(
    session: AsyncSession = Depends(get_async_session),
    _user: dict = Depends(get_current_user),
) -> list[CompSeriesOut]:
    """All series (enabled or not) with talent/contest counts."""
    service = CompStatsService(session)
    return await service.list_series()
