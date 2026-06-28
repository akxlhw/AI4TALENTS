"""lab_web collection endpoints (lab listing + task triggering/status)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.lab_web.schemas.lab_web import (
    CollectStartResponse,
    CollectTaskResponse,
    LabBrief,
)
from app.domains.lab_web.services.lw_collection_service import LWCollectionService
from app.domains.shared.schemas.common import SuccessResponse

router = APIRouter(prefix="/lab-web", tags=["Lab Web Talent"])


@router.get("/labs", response_model=list[LabBrief])
async def list_labs(
    only_active: bool = False,
    session: AsyncSession = Depends(get_async_session),
) -> list[LabBrief]:
    """List registered AI labs."""
    service = LWCollectionService(session)
    labs = await service.list_labs(only_active=only_active)
    return [LabBrief.model_validate(lab) for lab in labs]


@router.post("/labs/{lab_id}/collect", response_model=CollectStartResponse)
async def collect_lab(
    lab_id: int,
    session: AsyncSession = Depends(get_async_session),
) -> CollectStartResponse:
    """Start a background collection for one lab. Returns the task id."""
    service = LWCollectionService(session)
    try:
        task_id = await service.start_collection(lab_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="Lab not found") from None
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    task = await service.get_task_status(task_id)
    return CollectStartResponse(task_id=task_id, status=str(task.status) if task else "pending")


@router.get("/tasks/{task_id}", response_model=CollectTaskResponse)
async def get_task(
    task_id: int,
    session: AsyncSession = Depends(get_async_session),
) -> CollectTaskResponse:
    """Poll a collection task's status."""
    service = LWCollectionService(session)
    task = await service.get_task_status(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found") from None
    return CollectTaskResponse.model_validate(task)


@router.post("/tasks/{task_id}/cancel", response_model=SuccessResponse)
async def cancel_task(
    task_id: int,
    session: AsyncSession = Depends(get_async_session),
) -> SuccessResponse:
    """Request cancellation of a running collection task."""
    service = LWCollectionService(session)
    ok = await service.cancel_collection(task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Task not found") from None
    return SuccessResponse(message="Task cancelled")
