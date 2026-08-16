"""
Collect task list/trigger endpoints and the background task runner.
采集任务列表/触发接口与后台执行器

Split from collect.py; routes keep the original /collect prefix.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.academic.schemas.collect import (
    DEFAULT_START_YEAR,
    MIN_START_YEAR,
    CollectTaskListResponse,
    CollectTaskResponse,
    TriggerCollectTaskRequest,
    get_current_year,
)
from app.domains.academic.services.collect_background_service import CollectBackgroundService
from app.domains.academic.services.collect_service import CollectService
from app.domains.shared.api.auth import require_super_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/collect", tags=["Collect Configuration"])


# Background task runner


async def run_collect_task_background(task_id: int):
    """
    Fire-and-forget background task execution.
    Runs the collection task in-process using async/await.
    This avoids database connection issues with separate processes.
    """
    bg_service = CollectBackgroundService()

    # First, update task status to running immediately
    await bg_service.start_task_if_pending(task_id)

    try:
        progress = await bg_service.run_unified_collect(task_id)

        if progress.status == "completed":
            logging.info(
                "[BACKGROUND] 任务 #%s 完成! Works: %s, Authors: %s, "
                "Normalized: %s, Synced to Talent: %s (Created: %s, Updated: %s), "
                "Tech Tags: %s",
                task_id,
                progress.total_works,
                progress.total_authors,
                progress.normalized_authors,
                progress.synced_authors,
                progress.created_talents,
                progress.updated_talents,
                progress.created_tech_tags,
            )
        else:
            logging.error("[BACKGROUND] 任务 #%s 失败: %s", task_id, progress.errors)
    except Exception as e:
        logger.exception(f"Background task {task_id} failed")
        await bg_service.fail_task_if_running(task_id, str(e))


# ============ Collect Task Endpoints ============


@router.get(
    "/tasks",
    response_model=CollectTaskListResponse,
    summary="获取采集任务列表",
    description="获取采集任务列表（分页）",
)
async def list_tasks(
    status: str | None = Query(None, description="按状态筛选"),
    tech_domain_id: int | None = Query(None, description="按技术领域筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_super_admin),
):
    """List collect tasks."""
    service = CollectService(session)
    tasks, total = await service.list_tasks(
        status=status,
        tech_domain_id=tech_domain_id,
        page=page,
        page_size=page_size,
    )

    items = []
    for t in tasks:
        # 从 time_window_start/end 提取年份
        start_year = t.time_window_start.year if t.time_window_start else DEFAULT_START_YEAR
        end_year = t.time_window_end.year if t.time_window_end else None
        # 如果 end_year 是当前年份且 time_window_end 接近当前时间，则显示为"至今"
        current_year = get_current_year()
        if end_year == current_year and t.time_window_end:
            # 检查是否是"至今"（接近当前时间）
            from datetime import timedelta

            if datetime.now(timezone.utc).replace(tzinfo=None) - t.time_window_end < timedelta(
                days=1
            ):
                end_year = None

        items.append(
            CollectTaskResponse(
                task_id=t.task_id,
                task_code=t.task_code,
                tech_domain_id=t.tech_domain_id,
                tech_domain_name=t.tech_domain.domain_name if t.tech_domain else None,
                start_year=start_year,
                end_year=end_year,
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
        )

    return CollectTaskListResponse(items=items, total=total, page=page, page_size=page_size)


@router.post(
    "/tasks",
    response_model=CollectTaskResponse,
    summary="触发采集任务",
    description="""
触发采集任务。

**固定参数：**
- 数据类型：学者、论文、机构

**可配置参数：**
- tech_domain_id：技术领域ID（必填）
- start_year：起始年份，默认2020，最小2015
- end_year：截止年份，默认为至今

**说明：**
采集任务在后台异步执行，可通过任务列表查看进度。
""",
)
async def trigger_task(
    request: TriggerCollectTaskRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_super_admin),
):
    """Trigger a new collect task."""
    service = CollectService(session)

    # Validate tech domain exists
    domain = await service.get_tech_domain_by_id(request.tech_domain_id)
    if not domain:
        raise HTTPException(status_code=404, detail="Tech domain not found")

    # Check if has venue bindings configured
    bindings = await service.get_venue_bindings_by_tech_domain(request.tech_domain_id)
    if not bindings:
        raise HTTPException(
            status_code=400,
            detail="Tech domain has no venue bindings configured. Please bind venues first.",
        )

    # Check if there's already a running task for this domain
    active_tasks = await service.get_active_tasks()
    for t in active_tasks:
        if t.tech_domain_id == request.tech_domain_id:
            raise HTTPException(
                status_code=400,
                detail=f"There is already a running task (#{t.task_id}) for this tech domain.",
            )

    # Validate year range
    current_year = get_current_year()
    start_year = request.start_year

    if start_year < MIN_START_YEAR:
        raise HTTPException(status_code=400, detail=f"起始年份不能早于 {MIN_START_YEAR} 年")
    if start_year > current_year:
        raise HTTPException(status_code=400, detail=f"起始年份不能晚于当前年份 ({current_year})")

    end_year = request.end_year
    if end_year is not None:
        if end_year < start_year:
            raise HTTPException(status_code=400, detail="截止年份不能早于起始年份")
        if end_year > current_year:
            raise HTTPException(
                status_code=400, detail=f"截止年份不能晚于当前年份 ({current_year})"
            )

    # Calculate time window (naive datetime for WITHOUT TIME ZONE columns)
    time_start = datetime(start_year, 1, 1)
    if end_year is None:
        time_end = datetime.now(timezone.utc).replace(tzinfo=None)  # 至今
    else:
        time_end = datetime(end_year, 12, 31, 23, 59, 59)

    # Create task with sub-tasks
    task = await service.create_task_with_subtasks(
        tech_domain_id=request.tech_domain_id,
        user_id=current_user.get("user_id"),
        time_window_start=time_start,
        time_window_end=time_end,
    )

    logger.info(
        f"Created collect task {task.task_id} for {domain.domain_name} "
        f"with {len(task.venue_snapshot or [])} venues, year range: {start_year}-{end_year or '至今'}"
    )

    # Start background task using asyncio (in-process, works reliably on Windows)
    asyncio.create_task(run_collect_task_background(task.task_id))
    logger.info(f"Background task started for task #{task.task_id}")

    return CollectTaskResponse(
        task_id=task.task_id,
        task_code=task.task_code,
        tech_domain_id=task.tech_domain_id,
        tech_domain_name=domain.domain_name,
        start_year=start_year,
        end_year=end_year,
        triggered_by=task.triggered_by,
        triggered_at=task.triggered_at,
        status=task.status,
        progress_percent=task.progress_percent,
        current_step=task.current_step,
        total_records=task.total_records,
        processed_records=task.processed_records,
        success_records=task.success_records,
        failed_records=task.failed_records,
        skipped_records=task.skipped_records,
        started_at=task.started_at,
        completed_at=task.completed_at,
        error_message=task.error_message,
        error_details=task.error_details,
        result_summary=task.result_summary,
        venue_snapshot=task.venue_snapshot,
        created_at=task.created_at,
    )
