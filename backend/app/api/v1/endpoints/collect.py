"""
Collect configuration API endpoints - MVP v1.2
采集配置相关接口

功能说明：
- 技术领域配置：管理技术领域关联的顶会顶刊
- 采集任务：基于技术领域触发采集，可配置年份范围
- 固定参数：数据类型（学者+论文+机构）
- 可配置参数：时间范围（起始年份~截止年份/至今）
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import require_user
from app.core.database import get_async_session
from app.repositories.collect_repository import CollectTaskRepository, TechDomainCollectRepository
from app.repositories.venue_repository import VenueSubTaskRepository
from app.schemas.collect import (
    DEFAULT_START_YEAR,
    MIN_START_YEAR,
    TASK_STATUS_OPTIONS,
    CollectTaskListResponse,
    CollectTaskResponse,
    SubTaskActionResponse,
    TaskActionResponse,
    TechDomainCollectListResponse,
    TechDomainCollectResponse,
    TriggerCollectTaskRequest,
    UpdateCollectSourcesRequest,
    YearOptionsResponse,
    get_current_year,
    get_year_options,
)
from app.schemas.common import SuccessResponse
from app.schemas.venue import VenueSubTaskListResponse, VenueSubTaskResponse
from app.services.collect_service import CollectService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/collect", tags=["Collect Configuration"])


# Helper to check admin role
def require_admin_user(current_user: dict = Depends(require_user)) -> dict:
    """Require admin or super_admin role."""
    if current_user.get("role") not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


# Background task runner


async def run_collect_task_background(task_id: int):
    """
    Fire-and-forget background task execution.
    Runs the collection task in-process using async/await.
    This avoids SQLite database locking issues with separate processes.
    """
    from app.core.database import AsyncSessionLocal
    from app.repositories.collect_repository import CollectTaskRepository

    # First, update task status to running immediately
    async with AsyncSessionLocal() as session:
        repo = CollectTaskRepository(session)
        task = await repo.get_by_id(task_id)
        if task and task.status == "pending":
            await repo.start_task_and_commit(task_id)
            logger.info(f"Task {task_id} status updated to running")

    try:
        await _run_unified_collect(task_id)
    except Exception as e:
        logger.error(f"Background task {task_id} failed: {e}")
        # Update task status to failed
        async with AsyncSessionLocal() as session:
            repo = CollectTaskRepository(session)
            task = await repo.get_by_id(task_id)
            if task and task.status == "running":
                await repo.fail_task_and_commit(task_id, str(e))
            logger.error(f"Task {task_id} marked as failed: {e}")


async def _run_unified_collect(task_id: int):
    """异步执行统一采集任务"""
    from app.core.database import AsyncSessionLocal
    from app.services.collect.orchestrator import CollectionOrchestrator
    from app.services.data_fetchers import AuthorFetcher, InstitutionFetcher, WorkFetcher

    async with AsyncSessionLocal() as session:
        # Initialize fetchers
        work_fetcher = WorkFetcher(session)
        author_fetcher = AuthorFetcher(session)
        institution_fetcher = InstitutionFetcher(session)

        # Use CollectionOrchestrator directly
        orchestrator = CollectionOrchestrator(
            session,
            work_fetcher=work_fetcher,
            author_fetcher=author_fetcher,
            institution_fetcher=institution_fetcher,
        )
        progress = await orchestrator.execute_task(task_id)

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


# ============ Tech Domain Collect Config Endpoints ============


@router.get(
    "/tech-domains",
    response_model=TechDomainCollectListResponse,
    summary="获取技术领域采集配置列表",
    description="获取所有技术领域及其关联的顶会顶刊配置",
)
async def list_tech_domains_collect(
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin_user),
):
    """List all tech domains with collect configuration."""
    repo = TechDomainCollectRepository(session)
    domains = await repo.list_with_collect_config()

    # Get venue bindings for all tech domains
    from app.repositories.venue_repository import VenueTechBindingRepository

    binding_repo = VenueTechBindingRepository(session)

    items = []
    for d in domains:
        # Get bindings from VenueTechBinding table
        bindings = await binding_repo.get_by_tech_domain(d.tech_domain_id, is_enabled=True)
        venue_count = len(bindings)

        # Build collect_sources from bindings (for backward compatibility)
        collect_sources = [
            {"id": b.venue.venue_code, "name": b.venue.venue_name, "type": b.venue.venue_type}
            for b in bindings
            if b.venue
        ]

        items.append(
            TechDomainCollectResponse(
                tech_domain_id=d.tech_domain_id,
                domain_code=d.domain_code,
                domain_name=d.domain_name,
                domain_name_en=d.domain_name_en,
                collect_sources=collect_sources,
                last_collect_at=d.last_collect_at,
                is_enabled=d.is_enabled,
                venue_count=venue_count,
            )
        )

    return TechDomainCollectListResponse(items=items, total=len(items))


@router.put(
    "/tech-domains/{tech_domain_id}/sources",
    response_model=TechDomainCollectResponse,
    summary="更新技术领域的采集源配置",
    description="[已废弃] 请使用 /venues/bindings API 管理绑定关系",
    deprecated=True,
)
async def update_tech_domain_sources(
    tech_domain_id: int,
    request: UpdateCollectSourcesRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin_user),
):
    """Update collect sources for a tech domain - DEPRECATED, use venue bindings API instead."""
    raise HTTPException(
        status_code=400,
        detail="This API is deprecated. Please use /venues/bindings API to manage venue-tech domain bindings.",
    )


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
    current_user: dict = Depends(require_admin_user),
):
    """List collect tasks."""
    repo = CollectTaskRepository(session)
    tasks, total = await repo.list_tasks(
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

            if datetime.utcnow() - t.time_window_end < timedelta(days=1):
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
    current_user: dict = Depends(require_admin_user),
):
    """Trigger a new collect task."""
    task_repo = CollectTaskRepository(session)
    domain_repo = TechDomainCollectRepository(session)

    # Validate tech domain exists
    domain = await domain_repo.get_by_id(request.tech_domain_id)
    if not domain:
        raise HTTPException(status_code=404, detail="Tech domain not found")

    # Check if has venue bindings configured
    from app.repositories.venue_repository import VenueTechBindingRepository

    binding_repo = VenueTechBindingRepository(session)
    bindings = await binding_repo.get_by_tech_domain(request.tech_domain_id, is_enabled=True)

    if not bindings:
        raise HTTPException(
            status_code=400,
            detail="Tech domain has no venue bindings configured. Please bind venues first.",
        )

    # Check if there's already a running task for this domain
    active_tasks = await task_repo.get_active_tasks()
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
        time_end = datetime.utcnow()  # 至今
    else:
        time_end = datetime(end_year, 12, 31, 23, 59, 59)

    # Create task with sub-tasks using service
    service = CollectService(session)
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


@router.get(
    "/tasks/{task_id}",
    response_model=CollectTaskResponse,
    summary="获取采集任务详情",
    description="获取指定采集任务的详细信息，包含执行日志",
)
async def get_task(
    task_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin_user),
):
    """Get collect task details."""
    repo = CollectTaskRepository(session)
    task = await repo.get_by_id(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # 从 time_window_start/end 提取年份
    start_year = task.time_window_start.year if task.time_window_start else DEFAULT_START_YEAR
    end_year = task.time_window_end.year if task.time_window_end else None
    # 如果 end_year 是当前年份且 time_window_end 接近当前时间，则显示为"至今"
    current_year = get_current_year()
    if end_year == current_year and task.time_window_end:
        from datetime import timedelta

        if datetime.utcnow() - task.time_window_end < timedelta(days=1):
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
    current_user: dict = Depends(require_admin_user),
):
    """Execute a pending task."""
    repo = CollectTaskRepository(session)
    task = await repo.get_by_id(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status != "pending":
        raise HTTPException(
            status_code=400, detail=f"Task is not in pending status (current: {task.status})"
        )

    # Check if there's already a running task
    active_tasks = await repo.get_active_tasks()
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
    "/tasks/{task_id}/cancel",
    response_model=SuccessResponse,
    summary="取消采集任务",
    description="取消正在执行的采集任务",
)
async def cancel_task(
    task_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin_user),
):
    """Cancel a running task."""
    repo = CollectTaskRepository(session)
    task = await repo.get_by_id(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status not in ["pending", "running"]:
        raise HTTPException(status_code=400, detail="Task cannot be cancelled")

    # Update task status via service
    service = CollectService(session)
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
    current_user: dict = Depends(require_admin_user),
):
    """Delete a completed task record."""
    repo = CollectTaskRepository(session)
    task = await repo.get_by_id(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status in ["pending", "running"]:
        raise HTTPException(status_code=400, detail="Cannot delete running or pending task")

    # Delete task via service
    service = CollectService(session)
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
    current_user: dict = Depends(require_admin_user),
):
    """Get all active tasks."""
    repo = CollectTaskRepository(session)
    tasks = await repo.get_active_tasks()

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


# ============ Options Endpoints ============


@router.get(
    "/options/task-statuses",
    response_model=list[dict[str, str]],
    summary="获取任务状态选项",
    description="获取所有可用的任务状态选项",
)
async def get_task_statuses():
    """Get task status options."""
    return TASK_STATUS_OPTIONS


@router.get(
    "/options/years",
    response_model=YearOptionsResponse,
    summary="获取年份选项",
    description="获取可用的年份选项列表",
)
async def get_years():
    """Get year options for time range selection."""
    return YearOptionsResponse(
        start_years=get_year_options(),
        min_year=MIN_START_YEAR,
        default_year=DEFAULT_START_YEAR,
        current_year=get_current_year(),
    )


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
    current_user: dict = Depends(require_admin_user),
):
    """Get venue sub-tasks for a task."""
    sub_task_repo = VenueSubTaskRepository(session)
    sub_tasks = await sub_task_repo.get_by_task(task_id)

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
    current_user: dict = Depends(require_admin_user),
):
    """Get detailed progress for a task."""
    from app.services.collect.orchestrator import CollectionOrchestrator
    from app.services.data_fetchers import AuthorFetcher, InstitutionFetcher, WorkFetcher

    # Initialize fetchers
    work_fetcher = WorkFetcher(session)
    author_fetcher = AuthorFetcher(session)
    institution_fetcher = InstitutionFetcher(session)

    orchestrator = CollectionOrchestrator(
        session,
        work_fetcher=work_fetcher,
        author_fetcher=author_fetcher,
        institution_fetcher=institution_fetcher,
    )
    return await orchestrator.get_task_progress(task_id)


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
    current_user: dict = Depends(require_admin_user),
):
    """Retry a failed venue sub-task."""
    sub_task_repo = VenueSubTaskRepository(session)
    sub_task = await sub_task_repo.get_by_id(sub_task_id)

    if not sub_task or sub_task.task_id != task_id:
        raise HTTPException(status_code=404, detail="Sub-task not found")

    if sub_task.status != "failed":
        raise HTTPException(status_code=400, detail="Only failed sub-tasks can be retried")

    # Reset status via service
    service = CollectService(session)
    await service.retry_sub_task(task_id, sub_task_id)

    # TODO: Trigger retry execution

    return SubTaskActionResponse(message="Sub-task reset for retry", sub_task_id=sub_task_id)
