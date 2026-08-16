"""Open Source — Auto-discover endpoints (GitHub search by tech direction)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.open_source.api.auth import require_super_admin
from app.domains.open_source.services.discover_service import (
    get_discovery_status,
    import_discovered,
    start_discovery,
)

router = APIRouter(prefix="/open-source", tags=["Open Source Talent"])


class DiscoverStartRequest(BaseModel):
    """Start a discovery run."""

    direction_codes: list[str] = Field(
        default_factory=list,
        description="Tech direction codes to scan; empty = all seeded directions",
    )
    min_stars: int = Field(default=30000, ge=1000, le=500000, description="Star threshold")
    min_contributors: int = Field(
        default=0, ge=0, le=100000, description="Contributor count threshold (0 = no filter)"
    )


class DiscoverImportItem(BaseModel):
    """One selected repo to import."""

    repo_full_name: str
    tech_element: list[str] = Field(default_factory=lambda: ["ai"])


class DiscoverImportRequest(BaseModel):
    """Import selected discovered repos into os_repo_config."""

    repos: list[DiscoverImportItem] = Field(min_length=1)


@router.post("/discover/start")
async def start_discovery_endpoint(
    data: DiscoverStartRequest,
    session: AsyncSession = Depends(get_async_session),
    _admin: dict = Depends(require_super_admin),
) -> dict:
    """Launch a background GitHub discovery across the selected directions.

    Poll ``GET /open-source/discover/status`` for progress and results.
    Results are preview-only; importing is a separate explicit step.
    """
    # Seed session ensures the status key write below is durable even if
    # the caller's request scope closes immediately.
    await session.commit()
    return await start_discovery(data.direction_codes, data.min_stars, data.min_contributors)


@router.get("/discover/status")
async def discovery_status_endpoint(
    _admin: dict = Depends(require_super_admin),
) -> dict:
    """Current discovery status: progress counters + full result list."""
    return await get_discovery_status()


@router.post("/discover/import")
async def discovery_import_endpoint(
    data: DiscoverImportRequest,
    _admin: dict = Depends(require_super_admin),
) -> dict:
    """Import selected discovered repos (creates os_repo_config rows).

    Reuses the batch-create path: existing repos are skipped, fresh
    metadata is fetched from GitHub per repo.
    """
    return await import_discovered(
        [item.model_dump() for item in data.repos],
    )
