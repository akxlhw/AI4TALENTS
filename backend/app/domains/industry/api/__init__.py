"""Industry domain API — aggregates all industry routers into one."""

from __future__ import annotations

from fastapi import APIRouter

from app.domains.industry.api import import_endpoint, positions, talents

router = APIRouter()
router.include_router(import_endpoint.router)
router.include_router(positions.router)
router.include_router(talents.router)

__all__ = ["router"]
