"""
Collect configuration API endpoints - Simplified for MVP v1.1
采集配置相关接口 - 简化版

功能说明：
- 技术要素配置：管理技术要素关联的顶会顶刊
- 采集任务：基于技术要素触发采集，支持全量/增量模式
- 固定参数：数据类型（学者+论文+机构）、时间范围（2010.1.1至今）
- 新增：Venue级别的子任务追踪
"""
import logging
from typing import Optional, List
from datetime import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.repositories.collect_repository import CollectTaskRepository, TechElementCollectRepository
from app.repositories.venue_repository import VenueSubTaskRepository
from app.schemas.collect import (
    TechElementCollectResponse,
    TechElementCollectListResponse,
    UpdateCollectSourcesRequest,
    TriggerCollectTaskRequest,
    CollectTaskResponse,
    CollectTaskListResponse,
    TASK_STATUS_OPTIONS,
    COLLECT_MODE_OPTIONS,
)
from app.schemas.venue import VenueSubTaskResponse, VenueSubTaskListResponse
from app.api.v1.endpoints.auth import require_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/collect", tags=["Collect Configuration"])

# Helper to check admin role
def require_admin_user(current_user: dict = Depends(require_user)) -> dict:
    """Require admin or super_admin role."""
    if current_user.get("role") not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


# Background task runner
import asyncio
import subprocess
import sys
import os


def run_collect_task_in_subprocess(task_id: int):
    """
    Run collection task in a separate subprocess for maximum reliability.
    Uses a standalone script file to avoid Windows asyncio issues.
    """
    import sys
    import os

    # Get the backend directory
    current_file = os.path.abspath(__file__)
    endpoints_dir = os.path.dirname(current_file)
    v1_dir = os.path.dirname(endpoints_dir)
    api_dir = os.path.dirname(v1_dir)
    app_dir = os.path.dirname(api_dir)
    backend_dir = os.path.dirname(app_dir)

    print(f"[DEBUG] Backend dir: {backend_dir}")
    sys.stdout.flush()

    try:
        # Use the dedicated script file
        script_path = os.path.join(backend_dir, 'scripts', 'run_collect_task.py')

        print(f"[DEBUG] Running subprocess with script: {script_path}")
        sys.stdout.flush()

        # Run in subprocess with proper environment
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'

        result = subprocess.run(
            [sys.executable, script_path, str(task_id)],
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout
            cwd=backend_dir,
            env=env
        )

        print(f"[DEBUG] Subprocess returncode: {result.returncode}")
        print(f"[DEBUG] Subprocess stdout: {result.stdout[:1000] if result.stdout else 'empty'}")
        if result.stderr:
            print(f"[DEBUG] Subprocess stderr: {result.stderr[:500]}")
        sys.stdout.flush()

        if result.returncode != 0:
            error_msg = result.stderr[:500] if result.stderr else 'Unknown error'
            logger.error(f"Subprocess failed: {error_msg}")
            # Update task status using absolute path
            db_path = os.path.join(backend_dir, 'talent.db')
            import sqlite3
            from datetime import datetime
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE sync_collect_task SET status = ?, error_message = ?, completed_at = ?, current_step = ? WHERE task_id = ? AND status = ?',
                ('failed', error_msg, datetime.utcnow().isoformat(), '执行失败', task_id, 'running')
            )
            conn.commit()
            conn.close()
        else:
            logger.info(f"Subprocess completed: {result.stdout}")
    except Exception as e:
        print(f"[DEBUG] Exception in run_collect_task_in_subprocess: {e}")
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
        logger.error(f"Failed to run subprocess: {e}")


def start_background_task_in_thread(task_id: int):
    """Start background task in a separate thread for reliable execution."""
    import threading
    print(f"[DEBUG] start_background_task_in_thread called for task #{task_id}")
    sys.stdout.flush()
    thread = threading.Thread(target=run_collect_task_in_subprocess, args=(task_id,), daemon=False)
    thread.start()
    print(f"[DEBUG] Thread started: {thread.is_alive()}")
    sys.stdout.flush()
    logger.info(f"Started background thread for task #{task_id}")


