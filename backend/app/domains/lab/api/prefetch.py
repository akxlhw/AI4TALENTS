"""Lab homepage prefetch endpoints — batch fetch & cache personal homepages."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.shared.api.auth import require_admin
from app.domains.shared.schemas.common import TaskStartResponse
from app.domains.shared.services.config_service import ConfigService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/lab", tags=["AI Lab Talent"])

PREFETCH_STATUS_KEY = "lab_homepage_prefetch_status"
DEFAULT_STATUS = {
    "status": "idle",
    "processed": 0,
    "total": 0,
    "current": "",
    "errors": 0,
}


async def _load_status(config_service: ConfigService) -> dict:
    status = await config_service.get_value(PREFETCH_STATUS_KEY, default=None, use_cache=False)
    if status is None:
        return DEFAULT_STATUS.copy()
    return {**DEFAULT_STATUS, **status}


async def _save_status(config_service: ConfigService, status: dict) -> None:
    await config_service.set_value(PREFETCH_STATUS_KEY, status, config_type="json")
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
    status = await _load_status(config_service)
    if status["status"] == "running":
        raise HTTPException(status_code=409, detail="Homepage prefetch already in progress")

    status.update(
        {"status": "pending", "processed": 0, "total": 0, "current": "initializing", "errors": 0}
    )
    await _save_status(config_service, status)

    task = asyncio.create_task(_run_prefetch(parent_lab), name="lab_homepage_prefetch")
    task.add_done_callback(_on_task_done)
    return TaskStartResponse(message=f"Homepage prefetch started for {parent_lab}")


@router.get(
    "/prefetch-homepages/status",
    summary="Get homepage prefetch progress",
)
async def get_prefetch_status(
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    """Return current prefetch progress."""
    config_service = ConfigService(session)
    return await _load_status(config_service)


def _on_task_done(task: asyncio.Task) -> None:
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
        status = await _load_status(config_service)
        status.update({"status": "running", "current": "starting"})
        await _save_status(config_service, status)
        logger.info("[HomepagePrefetch] Background task started for %s", parent_lab)

        async def _update_progress(processed: int, total: int, current: str) -> None:
            status.update({"processed": processed, "total": total, "current": current})
            await _save_status(config_service, status)

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
                    "errors": result["errors"],
                }
            )
            await _save_status(config_service, status)
            logger.info("[HomepagePrefetch] Completed: %s", result)
        except asyncio.CancelledError:
            status.update({"status": "cancelled", "current": "cancelled"})
            await _save_status(config_service, status)
            raise
        except Exception:
            logger.exception("[HomepagePrefetch] Background task failed")
            status.update({"status": "error", "current": "failed"})
            await _save_status(config_service, status)
            raise
