"""Lab homepage prefetch endpoints — batch fetch & cache personal homepages."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.lab.services.prefetch_background_service import (
    is_heartbeat_alive,
    load_prefetch_status,
    run_prefetch,
    save_prefetch_status,
    utc_now_iso,
)
from app.domains.shared.api.auth import require_admin
from app.domains.shared.schemas.common import TaskStartResponse
from app.domains.shared.services.config_service import ConfigService

logger = logging.getLogger(__name__)

# Keep references to background tasks to prevent GC (Python docs:
# "Save a reference to the result of this function")
_background_tasks: set[asyncio.Task] = set()

router = APIRouter(prefix="/lab", tags=["AI Lab Talent"])


@router.post(
    "/prefetch-homepages",
    response_model=TaskStartResponse,
    summary="Trigger batch homepage prefetch for a lab (admin)",
)
async def trigger_prefetch(
    parent_lab: str = Query(..., description="Lab to prefetch homepages for"),
    session: AsyncSession = Depends(get_async_session),
    _admin: dict = Depends(require_admin),
) -> TaskStartResponse:
    """Start batch fetching and caching personal homepage HTML."""
    config_service = ConfigService(session)
    status = await load_prefetch_status(config_service, parent_lab)

    if status["status"] == "running" and is_heartbeat_alive(status.get("heartbeat_at")):
        raise HTTPException(status_code=409, detail="Homepage prefetch already in progress")

    if status["status"] == "running":
        logger.warning(
            "[HomepagePrefetch] Found stale running status for %s (heartbeat=%s), resetting",
            parent_lab,
            status.get("heartbeat_at"),
        )

    status.update(
        {
            "status": "pending",
            "processed": 0,
            "total": 0,
            "current": "initializing",
            "errors": 0,
            "heartbeat_at": utc_now_iso(),
        }
    )
    await save_prefetch_status(config_service, parent_lab, status)

    task = asyncio.create_task(run_prefetch(parent_lab), name=f"lab_homepage_prefetch:{parent_lab}")
    _background_tasks.add(task)
    task.add_done_callback(_on_task_done)
    return TaskStartResponse(message=f"Homepage prefetch started for {parent_lab}")


@router.get(
    "/prefetch-homepages/status",
    summary="Get homepage prefetch progress for a lab (admin)",
)
async def get_prefetch_status(
    parent_lab: str = Query(..., description="Lab to get prefetch status for"),
    session: AsyncSession = Depends(get_async_session),
    _admin: dict = Depends(require_admin),
) -> dict:
    """Return current prefetch progress for the given lab."""
    config_service = ConfigService(session)
    status = await load_prefetch_status(config_service, parent_lab)
    if status["status"] == "running" and not is_heartbeat_alive(status.get("heartbeat_at")):
        status["stale"] = True
    return status


def _on_task_done(task: asyncio.Task) -> None:
    _background_tasks.discard(task)
    try:
        task.result()
    except asyncio.CancelledError:
        logger.warning("[HomepagePrefetch] Task cancelled")
    except Exception:
        logger.exception("[HomepagePrefetch] Task failed")