async def run_collect_task_background(task_id: int):
    """
    Fire-and-forget background task execution.
    Runs the collection task in-process using async/await.
    This avoids SQLite database locking issues with separate processes.
    """
    try:
        await _run_unified_collect(task_id)
    except Exception as e:
        logger.error(f"Background task {task_id} failed: {e}")
        # Update task status to failed
        from app.core.database import AsyncSessionLocal
        from app.models.sync import CollectTask
        from datetime import datetime
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(CollectTask).where(CollectTask.task_id == task_id)
            )
            task = result.scalar_one_or_none()
            if task and task.status == "running":
                task.status = "failed"
                task.error_message = str(e)
                task.completed_at = datetime.utcnow()
                task.current_step = "执行失败"
                await session.commit()
            logger.error(f"Task {task_id} marked as failed: {e}")


async def _run_unified_collect(task_id: int):
    """异步执行统一采集任务"""
    from app.core.database import AsyncSessionLocal
    from app.services.collect.orchestrator import CollectionOrchestrator
    from app.services.data_fetchers import WorkFetcher, AuthorFetcher, InstitutionFetcher

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
            institution_fetcher=institution_fetcher
        )
        progress = await orchestrator.execute_task(task_id)

        if progress.status == "completed":
            print(f"\n[BACKGROUND] 任务 #{task_id} 完成!")
            print(f"[BACKGROUND] Works: {progress.total_works:,}")
            print(f"[BACKGROUND] Authors: {progress.total_authors:,}")
            print(f"[BACKGROUND] Normalized: {progress.normalized_authors:,}")
            print(f"[BACKGROUND] Synced to Talent: {progress.synced_authors:,}")
            print(f"[BACKGROUND]   - Created: {progress.created_talents:,}")
            print(f"[BACKGROUND]   - Updated: {progress.updated_talents:,}")
            print(f"[BACKGROUND] Tech Tags: {progress.created_tech_tags:,}")
        else:
            print(f"\n[BACKGROUND] 任务 #{task_id} 失败: {progress.errors}")


# ============ Tech Element Collect Config Endpoints ============

@router.get(
    "/tech-elements",
    response_model=TechElementCollectListResponse,
    summary="获取技术要素采集配置列表",
    description="获取所有技术要素及其关联的顶会顶刊配置"
)
async def list_tech_elements_collect(
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin_user),
):
    """List all tech elements with collect configuration."""
    repo = TechElementCollectRepository(session)
    elements = await repo.list_with_collect_config()

    # Get venue bindings for all tech elements
    from app.repositories.venue_repository import VenueTechBindingRepository
    binding_repo = VenueTechBindingRepository(session)

    items = []
    for e in elements:
        # Get bindings from VenueTechBinding table
        bindings = await binding_repo.get_by_tech_element(e.tech_element_id, is_enabled=True)
        venue_count = len(bindings)

        # Build collect_sources from bindings (for backward compatibility)
        collect_sources = [
            {"id": b.venue.venue_code, "name": b.venue.venue_name, "type": b.venue.venue_type}
            for b in bindings if b.venue
        ]

        items.append(TechElementCollectResponse(
            tech_element_id=e.tech_element_id,
            element_code=e.element_code,
            element_name=e.element_name,
            element_name_en=e.element_name_en,
            collect_sources=collect_sources,
            last_collect_at=e.last_collect_at,
            is_enabled=e.is_enabled,
            venue_count=venue_count,
        ))

    return TechElementCollectListResponse(items=items, total=len(items))


@router.put(
    "/tech-elements/{tech_element_id}/sources",
    response_model=TechElementCollectResponse,
    summary="更新技术要素的采集源配置",
    description="[已废弃] 请使用 /venues/bindings API 管理绑定关系",
    deprecated=True
)
async def update_tech_element_sources(
    tech_element_id: int,
    request: UpdateCollectSourcesRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin_user),
):
    """Update collect sources for a tech element - DEPRECATED, use venue bindings API instead."""
    raise HTTPException(
        status_code=400,
        detail="This API is deprecated. Please use /venues/bindings API to manage venue-tech element bindings."
    )


# ============ Collect Task Endpoints ============

