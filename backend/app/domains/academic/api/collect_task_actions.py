"""
Collect task detail/action endpoints (get/execute/rerun/cancel/delete/active).
采集任务详情与操作接口

Split from collect.py; routes keep the original /collect prefix.
Route order preserved: /tasks/{task_id} family before /tasks/active.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.academic.api.collect_tasks import run_collect_task_background
from app.domains.academic.schemas.collect import (
    DEFAULT_START_YEAR,
    CollectTaskResponse,
    TaskActionResponse,
    get_current_year,
)
from app.domains.academic.services.collect_service import CollectService
from app.domains.shared.api.auth import require_super_admin
from app.domains.shared.schemas.common import SuccessResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/collect", tags=["Collect Configuration"])


@router.get(
    "/tasks/{task_id}",
    response_model=CollectTaskResponse,
    summary="获取采集任务详情",
    description="获取指定采集任务的详细信息，包含执行日志",
)
async def get_task(
    task_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_super_admin),
):
    """Get collect task details."""
    service = CollectService(session)
    task = await service.get_task_by_id(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # 从 time_window_start/end 提取年份
    start_year = task.time_window_start.year if task.time_window_start else DEFAULT_START_YEAR
    end_year = task.time_window_end.year if task.time_window_end else None
    # 如果 end_year 是当前年份且 time_window_end 接近当前时间，则显示为"至今"
    current_year = get_current_year()
    if end_year == current_year and task.time_window_end:
        from datetime import timedelta

        if datetime.now(timezone.utc).replace(tzinfo=None) - task.time_window_end < timedelta(
            days=1
        ):
            end_year = None

    return CollectTaskResponse(
        task_id=task.task_id,
        task_code=task.task_code,
        tech_domain_id=task.tech_domain_id,
        tech_domain_name=task.tech_domain.domain_name if task.tech_domain else None,
        start_year=start_year,
        end_year=end_year,
        triggered_by=task.triggered_by,
        triggered_at=task.triggered_at,
        status=task.status,
        progress_percent=task.progress_percent or 0,
        current_step=task.current_step,
        total_records=task.total_records or 0,
        processed_records=task.processed_records or 0,
        success_records=task.success_records or 0,
        failed_records=task.failed_records or 0,
        skipped_records=task.skipped_records or 0,
        started_at=task.started_at,
        completed_at=task.completed_at,
        error_message=task.error_message,
        error_details=task.error_details,
        result_summary=task.result_summary,
        execution_logs=task.execution_logs or [],
        venue_snapshot=task.venue_snapshot,
        created_at=task.created_at,
    )


@router.post(
    "/tasks/{task_id}/execute",
    response_model=TaskActionResponse,
    summary="执行采集任务",
    description="执行待执行状态的采集任务",
)
async def execute_task(
    task_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_super_admin),
):
    """Execute a pending task."""
    service = CollectService(session)
    task = await service.get_task_by_id(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status != "pending":
        raise HTTPException(
            status_code=400, detail=f"Task is not in pending status (current: {task.status})"
        )

    # Check if there's already a running task
    active_tasks = await service.get_active_tasks()
    for t in active_tasks:
        if t.task_id != task_id and t.status == "running":
            raise HTTPException(
                status_code=400,
                detail=f"There is already a running task (#{t.task_id}). Please wait for it to complete.",
            )

    # Start background execution
    asyncio.create_task(run_collect_task_background(task_id))
    logger.info(f"Background task started for task #{task_id}")

    return TaskActionResponse(message="Task execution started", task_id=task_id)


@router.post(
    "/tasks/{task_id}/rerun",
    response_model=TaskActionResponse,
    summary="重跑失败的采集任务（保留 checkpoint）",
    description="将 failed 任务重置为 pending 并从 last_completed_phase 继续，无需全量重跑",
)
async def rerun_failed_task(
    task_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_super_admin),
):
    """Reset a failed task to pending, preserving its checkpoint."""
    service = CollectService(session)
    task = await service.get_task_by_id(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status not in ("failed", "cancelled"):
        raise HTTPException(
            status_code=400,
            detail=f"Only failed or cancelled tasks can be rerun (current: {task.status})",
        )

    # Check if there's already a running task
    active_tasks = await service.get_active_tasks()
    for t in active_tasks:
        if t.task_id != task_id and t.status == "running":
            raise HTTPException(
                status_code=400,
                detail=f"There is already a running task (#{t.task_id}). Please wait for it to complete.",
            )

    # Reset to pending, keep last_completed_phase for checkpoint resume
    await service.reset_task_for_rerun(task)
    logger.info(
        f"Task #{task_id} reset to pending for rerun (checkpoint: phase {task.last_completed_phase})"
    )

    # Start background execution (orchestrator will resume from checkpoint)
    asyncio.create_task(run_collect_task_background(task_id))
    logger.info(f"Background task started for rerun of task #{task_id}")

    return TaskActionResponse(
        message=f"Task rerun started from phase {task.last_completed_phase or 0}",
        task_id=task_id,
    )


@router.post(
    "/tasks/{task_id}/cancel",
    response_model=SuccessResponse,
    summary="取消采集任务",
    description="取消正在执行的采集任务",
)
async def cancel_task(
    task_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_super_admin),
):
    """Cancel a running task."""
    service = CollectService(session)
    task = await service.get_task_by_id(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status not in ["pending", "running"]:
        raise HTTPException(status_code=400, detail="Task cannot be cancelled")

    await service.cancel_task(task_id)

    return SuccessResponse(message="Task cancelled")


@router.delete(
    "/tasks/{task_id}",
    response_model=TaskActionResponse,
    summary="删除采集任务",
    description="删除已完成的采集任务记录",
)
async def delete_task(
    task_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_super_admin),
):
    """Delete a completed task record."""
    service = CollectService(session)
    task = await service.get_task_by_id(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status in ["pending", "running"]:
        raise HTTPException(status_code=400, detail="Cannot delete running or pending task")

    await service.delete_task(task_id)

    return TaskActionResponse(message="Task deleted", task_id=task_id)


@router.get(
    "/tasks/active",
    response_model=list[CollectTaskResponse],
    summary="获取活动任务",
    description="获取当前正在执行或待执行的任务",
)
async def get_active_tasks(
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_super_admin),
):
    """Get all active tasks."""
    service = CollectService(session)
    tasks = await service.get_active_tasks()

    return [
        CollectTaskResponse(
            task_id=t.task_id,
            task_code=t.task_code,
            tech_domain_id=t.tech_domain_id,
            tech_domain_name=t.tech_domain.domain_name if t.tech_domain else None,
            start_year=t.time_window_start.year if t.time_window_start else DEFAULT_START_YEAR,
            end_year=t.time_window_end.year if t.time_window_end else None,
            triggered_by=t.triggered_by,
            triggered_at=t.triggered_at,
            status=t.status,
            progress_percent=t.progress_percent or 0,
            current_step=t.current_step,
            total_records=t.total_records or 0,
            processed_records=t.processed_records or 0,
            success_records=t.success_records or 0,
            failed_records=t.failed_records or 0,
            skipped_records=t.skipped_records or 0,
            started_at=t.started_at,
            completed_at=t.completed_at,
            error_message=t.error_message,
            error_details=t.error_details,
            result_summary=t.result_summary,
            venue_snapshot=t.venue_snapshot,
            created_at=t.created_at,
        )
        for t in tasks
    ]
