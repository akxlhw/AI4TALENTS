"""
Open Source API — aggregate all sub-routers.
"""

from fastapi import APIRouter

from app.domains.open_source.api.collection import router as collection_router
from app.domains.open_source.api.developers import router as developers_router
from app.domains.open_source.api.discover import router as discover_router
from app.domains.open_source.api.favourites import router as favourites_router
from app.domains.open_source.api.open_api import router as open_api_router
from app.domains.open_source.api.repo_config import router as repo_config_router
from app.domains.open_source.api.stats import router as stats_router

router = APIRouter()

# collection_router must come first: its static path /repo-configs/collect-check
# would otherwise be swallowed by repo_config_router's /repo-configs/{id} (int
# parse 422), silently disabling the batch-collect history warning
router.include_router(collection_router)
router.include_router(repo_config_router)
router.include_router(developers_router)
router.include_router(favourites_router)
router.include_router(discover_router)
router.include_router(stats_router)
router.include_router(open_api_router)

__all__ = ["router"]
