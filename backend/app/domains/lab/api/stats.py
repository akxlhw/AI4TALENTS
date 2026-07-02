"""Lab stats endpoint — overview statistics."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.lab.schemas.lab_talent import LabStatsResponse
from app.domains.lab.services.lab_stats_service import LabStatsService
from app.domains.shared.api.auth import get_current_user

router = APIRouter(prefix="/lab", tags=["AI Lab Talent"])


@router.get(
    "/stats",
    response_model=LabStatsResponse,
    summary="Lab talent library overview statistics",
)
async def get_lab_stats(
    session: AsyncSession = Depends(get_async_session),
    _user: dict = Depends(get_current_user),
) -> LabStatsResponse:
    """Return overview statistics (totals, distributions, top labs)."""
    service = LabStatsService(session)
    return await service.get_stats()