@router.get(
    "/tasks",
    response_model=CollectTaskListResponse,
    summary="获取采集任务列表",
    description="获取采集任务列表（分页）"
)
async def list_tasks(
    status: Optional[str] = Query(None, description="按状态筛选"),
    tech_element_id: Optional[int] = Query(None, description="按技术要素筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin_user),
):
    """List collect tasks."""
    repo = CollectTaskRepository(session)
    tasks, total = await repo.list_tasks(
        status=status,
        tech_element_id=tech_element_id,
        page=page,
        page_size=page_size,
    )

    items = []
    for t in tasks:
        items.append(CollectTaskResponse(
            task_id=t.task_id,
            task_code=t.task_code,
            tech_element_id=t.tech_element_id,
            tech_element_name=t.tech_element.element_name if t.tech_element else None,
            collect_mode=t.collect_mode,
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
            created_at=t.created_at,
        ))

    return CollectTaskListResponse(items=items, total=total, page=page, page_size=page_size)


@router.post(
    "/tasks",
    response_model=CollectTaskResponse,
    summary="触发采集任务",
    description="""
触发采集任务。

**固定参数：**
- 数据类型：学者、论文、机构
- 时间范围：2010.1.1 至今

**可配置参数：**
- tech_element_id：技术要素ID
- collect_mode：full（全量）或 incremental（增量）

**说明：**
采集任务在后台异步执行，可通过任务列表查看进度。
"""
)
async def trigger_task(
    request: TriggerCollectTaskRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin_user),
):
    """Trigger a new collect task."""
    task_repo = CollectTaskRepository(session)
    element_repo = TechElementCollectRepository(session)

    # Validate tech element exists
    element = await element_repo.get_by_id(request.tech_element_id)
    if not element:
        raise HTTPException(status_code=404, detail="Tech element not found")

    # Check if has venue bindings configured
    from app.repositories.venue_repository import VenueTechBindingRepository
    binding_repo = VenueTechBindingRepository(session)
    bindings = await binding_repo.get_by_tech_element(request.tech_element_id, is_enabled=True)

    if not bindings:
        raise HTTPException(
            status_code=400,
            detail="Tech element has no venue bindings configured. Please bind venues first."
        )

    # Check if there's already a running task for this element
    active_tasks = await task_repo.get_active_tasks()
    for t in active_tasks:
        if t.tech_element_id == request.tech_element_id:
            raise HTTPException(
                status_code=400,
                detail=f"There is already a running task (#{t.task_id}) for this tech element."
            )

    # Determine time window BEFORE creating task
    from datetime import timedelta
    if request.collect_mode == "full":
        time_start = datetime(2015, 1, 1)
    else:
        # Incremental: look back 30 days, or use last_collect_at if available
        if element.last_collect_at:
            time_start = element.last_collect_at - timedelta(days=30)
        else:
            time_start = datetime.utcnow() - timedelta(days=30)
    time_end = datetime.utcnow()

    # Generate unique task code
    task_code = f"COLLECT-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"

    task = await task_repo.create_task(
        task_code=task_code,
        tech_element_id=request.tech_element_id,
        collect_mode=request.collect_mode,
        triggered_by=current_user.get("user_id"),
        time_window_start=time_start,
        time_window_end=time_end,
    )

    # Set initial status
    task.status = "pending"
    task.current_step = "等待执行"

    # Create VenueSubTask records for each venue binding
    from app.repositories.venue_repository import VenueTechBindingRepository, VenueSubTaskRepository
    from app.models.venue import VenueSubTask

    binding_repo = VenueTechBindingRepository(session)
    sub_task_repo = VenueSubTaskRepository(session)

    bindings = await binding_repo.get_by_tech_element(request.tech_element_id, is_enabled=True)

    for binding in bindings:
        sub_task = VenueSubTask(
            task_id=task.task_id,
            venue_id=binding.venue_id,
            status="pending",
            time_window_start=time_start,
            time_window_end=time_end,
        )
        await sub_task_repo.create(sub_task)

    await session.commit()

    logger.info(f"Created collect task {task.task_id} for {element.element_name} with {len(bindings)} venues")

    # Start background task using asyncio (in-process, works reliably on Windows)
    asyncio.create_task(run_collect_task_background(task.task_id))
    logger.info(f"Background task started for task #{task.task_id}")

    return CollectTaskResponse(
        task_id=task.task_id,
        task_code=task.task_code,
        tech_element_id=task.tech_element_id,
        tech_element_name=element.element_name,
        collect_mode=task.collect_mode,
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
        created_at=task.created_at,
    )


