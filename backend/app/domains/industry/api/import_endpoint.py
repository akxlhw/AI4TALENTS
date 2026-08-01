"""Industry import endpoints — admin JSONL upload (super_admin).

The static API Key push channel (POST /industry/import) is reserved but NOT
enabled in v1: enabling it requires an API Key config + verification
dependency, an import-only permission boundary, call auditing and failure
alerting (docs/v5.0.0/02-技术设计.md §5).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.industry.schemas.industry import IndustryImportReport
from app.domains.industry.services.industry_import_service import IndustryImportService
from app.domains.industry.services.industry_position_service import IndustryPositionService
from app.domains.shared.api.auth import require_super_admin

router = APIRouter(prefix="/industry", tags=["Industry Talent"])

# Max JSONL upload size: 20 MB (NF-05)
_MAX_UPLOAD_BYTES = 20 * 1024 * 1024


async def _read_upload(file: UploadFile) -> tuple[str, str]:
    """Read an uploaded JSONL file. Returns (content, error_msg)."""
    raw = await file.read()
    if len(raw) > _MAX_UPLOAD_BYTES:
        return "", f"File too large ({len(raw)} bytes, max {_MAX_UPLOAD_BYTES})"
    try:
        return raw.decode("utf-8"), ""
    except UnicodeDecodeError:
        return "", "File is not valid UTF-8"


@router.post(
    "/import/upload",
    response_model=IndustryImportReport,
    summary="Import industry talent JSONL (admin upload, super_admin)",
)
async def import_industry_talents_upload(
    position_id: int = Form(..., description="Target position for all rows (rows may override)"),
    batch: str | None = Form(None, description="Import batch identifier"),
    file: UploadFile = File(..., description="JSONL file from smart-talent-sourcing skill"),
    session: AsyncSession = Depends(get_async_session),
    _admin: dict = Depends(require_super_admin),
) -> IndustryImportReport:
    """Admin-facing import entry. Incremental upsert (empty fields never
    overwrite, absent rows untouched, link recruiting state preserved)."""
    # Fail fast when the target position does not exist
    await IndustryPositionService(session).get_position(position_id)

    content, err = await _read_upload(file)
    if err:
        raise HTTPException(status_code=400, detail=err)

    service = IndustryImportService(session)
    return await service.import_jsonl(content, position_id=position_id, batch=batch)


@router.post(
    "/import",
    response_model=IndustryImportReport,
    summary="Import industry talent JSONL (API Key push channel, reserved)",
)
async def import_industry_talents_push() -> IndustryImportReport:
    """Reserved push channel for the sourcing skill — not enabled in v1.

    Enablement requires: API Key config + verification dependency, an
    import-only permission boundary, call auditing (source/batch/row counts)
    and failure alerting. Until then the admin upload endpoint is the only
    import entry.
    """
    raise HTTPException(
        status_code=501,
        detail="API Key push channel is not enabled in v1; use /industry/import/upload",
    )
