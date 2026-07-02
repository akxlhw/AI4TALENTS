"""Lab domain API — aggregates all lab routers into one."""

from __future__ import annotations

from fastapi import APIRouter

from app.domains.lab.api import import_endpoint, stats, talents

router = APIRouter()
router.include_router(import_endpoint.router)
router.include_router(talents.router)
router.include_router(stats.router)

__all__ = ["router"]
