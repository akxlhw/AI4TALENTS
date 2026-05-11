"""
Open Source API — aggregate all sub-routers.
"""

from fastapi import APIRouter

from app.domains.open_source.api.collection import router as collection_router
from app.domains.open_source.api.developers import router as developers_router
from app.domains.open_source.api.favourites import router as favourites_router
from app.domains.open_source.api.repo_config import router as repo_config_router
from app.domains.open_source.api.stats import router as stats_router

router = APIRouter()

router.include_router(repo_config_router)
router.include_router(collection_router)
router.include_router(developers_router)
router.include_router(favourites_router)
router.include_router(stats_router)

__all__ = ["router"]
