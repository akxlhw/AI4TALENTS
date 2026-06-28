"""lab_web_site collection endpoints (site listing + task triggering/status)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.lab_web.schemas.lab_web_site import (
    SiteBrief,
    SiteCollectStartResponse,
    SiteCollectTaskResponse,
)
from app.domains.lab_web.services.lw_site_collection_service import (
    LWSiteCollectionService,
)
from app.domains.shared.schemas.common import SuccessResponse

router = APIRouter(prefix="/lab-web-sites", tags=["Lab Web Site Talent"])


@router.get("/sites", response_model=list[SiteBrief])
async def list_sites(
    only_active: bool = False,
    session: AsyncSession = Depends(get_async_session),
) -> list[SiteBrief]:
    """List registered lab sites."""
    service = LWSiteCollectionService(session)
    sites = await service.list_sites(only_active=only_active)
    return [SiteBrief.model_validate(s) for s in sites]


@router.post("/sites/{site_code}/collect", response_model=SiteCollectStartResponse)
async def collect_site(
    site_code: str,
    force_reparse: bool = Query(False),
    session: AsyncSession = Depends(get_async_session),
) -> SiteCollectStartResponse:
    """Start a background LLM collection for one site. Returns the task id."""
    service = LWSiteCollectionService(session)
    try:
        task_id = await service.start_collection(site_code, force_reparse=force_reparse)
    except LookupError:
        raise HTTPException(status_code=404, detail="Site not found") from None
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    task = await service.get_task_status(task_id)
    return SiteCollectStartResponse(
        task_id=task_id, status=str(task.status) if task else "pending"
    )


@router.get("/tasks/{task_id}", response_model=SiteCollectTaskResponse)
async def get_site_task(
    task_id: int,
    session: AsyncSession = Depends(get_async_session),
) -> SiteCollectTaskResponse:
    """Poll a site collection task's status."""
    service = LWSiteCollectionService(session)
    task = await service.get_task_status(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found") from None
    return SiteCollectTaskResponse.model_validate(task)


@router.post("/tasks/{task_id}/cancel", response_model=SuccessResponse)
async def cancel_site_task(
    task_id: int,
    session: AsyncSession = Depends(get_async_session),
) -> SuccessResponse:
    service = LWSiteCollectionService(session)
    await service.cancel_collection(task_id)
    return SuccessResponse(message="Task cancelled")


@router.get("/sites/{site_code}/review")
async def review_site(
    site_code: str,
    session: AsyncSession = Depends(get_async_session),
):
    """List needs_review parse results for manual inspection."""
    service = LWSiteCollectionService(session)
    items = await service.get_review_items(site_code)
    return [
        {
            "page_id": i.page_id,
            "parse_status": i.parse_status,
            "parse_error": i.parse_error,
            "fetched_at": i.fetched_at,
        }
        for i in items
    ]
