"""Industry position endpoints — CRUD (no DELETE, archive via status)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.industry.schemas.industry import (
    IndustryPositionCreate,
    IndustryPositionResponse,
    IndustryPositionUpdate,
)
from app.domains.industry.services.industry_position_service import IndustryPositionService
from app.domains.industry.services.industry_talent_service import IndustryTalentService
from app.domains.shared.api.auth import get_current_user, require_super_admin
from app.domains.shared.services.audit_service import AuditService

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


@router.get(
    "/positions/{position_id}/export",
    response_model=None,
    summary="Export position talents as JSONL (super_admin)",
)
async def export_position_talents(
    position_id: int,
    batch: str | None = Query(
        None, description="Filter by import batch; omit to export all talents of the position"
    ),
    session: AsyncSession = Depends(get_async_session),
    admin: dict = Depends(require_super_admin),
    request: Request = None,  # type: ignore[assignment]
) -> StreamingResponse:
    """Export a position's candidates as JSONL for cross-server migration.

    The output format matches the import contract exactly, so the file can be
    uploaded via ``POST /industry/import/upload`` on another server. The
    importer's incremental upsert preserves the target server's operational
    state (touched/status/notes) — those fields are deliberately omitted here.
    """
    import io
    import re

    talent_service = IndustryTalentService(session)
    content, count = await talent_service.export_jsonl(position_id, batch)

    if count == 0:
        await AuditService.log_data_operation(
            user_id=admin.get("user_id"),
            operation="export",
            resource_type="industry_talent",
            resource_id=None,
            status="failure",
            user_ip=request.client.host if request and request.client else None,
            request_id=getattr(request.state, "request_id", None) if request else None,
            detail={"position_id": position_id, "batch": batch, "error": "no candidates to export"},
        )
        raise HTTPException(status_code=404, detail="该岗位下没有可导出的候选人")

    await AuditService.log_data_operation(
        user_id=admin.get("user_id"),
        operation="export",
        resource_type="industry_talent",
        resource_id=None,
        status="success",
        user_ip=request.client.host if request and request.client else None,
        request_id=getattr(request.state, "request_id", None) if request else None,
        detail={"position_id": position_id, "batch": batch, "count": count},
    )

    # Sanitize batch for filename (allow only alnum, dash, underscore, dot)
    safe_batch = re.sub(r"[^A-Za-z0-9._-]", "", batch) if batch else None
    suffix = f"_{safe_batch}" if safe_batch else "_all"
    filename = f"industry_position_{position_id}{suffix}.jsonl"

    buffer = io.BytesIO(content.encode("utf-8"))
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/x-jsonlines",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
