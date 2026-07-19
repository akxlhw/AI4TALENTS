"""Background runner and status store for lab homepage prefetch.

Keeps AsyncSessionLocal usage in the Service layer so API endpoints stay thin.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.core.database import AsyncSessionLocal
from app.domains.lab.services.homepage_preview_service import HomepagePreviewService
from app.domains.shared.services.config_service import ConfigService

logger = logging.getLogger(__name__)

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


def build_status_key(parent_lab: str) -> str:
    """Build the per-lab status config key."""
    return f"{PREFETCH_STATUS_KEY}:{parent_lab}"


def utc_now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def is_heartbeat_alive(heartbeat_at: str | None) -> bool:
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


async def load_prefetch_status(config_service: ConfigService, parent_lab: str) -> dict:
    """Load per-lab prefetch status from persistent config store."""
    status = await config_service.get_value(
        build_status_key(parent_lab), default=None, use_cache=False
    )
    if status is None:
        return DEFAULT_STATUS.copy()
    return {**DEFAULT_STATUS, **status}


async def save_prefetch_status(
    config_service: ConfigService, parent_lab: str, status: dict
) -> None:
    """Persist per-lab prefetch status to config store."""
    await config_service.set_value(build_status_key(parent_lab), status, config_type="json")
    await config_service.session.commit()


async def run_prefetch(parent_lab: str) -> None:
    """Background coroutine: batch fetch + cache homepages."""
    async with AsyncSessionLocal() as session:
        config_service = ConfigService(session)
        status = await load_prefetch_status(config_service, parent_lab)
        status.update({"status": "running", "current": "starting", "heartbeat_at": utc_now_iso()})
        await save_prefetch_status(config_service, parent_lab, status)
        logger.info("[HomepagePrefetch] Background task started for %s", parent_lab)

        async def _update_progress(processed: int, total: int, current: str) -> None:
            status.update(
                {
                    "processed": processed,
                    "total": total,
                    "current": current,
                    "heartbeat_at": utc_now_iso(),
                }
            )
            await save_prefetch_status(config_service, parent_lab, status)

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
                    "heartbeat_at": utc_now_iso(),
                }
            )
            await save_prefetch_status(config_service, parent_lab, status)
            logger.info("[HomepagePrefetch] Completed: %s", result)
        except asyncio.CancelledError:
            status.update(
                {
                    "status": "cancelled",
                    "current": "cancelled",
                    "heartbeat_at": utc_now_iso(),
                }
            )
            await save_prefetch_status(config_service, parent_lab, status)
            raise
        except Exception:
            logger.exception("[HomepagePrefetch] Background task failed")
            status.update(
                {
                    "status": "error",
                    "current": "failed",
                    "heartbeat_at": utc_now_iso(),
                }
            )
            await save_prefetch_status(config_service, parent_lab, status)
            raise