@router.get(
    "/tasks/{task_id}",
    response_model=CollectTaskResponse,
    summary="获取采集任务详情",
    description="获取指定采集任务的详细信息，包含执行日志"
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

    return CollectTaskResponse(
        task_id=task.task_id,
        task_code=task.task_code,
        tech_element_id=task.tech_element_id,
        tech_element_name=task.tech_element.element_name if task.tech_element else None,
        collect_mode=task.collect_mode,
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
        created_at=task.created_at,
    )


@router.post(
    "/tasks/{task_id}/execute",
    summary="执行采集任务",
    description="执行待执行状态的采集任务"
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
            status_code=400,
            detail=f"Task is not in pending status (current: {task.status})"
        )

    # Check if there's already a running task
    active_tasks = await repo.get_active_tasks()
    for t in active_tasks:
        if t.task_id != task_id and t.status == "running":
            raise HTTPException(
                status_code=400,
                detail=f"There is already a running task (#{t.task_id}). Please wait for it to complete."
            )

    # Start background execution
    asyncio.create_task(run_collect_task_background(task_id))
    logger.info(f"Background task started for task #{task_id}")

    return {
        "message": "Task execution started",
        "task_id": task_id,
        "status": "running"
    }


@router.post(
    "/tasks/{task_id}/cancel",
    summary="取消采集任务",
    description="取消正在执行的采集任务"
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

    task.status = "cancelled"
    task.completed_at = datetime.now()
    task.current_step = "已取消"

    await session.commit()
    return {"message": "Task cancelled"}


@router.delete(
    "/tasks/{task_id}",
    summary="删除采集任务",
    description="删除已完成的采集任务记录"
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

    # Delete related venue sub-tasks first
    from app.repositories.venue_repository import VenueSubTaskRepository
    sub_task_repo = VenueSubTaskRepository(session)
    sub_tasks = await sub_task_repo.get_by_task(task_id)
    for st in sub_tasks:
        await session.delete(st)

    # Delete the task
    await session.delete(task)
    await session.commit()

    return {"message": "Task deleted", "task_id": task_id}


@router.get(
    "/tasks/active",
    response_model=List[CollectTaskResponse],
    summary="获取活动任务",
    description="获取当前正在执行或待执行的任务"
)
async def get_active_tasks(
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin_user),
):
    """Get all active tasks."""
    repo = CollectTaskRepository(session)
    tasks = await repo.get_active_tasks()

    return [CollectTaskResponse(
        task_id=t.task_id,
        task_code=t.task_code,
        tech_element_id=t.tech_element_id,
        tech_element_name=t.tech_element.element_name if t.tech_element else None,
        collect_mode=t.collect_mode,
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
        created_at=t.created_at,
    ) for t in tasks]


# ============ Options Endpoints ============

@router.get(
    "/options/task-statuses",
    summary="获取任务状态选项",
    description="获取所有可用的任务状态选项"
)
async def get_task_statuses():
    """Get task status options."""
    return TASK_STATUS_OPTIONS


@router.get(
    "/options/collect-modes",
    summary="获取采集模式选项",
    description="获取所有可用的采集模式选项"
)
async def get_collect_modes():
    """Get collect mode options."""
    return COLLECT_MODE_OPTIONS


# ============ Venue Sub-Task Endpoints ============

@router.get(
    "/tasks/{task_id}/sub-tasks",
    response_model=VenueSubTaskListResponse,
    summary="获取任务的Venue子任务列表",
    description="获取指定任务下所有Venue级别的子任务"
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
        total=len(sub_tasks),
        items=[VenueSubTaskResponse.model_validate(st) for st in sub_tasks]
    )


@router.get(
    "/tasks/{task_id}/progress",
    summary="获取任务详细进度",
    description="获取任务的详细进度信息，包括各Venue子任务状态"
)
async def get_task_detailed_progress(
    task_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin_user),
):
    """Get detailed progress for a task."""
    from app.services.collect.orchestrator import CollectionOrchestrator
    from app.services.data_fetchers import WorkFetcher, AuthorFetcher, InstitutionFetcher

    # Initialize fetchers
    work_fetcher = WorkFetcher(session)
    author_fetcher = AuthorFetcher(session)
    institution_fetcher = InstitutionFetcher(session)

    orchestrator = CollectionOrchestrator(
        session,
        work_fetcher=work_fetcher,
        author_fetcher=author_fetcher,
        institution_fetcher=institution_fetcher
    )
    return await orchestrator.get_task_progress(task_id)


@router.post(
    "/tasks/{task_id}/sub-tasks/{sub_task_id}/retry",
    summary="重试失败的子任务",
    description="重新执行失败的Venue子任务"
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

    # Reset status
    await sub_task_repo.update_status(sub_task_id, "pending")

    # TODO: Trigger retry execution

    await session.commit()
    return {"message": "Sub-task reset for retry", "sub_task_id": sub_task_id}
