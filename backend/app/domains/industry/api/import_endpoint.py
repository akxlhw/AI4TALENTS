"""Industry import endpoints.

Two channels:
- POST /industry/import/upload — admin JSONL upload (super_admin, multipart Form+File)
- POST /industry/import       — API Key push channel for Agent/skill (X-API-Key header)

The push channel lets the ``smart-talent-sourcing`` skill push scored JSONL
programmatically after collection, without admin manual upload. It is guarded
by a static API Key stored in ``sys_config`` (key ``INDUSTRY_IMPORT_API_KEY``),
configurable via the system-config admin UI with hot reload (5 min TTL cache).
"""

from __future__ import annotations

import logging
import secrets

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.industry.schemas.industry import IndustryImportReport
from app.domains.industry.services.industry_import_service import IndustryImportService
from app.domains.industry.services.industry_position_service import IndustryPositionService
from app.domains.shared.api.auth import require_super_admin
from app.domains.shared.services.audit_service import AuditService
from app.domains.shared.services.config_service import ConfigService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/industry", tags=["Industry Talent"])

# Max JSONL upload size: 20 MB (applies to both upload and push channels)
_MAX_UPLOAD_BYTES = 20 * 1024 * 1024

# sys_config key for the push-channel API Key
_API_KEY_CONFIG = "INDUSTRY_IMPORT_API_KEY"


async def _read_upload(file: UploadFile) -> tuple[str, str]:
    """Read an uploaded JSONL file. Returns (content, error_msg)."""
    raw = await file.read()
    if len(raw) > _MAX_UPLOAD_BYTES:
        return "", f"File too large ({len(raw)} bytes, max {_MAX_UPLOAD_BYTES})"
    try:
        return raw.decode("utf-8"), ""
    except UnicodeDecodeError:
        return "", "File is not valid UTF-8"


async def verify_industry_api_key(
    api_key: str | None = Header(None, alias="X-API-Key"),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    """Verify the X-API-Key header against the configured INDUSTRY_IMPORT_API_KEY.

    Returns a synthetic principal dict ``{"role": "import_agent", "source": "api_key"}``
    on success. Raises:
    - 503 if the API Key is not configured in sys_config (admin must set it first)
    - 401 if the header is missing or does not match
    """
    configured = await ConfigService(session).get_value(_API_KEY_CONFIG, "")
    if not configured:
        raise HTTPException(
            status_code=503,
            detail="Import API Key not configured; an admin must set INDUSTRY_IMPORT_API_KEY in system config first.",
        )
    if not api_key or not secrets.compare_digest(api_key, configured):
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")
    return {"role": "import_agent", "source": "api_key"}


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
    summary="Import industry talent JSONL (API Key push channel for Agent/skill)",
)
async def import_industry_talents_push(
    request: Request,
    position_id: int = Query(..., description="Target position for all rows"),
    batch: str | None = Query(None, description="Import batch identifier"),
    session: AsyncSession = Depends(get_async_session),
    _agent: dict = Depends(verify_industry_api_key),
) -> IndustryImportReport:
    """Machine-to-machine import entry for the sourcing skill.

    The request body is the raw JSONL text (Content-Type: application/x-jsonlines);
    ``position_id`` and ``batch`` travel as query parameters. Guarded by a static
    API Key (X-API-Key header) configured via system config. Operational state
    (touched/status/notes) is preserved by the same upsert logic as the upload channel.
    """
    # Fail fast when the target position does not exist (404, not 422)
    await IndustryPositionService(session).get_position(position_id)

    raw = await request.body()
    if len(raw) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"Body too large ({len(raw)} bytes, max {_MAX_UPLOAD_BYTES})",
        )
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError as e:
        raise HTTPException(status_code=400, detail="Body is not valid UTF-8") from e

    user_ip = request.client.host if request.client else None
    request_id = getattr(request.state, "request_id", None)
    audit_detail = {
        "source": "api_key",
        "position_id": position_id,
        "batch": batch,
    }

    try:
        service = IndustryImportService(session)
        report = await service.import_jsonl(content, position_id=position_id, batch=batch)
        audit_detail["rows"] = report.total_parsed
        await AuditService.log_data_operation(
            user_id=None,
            operation="import",
            resource_type="industry_talent",
            resource_id=None,
            status="success",
            user_ip=user_ip,
            request_id=request_id,
            detail=audit_detail,
            event_subtype="import",
        )
        return report
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Industry push import failed (position_id=%s, batch=%s): %s",
            position_id,
            batch,
            e,
            exc_info=True,
        )
        await AuditService.log_data_operation(
            user_id=None,
            operation="import",
            resource_type="industry_talent",
            resource_id=None,
            status="failure",
            user_ip=user_ip,
            request_id=request_id,
            detail=audit_detail,
            error_message=str(e),
            event_subtype="import",
        )
        raise HTTPException(status_code=500, detail=f"Import failed: {e}") from e
