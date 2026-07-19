"""Competition import endpoint — admin JSONL upload (super_admin)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.competition.schemas.competition import CompImportReport
from app.domains.competition.services.comp_import_service import (
    CompImportError,
    CompImportService,
)
from app.domains.shared.api.auth import require_super_admin

router = APIRouter(prefix="/comp", tags=["Competition Talent"])

# Max JSONL upload size: 20 MB (one contest standings file is typically < 5 MB)
_MAX_UPLOAD_BYTES = 20 * 1024 * 1024


@router.post(
    "/import/upload",
    response_model=CompImportReport,
    summary="Import competition JSONL (admin upload, super_admin)",
)
async def import_competition_upload(
    file: UploadFile = File(..., description="JSONL file from comp-talent-crawler"),
    session: AsyncSession = Depends(get_async_session),
    _admin: dict = Depends(require_super_admin),
) -> CompImportReport:
    """Admin-facing import entry. Authenticates via super_admin JWT."""
    raw = await file.read()
    if len(raw) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413, detail=f"File too large ({len(raw)} bytes, max {_MAX_UPLOAD_BYTES})"
        )
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File is not valid UTF-8") from None

    service = CompImportService(session)
    try:
        return await service.import_jsonl(content)
    except CompImportError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
