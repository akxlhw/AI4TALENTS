"""Industry position endpoints — CRUD (no DELETE, archive via status)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.industry.schemas.industry import (
    IndustryPositionCreate,
    IndustryPositionResponse,
    IndustryPositionUpdate,
)
from app.domains.industry.services.industry_position_service import IndustryPositionService
from app.domains.shared.api.auth import get_current_user, require_super_admin

router = APIRouter(prefix="/industry", tags=["Industry Talent"])


@router.post(
    "/positions",
    response_model=IndustryPositionResponse,
    summary="Create an industry position (super_admin)",
)
async def create_position(
    data: IndustryPositionCreate,
    session: AsyncSession = Depends(get_async_session),
    admin: dict = Depends(require_super_admin),
) -> IndustryPositionResponse:
    """Create a recruiting position (title/department/tech directions/levels/JD)."""
    service = IndustryPositionService(session)
    return await service.create_position(data, created_by=admin.get("user_id"))


@router.get(
    "/positions",
    response_model=list[IndustryPositionResponse],
    summary="List industry positions with candidate stats",
)
async def list_positions(
    status: str | None = Query(None, description="Filter by status: open/closed/archived"),
    session: AsyncSession = Depends(get_async_session),
    _user: dict | None = Depends(get_current_user),
) -> list[IndustryPositionResponse]:
    """List positions with candidate count and average match score (F-POS-04)."""
    service = IndustryPositionService(session)
    return await service.list_positions(status=status)


@router.get(
    "/positions/{position_id}",
    response_model=IndustryPositionResponse,
    summary="Get an industry position",
)
async def get_position(
    position_id: int,
    session: AsyncSession = Depends(get_async_session),
    _user: dict | None = Depends(get_current_user),
) -> IndustryPositionResponse:
    """Get one position with candidate aggregates."""
    service = IndustryPositionService(session)
    return await service.get_position(position_id)


@router.put(
    "/positions/{position_id}",
    response_model=IndustryPositionResponse,
    summary="Update an industry position (super_admin)",
)
async def update_position(
    position_id: int,
    data: IndustryPositionUpdate,
    session: AsyncSession = Depends(get_async_session),
    _admin: dict = Depends(require_super_admin),
) -> IndustryPositionResponse:
    """Update any position field, including status transitions (open/closed/archived).

    Positions are never physically deleted — archive via status instead.
    """
    service = IndustryPositionService(session)
    return await service.update_position(position_id, data)


@router.get(
    "/positions/{position_id}/batches",
    summary="List import batches for a position",
)
async def list_batches(
    position_id: int,
    session: AsyncSession = Depends(get_async_session),
    _admin: dict = Depends(require_super_admin),
) -> list[dict]:
    """List distinct import batches with candidate counts."""
    service = IndustryPositionService(session)
    return await service.list_batches(position_id)


@router.delete(
    "/positions/{position_id}/batches/{batch}",
    summary="Delete all candidates from a specific import batch",
)
async def delete_batch(
    position_id: int,
    batch: str,
    session: AsyncSession = Depends(get_async_session),
    _admin: dict = Depends(require_super_admin),
) -> dict:
    """Delete all candidate links for a batch. Orphan talents (no remaining
    position association) are also cleaned up."""
    service = IndustryPositionService(session)
    return await service.delete_batch(position_id, batch)
