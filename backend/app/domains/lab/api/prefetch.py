"""Lab homepage prefetch endpoints — batch fetch & cache personal homepages."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.shared.api.auth import require_admin
from app.domains.shared.schemas.common import TaskStartResponse
from app.domains.shared.services.config_service import ConfigService

logger = logging.getLogger(__name__)

# Keep references to background tasks to prevent GC (Python docs:
# "Save a reference to the result of this function")
_background_tasks: set[asyncio.Task] = set()

router = APIRouter(prefix="/lab", tags=["AI Lab Talent"])

PREFETCH_STATUS_KEY = "lab_homepage_prefetch_status"

# If a running task has not updated its heartbeat for this long, it is
# considered dead (e.g. after a service restart) and a new prefetch may start.
HEARTBEAT_TIMEOUT_SECONDS = 300

DEFAULT_STATUS = {
    "status": "idle",
    "processed": 0,
    "total": 0,
    "current": "",
    "errors": 0,
    "heartbeat_at": "",
}


def _status_key(parent_lab: str) -> str:
    """Build the per-lab status config key."""
    return f"{PREFETCH_STATUS_KEY}:{parent_lab}"


def _utc_now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _is_heartbeat_alive(heartbeat_at: str | None) -> bool:
    """Return True if the heartbeat timestamp is recent enough."""
    if not heartbeat_at:
        return False
    try:
        heartbeat = datetime.fromisoformat(heartbeat_at)
    except (ValueError, TypeError):
        return False
    if heartbeat.tzinfo is None:
        heartbeat = heartbeat.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - heartbeat < timedelta(seconds=HEARTBEAT_TIMEOUT_SECONDS)


async def _load_status(config_service: ConfigService, parent_lab: str) -> dict:
    status = await config_service.get_value(_status_key(parent_lab), default=None, use_cache=False)
    if status is None:
        return DEFAULT_STATUS.copy()
    return {**DEFAULT_STATUS, **status}


async def _save_status(config_service: ConfigService, parent_lab: str, status: dict) -> None:
    await config_service.set_value(_status_key(parent_lab), status, config_type="json")
    await config_service.session.commit()


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
    status = await _load_status(config_service, parent_lab)

    if status["status"] == "running" and _is_heartbeat_alive(status.get("heartbeat_at")):
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
            "heartbeat_at": _utc_now_iso(),
        }
    )
    await _save_status(config_service, parent_lab, status)

    task = asyncio.create_task(
        _run_prefetch(parent_lab), name=f"lab_homepage_prefetch:{parent_lab}"
    )
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
    status = await _load_status(config_service, parent_lab)
    if status["status"] == "running" and not _is_heartbeat_alive(status.get("heartbeat_at")):
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


async def _run_prefetch(parent_lab: str) -> None:
    """Background coroutine: batch fetch + cache homepages."""
    from app.core.database import AsyncSessionLocal
    from app.domains.lab.services.homepage_preview_service import HomepagePreviewService

    async with AsyncSessionLocal() as session:
        config_service = ConfigService(session)
        status = await _load_status(config_service, parent_lab)
        status.update({"status": "running", "current": "starting", "heartbeat_at": _utc_now_iso()})
        await _save_status(config_service, parent_lab, status)
        logger.info("[HomepagePrefetch] Background task started for %s", parent_lab)

        async def _update_progress(processed: int, total: int, current: str) -> None:
            status.update(
                {
                    "processed": processed,
                    "total": total,
                    "current": current,
                    "heartbeat_at": _utc_now_iso(),
                }
            )
            await _save_status(config_service, parent_lab, status)

        try:
            svc = HomepagePreviewService()
            result = await svc.prefetch_all(
                session=session,
                parent_lab=parent_lab,
                progress_callback=_update_progress,
            )
            status.update(
                {
                    "status": "completed",
                    "processed": result["total"],
                    "total": result["total"],
                    "current": "done",
                    "errors": result["failed"],
                    "heartbeat_at": _utc_now_iso(),
                }
            )
            await _save_status(config_service, parent_lab, status)
            logger.info("[HomepagePrefetch] Completed: %s", result)
        except asyncio.CancelledError:
            status.update(
                {
                    "status": "cancelled",
                    "current": "cancelled",
                    "heartbeat_at": _utc_now_iso(),
                }
            )
            await _save_status(config_service, parent_lab, status)
            raise
        except Exception:
            logger.exception("[HomepagePrefetch] Background task failed")
            status.update(
                {
                    "status": "error",
                    "current": "failed",
                    "heartbeat_at": _utc_now_iso(),
                }
            )
            await _save_status(config_service, parent_lab, status)
            raise
