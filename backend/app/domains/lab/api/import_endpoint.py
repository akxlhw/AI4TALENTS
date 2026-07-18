"""Lab import endpoints — admin JSONL upload (super_admin)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.lab.schemas.lab_talent import LabImportReport
from app.domains.lab.services.lab_import_service import LabImportService
from app.domains.shared.api.auth import require_super_admin

router = APIRouter(prefix="/lab", tags=["AI Lab Talent"])

# Max JSONL upload size: 20 MB (crawler output for one lab is typically < 2 MB)
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
    response_model=LabImportReport,
    summary="Import lab talent JSONL (admin upload, super_admin)",
)
async def import_lab_talents_upload(
    parent_lab: str | None = Form(
        None,
        description="Top-level lab name being replaced (optional when JSONL contains a lab metadata header)",
    ),
    file: UploadFile = File(..., description="JSONL file from ai-lab-talent-crawler"),
    session: AsyncSession = Depends(get_async_session),
    _admin: dict = Depends(require_super_admin),
) -> LabImportReport:
    """Admin-facing import entry. Authenticates via super_admin JWT."""
    content, err = await _read_upload(file)
    if err:
        raise HTTPException(status_code=400, detail=err)

    service = LabImportService(session)
    return await service.import_jsonl(content, parent_lab or "")
