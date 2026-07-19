"""Competition domain API — aggregates all competition routers into one."""

from __future__ import annotations

from fastapi import APIRouter

from app.domains.competition.api import contests, import_endpoint, stats, talents

router = APIRouter()
router.include_router(import_endpoint.router)
router.include_router(talents.router)
router.include_router(contests.router)
router.include_router(stats.router)

__all__ = ["router"]
