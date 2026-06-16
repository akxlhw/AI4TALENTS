"""Genealogy API endpoints for academic talent networks."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_async_session
from app.domains.academic.schemas.genealogy import (
    GenealogyNetworkResponse,
    InfluenceRankingItem,
    SyncStatusResponse,
)
from app.domains.academic.services.genealogy_service import GenealogyService
from app.domains.academic.services.influence_service import InfluenceService
from app.domains.shared.api.auth import require_admin
from app.domains.shared.schemas.common import (
    PaginatedResponse,
    TaskStartResponse,
)
from app.domains.shared.services.config_service import ConfigService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/talents", tags=["Genealogy"])

GENEALOGY_SYNC_STATUS_KEY = "genealogy_sync_status"
DEFAULT_SYNC_STATUS = {
    "status": "idle",
    "processed": 0,
    "total": 0,
    "edges": 0,
    "current_phase": "",
}


async def _load_sync_status(config_service: ConfigService) -> dict:
    """Load sync status from persistent config store."""
    status = await config_service.get_value(
        GENEALOGY_SYNC_STATUS_KEY, default=None, use_cache=False
    )
    if status is None:
        return DEFAULT_SYNC_STATUS.copy()
    return {**DEFAULT_SYNC_STATUS, **status}


async def _save_sync_status(config_service: ConfigService, status: dict) -> None:
    """Persist sync status to config store."""
    await config_service.set_value(
        GENEALOGY_SYNC_STATUS_KEY,
        status,
        config_type="json",
    )
    await config_service.session.commit()


@router.get(
    "/{talent_id}/genealogy",
    response_model=GenealogyNetworkResponse,
    summary="获取学术族谱网络",
)
async def get_genealogy_network(
    talent_id: int,
    depth: int = Query(2, ge=1, le=3),
    min_confidence: float = Query(0.3, ge=0.0, le=1.0),
    relationship_type: str | None = Query(
        None, description="advisor_student / mentor_mentee / senior_junior"
    ),
    tier_filter: str | None = Query(None, description="tier1 / tier2 / tier3 / tier4"),
    session: AsyncSession = Depends(get_async_session),
) -> GenealogyNetworkResponse:
    """Get genealogy network centered on a given talent."""
    service = GenealogyService(session)
    network = await service.get_network(
        talent_id=talent_id,
        depth=depth,
        min_confidence=min_confidence,
        relationship_type=relationship_type,
        tier_filter=tier_filter,
    )
    if network is None:
        raise HTTPException(status_code=404, detail="Talent not found")
    return network  # type: ignore[return-value]


@router.post(
    "/genealogy/sync",
    response_model=TaskStartResponse,
    summary="触发学术族谱计算（管理员）",
)
async def sync_genealogy(
    admin_user: dict = Depends(require_admin),
    session: AsyncSession = Depends(get_async_session),
) -> TaskStartResponse:
    """Trigger influence score + genealogy inference (admin only)."""
    config_service = ConfigService(session)
    status = await _load_sync_status(config_service)
    if status["status"] == "running":
        raise HTTPException(status_code=409, detail="Genealogy sync already in progress")

    status.update(
        {
            "status": "pending",
            "processed": 0,
            "total": 0,
            "edges": 0,
            "current_phase": "initializing",
        }
    )
    await _save_sync_status(config_service, status)

    # Use asyncio.create_task with timeout wrapper
    task = asyncio.create_task(_run_with_timeout(), name="genealogy_sync")
    task.add_done_callback(_on_genealogy_task_done)
    return TaskStartResponse(message="Genealogy sync started in background")


@router.get(
    "/genealogy/sync-status",
    response_model=SyncStatusResponse,
    summary="获取族谱计算进度",
)
async def get_genealogy_sync_status(
    session: AsyncSession = Depends(get_async_session),
) -> SyncStatusResponse:
    """Get current genealogy sync progress."""
    config_service = ConfigService(session)
    status = await _load_sync_status(config_service)
    return SyncStatusResponse(**status)


@router.get(
    "/genealogy/influence-ranking",
    response_model=PaginatedResponse[InfluenceRankingItem],
    summary="影响力排名",
)
async def get_influence_ranking(
    tier: str | None = Query(None, description="tier1 / tier2 / tier3 / tier4"),
    limit: int = Query(
        settings.GENEALOGY_RANKING_DEFAULT_LIMIT,
        ge=1,
        le=settings.GENEALOGY_RANKING_MAX_LIMIT,
    ),
    session: AsyncSession = Depends(get_async_session),
) -> PaginatedResponse[InfluenceRankingItem]:
    """Get influence ranking list."""
    service = InfluenceService(session)
    items = await service.get_ranking(tier=tier, limit=limit)
    return PaginatedResponse(
        items=items,  # type: ignore[arg-type]
        total=len(items),
        page=1,
        page_size=limit,
        total_pages=1,
    )


async def _run_with_timeout() -> None:
    """Run genealogy sync with timeout and retry."""
    sync_timeout = settings.SYNC_TIMEOUT
    max_retries = 2

    for attempt in range(1, max_retries + 1):
        try:
            await asyncio.wait_for(_run_genealogy_sync(), timeout=sync_timeout)
            return
        except TimeoutError:
            logger.warning(f"[GenealogySync] Timeout on attempt {attempt}/{max_retries}")
            if attempt == max_retries:
                logger.error("[GenealogySync] All retry attempts exhausted (timeout)")
        except Exception:
            if attempt < max_retries:
                logger.warning(
                    f"[GenealogySync] Failed on attempt {attempt}/{max_retries}, retrying..."
                )
            else:
                raise


def _on_genealogy_task_done(task: asyncio.Task) -> None:
    """Callback when genealogy background task finishes."""
    try:
        task.result()
    except asyncio.CancelledError:
        logger.warning("[GenealogySync] Background task was cancelled")
    except Exception:
        logger.exception("[GenealogySync] Background task failed")


async def _run_genealogy_sync() -> None:
    """Background task: compute influence scores then infer genealogy."""
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        config_service = ConfigService(session)
        status = await _load_sync_status(config_service)
        status.update(
            {
                "status": "running",
                "processed": 0,
                "total": 0,
                "edges": 0,
                "current_phase": "starting",
            }
        )
        await _save_sync_status(config_service, status)
        logger.info("[GenealogySync] Background task started")

        async def _update_progress(processed: int, total: int, edges: int) -> None:
            status.update({"processed": processed, "total": total, "edges": edges})
            await _save_sync_status(config_service, status)

        try:
            status["current_phase"] = "influence_scores"
            await _save_sync_status(config_service, status)

            result = await GenealogyService.run_background_sync(progress_callback=_update_progress)
            inf_result = result["influence"]
            gen_result = result["genealogy"]
            status.update(
                {
                    "status": "completed",
                    "processed": gen_result["total_raw_works"],
                    "total": inf_result.get("total", 0),
                    "edges": gen_result["edges_upserted"],
                    "current_phase": "done",
                }
            )
            await _save_sync_status(config_service, status)
        except asyncio.CancelledError:
            status.update({"status": "cancelled", "current_phase": "cancelled"})
            await _save_sync_status(config_service, status)
            raise
        except Exception:
            logger.exception("[GenealogySync] Background task failed")
            status.update({"status": "error", "current_phase": "failed"})
            await _save_sync_status(config_service, status)
            raise
