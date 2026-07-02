"""Lab import endpoints — hermes push (API Key) + admin upload (super_admin)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.lab.schemas.lab_talent import LabImportReport
from app.domains.lab.services.lab_import_service import LabImportService
from app.domains.shared.api.auth import require_super_admin
from app.domains.shared.services.config_service import ConfigService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/lab", tags=["AI Lab Talent"])

# Max JSONL upload size: 20 MB (crawler output for one lab is typically < 2 MB)
_MAX_UPLOAD_BYTES = 20 * 1024 * 1024


async def require_lab_import_api_key(
    authorization: str | None = Depends(lambda: None),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    """Dependency: validate hermes static import API key.

    The key is stored in sys_config under LAB_IMPORT_API_KEY. If the key is
    unset (empty), all imports via this entry are rejected with 503.
    """
    config_service = ConfigService(session)
    expected_key = await config_service.get_value("LAB_IMPORT_API_KEY", default="")

    if not expected_key:
        raise HTTPException(
            status_code=503,
            detail="Lab import API key not configured. Set LAB_IMPORT_API_KEY in system config.",
        )

    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    token = authorization
    if token.startswith("Bearer "):
        token = token[7:]

    if token != expected_key:
        raise HTTPException(status_code=401, detail="Invalid lab import API key")

    return {"role": "lab_importer", "source": "hermes"}


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
    "/import",
    response_model=LabImportReport,
    summary="Import lab talent JSONL (hermes push, API Key auth)",
)
async def import_lab_talents_push(
    parent_lab: str = Form(..., description="Top-level lab name being replaced"),
    file: UploadFile = File(..., description="JSONL file from ai-lab-talent-crawler"),
    session: AsyncSession = Depends(get_async_session),
    _caller: dict = Depends(require_lab_import_api_key),
) -> LabImportReport:
    """Hermes-facing import entry. Authenticates via static API key."""
    content, err = await _read_upload(file)
    if err:
        raise HTTPException(status_code=400, detail=err)

    service = LabImportService(session)
    return await service.import_jsonl(content, parent_lab)


@router.post(
    "/import/upload",
    response_model=LabImportReport,
    summary="Import lab talent JSONL (admin upload, super_admin)",
)
async def import_lab_talents_upload(
    parent_lab: str = Form(..., description="Top-level lab name being replaced"),
    file: UploadFile = File(..., description="JSONL file from ai-lab-talent-crawler"),
    session: AsyncSession = Depends(get_async_session),
    _admin: dict = Depends(require_super_admin),
) -> LabImportReport:
    """Admin-facing import entry. Authenticates via super_admin JWT."""
    content, err = await _read_upload(file)
    if err:
        raise HTTPException(status_code=400, detail=err)

    service = LabImportService(session)
    return await service.import_jsonl(content, parent_lab)
