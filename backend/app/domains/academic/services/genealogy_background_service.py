"""Background runner and status store for genealogy sync.

Keeps AsyncSessionLocal usage in the Service layer so API endpoints stay thin
(see collect_background_service.py for the same pattern).
"""

from __future__ import annotations

import asyncio
import logging

from app.core.database import AsyncSessionLocal
from app.domains.academic.services.genealogy_service import GenealogyService
from app.domains.shared.services.config_service import ConfigService

logger = logging.getLogger(__name__)

GENEALOGY_SYNC_STATUS_KEY = "genealogy_sync_status"
DEFAULT_SYNC_STATUS = {
    "status": "idle",
    "processed": 0,
    "total": 0,
    "edges": 0,
    "current_phase": "",
}


async def load_sync_status(config_service: ConfigService) -> dict:
    """Load sync status from persistent config store."""
    status = await config_service.get_value(
        GENEALOGY_SYNC_STATUS_KEY, default=None, use_cache=False
    )
    if status is None:
        return DEFAULT_SYNC_STATUS.copy()
    return {**DEFAULT_SYNC_STATUS, **status}


async def save_sync_status(config_service: ConfigService, status: dict) -> None:
    """Persist sync status to config store."""
    await config_service.set_value(
        GENEALOGY_SYNC_STATUS_KEY,
        status,
        config_type="json",
    )
    await config_service.session.commit()


async def run_genealogy_sync() -> None:
    """Background task: compute influence scores then infer genealogy."""
    async with AsyncSessionLocal() as session:
        config_service = ConfigService(session)
        status = await load_sync_status(config_service)
        status.update(
            {
                "status": "running",
                "processed": 0,
                "total": 0,
                "edges": 0,
                "current_phase": "starting",
            }
        )
        await save_sync_status(config_service, status)
        logger.info("[GenealogySync] Background task started")

        async def _update_progress(processed: int, total: int, edges: int) -> None:
            status.update({"processed": processed, "total": total, "edges": edges})
            await save_sync_status(config_service, status)

        try:
            status["current_phase"] = "influence_scores"
            await save_sync_status(config_service, status)

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
            await save_sync_status(config_service, status)
        except asyncio.CancelledError:
            status.update({"status": "cancelled", "current_phase": "cancelled"})
            await save_sync_status(config_service, status)
            raise
        except Exception:
            logger.exception("[GenealogySync] Background task failed")
            status.update({"status": "error", "current_phase": "failed"})
            await save_sync_status(config_service, status)
            raise
