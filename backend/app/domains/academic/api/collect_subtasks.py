"""
Venue sub-task endpoints (list/progress/retry).
Venue 子任务接口

Split from collect.py; routes keep the original /collect prefix.
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.academic.schemas.collect import SubTaskActionResponse
from app.domains.academic.schemas.venue import VenueSubTaskListResponse, VenueSubTaskResponse
from app.domains.academic.services.collect_background_service import CollectBackgroundService
from app.domains.academic.services.collect_service import CollectService
from app.domains.shared.api.auth import require_super_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/collect", tags=["Collect Configuration"])


# ============ Venue Sub-Task Endpoints ============


@router.get(
    "/tasks/{task_id}/sub-tasks",
    response_model=VenueSubTaskListResponse,
    summary="获取任务的Venue子任务列表",
    description="获取指定任务下所有Venue级别的子任务",
)
async def get_task_sub_tasks(
    task_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_super_admin),
):
    """Get venue sub-tasks for a task."""
    service = CollectService(session)
    sub_tasks = await service.get_task_sub_tasks(task_id)

    return VenueSubTaskListResponse(
        total=len(sub_tasks), items=[VenueSubTaskResponse.model_validate(st) for st in sub_tasks]
    )


@router.get(
    "/tasks/{task_id}/progress",
    response_model=dict,
    summary="获取任务详细进度",
    description="获取任务的详细进度信息，包括各Venue子任务状态",
)
async def get_task_detailed_progress(
    task_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_super_admin),
):
    """Get detailed progress for a task."""
    service = CollectService(session)
    return await service.get_task_detailed_progress(task_id)


@router.post(
    "/tasks/{task_id}/sub-tasks/{sub_task_id}/retry",
    response_model=SubTaskActionResponse,
    summary="重试失败的子任务",
    description="重新执行失败的Venue子任务",
)
async def retry_sub_task(
    task_id: int,
    sub_task_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_super_admin),
):
    """Retry a failed venue sub-task."""
    service = CollectService(session)
    sub_task = await service.get_sub_task_by_id(sub_task_id)

    if not sub_task or sub_task.task_id != task_id:
        raise HTTPException(status_code=404, detail="Sub-task not found")

    if sub_task.status != "failed":
        raise HTTPException(status_code=400, detail="Only failed sub-tasks can be retried")

    await service.retry_sub_task(task_id, sub_task_id)

    # Trigger background re-execution of the sub-task
    async def _run_retry():
        bg_service = CollectBackgroundService()
        await bg_service.run_single_sub_task(task_id, sub_task_id)

    asyncio.create_task(_run_retry())
    logger.info(f"Sub-task #{sub_task_id} retry triggered in background")

    return SubTaskActionResponse(message="Sub-task retry started", sub_task_id=sub_task_id)
