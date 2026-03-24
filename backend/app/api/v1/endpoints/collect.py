"""
Collect configuration API endpoints.
采集配置相关接口
"""
from typing import Optional, List
from datetime import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.iam import UserAccount
from app.repositories.collect_repository import (
    CollectScopeRepository,
    CollectStrategyRepository,
    CollectTaskRepository,
)
from app.schemas.collect import (
    CreateScopeRequest,
    UpdateScopeRequest,
    CollectScopeResponse,
    ScopeListResponse,
    CreateStrategyRequest,
    UpdateStrategyRequest,
    CollectStrategyResponse,
    StrategyListResponse,
    CreateTaskRequest,
    CollectTaskResponse,
    TaskListResponse,
    SCOPE_TYPE_OPTIONS,
    STRATEGY_TYPE_OPTIONS,
    TASK_STATUS_OPTIONS,
    DATA_TYPE_OPTIONS,
)
from app.api.v1.endpoints.auth import require_user, require_admin

router = APIRouter(prefix="/collect", tags=["Collect Configuration"])


# ============ Scope Endpoints ============

@router.get(
    "/scopes",
    response_model=ScopeListResponse,
    summary="获取采集范围列表",
    description="获取所有采集范围配置"
)
async def list_scopes(
    scope_type: Optional[str] = Query(None, description="按类型筛选"),
    is_enabled: Optional[bool] = Query(None, description="按状态筛选"),
    session: AsyncSession = Depends(get_async_session),
    current_user: UserAccount = Depends(require_admin),
):
    """List all collect scopes."""
    repo = CollectScopeRepository(session)
    scopes = await repo.list_scopes(scope_type=scope_type, is_enabled=is_enabled)

    items = [CollectScopeResponse.model_validate(s) for s in scopes]
    return ScopeListResponse(items=items, total=len(items))


@router.post(
    "/scopes",
    response_model=CollectScopeResponse,
    summary="创建采集范围",
    description="创建新的采集范围配置"
)
async def create_scope(
    request: CreateScopeRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: UserAccount = Depends(require_admin),
):
    """Create a new collect scope."""
    repo = CollectScopeRepository(session)

    # Check if code exists
    existing = await repo.get_by_code(request.scope_code)
    if existing:
        raise HTTPException(status_code=400, detail="Scope code already exists")

    scope = await repo.create_scope(
        scope_code=request.scope_code,
        scope_name=request.scope_name,
        scope_type=request.scope_type,
        scope_value=request.scope_value,
        description=request.description,
        created_by=current_user.user_id,
    )
    await session.commit()

    return CollectScopeResponse.model_validate(scope)


@router.get(
    "/scopes/{scope_id}",
    response_model=CollectScopeResponse,
    summary="获取采集范围详情",
    description="获取指定采集范围的详细信息"
)
async def get_scope(
    scope_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: UserAccount = Depends(require_admin),
):
    """Get collect scope details."""
    repo = CollectScopeRepository(session)
    scope = await repo.get_by_id(scope_id)

    if not scope:
        raise HTTPException(status_code=404, detail="Scope not found")

    return CollectScopeResponse.model_validate(scope)


@router.put(
    "/scopes/{scope_id}",
    response_model=CollectScopeResponse,
    summary="更新采集范围",
    description="更新采集范围配置"
)
async def update_scope(
    scope_id: int,
    request: UpdateScopeRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: UserAccount = Depends(require_admin),
):
    """Update collect scope."""
    repo = CollectScopeRepository(session)
    scope = await repo.update_scope(
        scope_id,
        scope_name=request.scope_name,
        scope_value=request.scope_value,
        is_enabled=request.is_enabled,
        description=request.description,
    )

    if not scope:
        raise HTTPException(status_code=404, detail="Scope not found")

    await session.commit()
    return CollectScopeResponse.model_validate(scope)


@router.delete(
    "/scopes/{scope_id}",
    summary="删除采集范围",
    description="删除采集范围配置"
)
async def delete_scope(
    scope_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: UserAccount = Depends(require_admin),
):
    """Delete collect scope."""
    repo = CollectScopeRepository(session)
    success = await repo.delete_scope(scope_id)

    if not success:
        raise HTTPException(status_code=404, detail="Scope not found")

    await session.commit()
    return {"message": "Scope deleted"}


# ============ Strategy Endpoints ============

@router.get(
    "/strategies",
    response_model=StrategyListResponse,
    summary="获取采集策略列表",
    description="获取所有采集策略配置"
)
async def list_strategies(
    strategy_type: Optional[str] = Query(None, description="按类型筛选"),
    is_enabled: Optional[bool] = Query(None, description="按状态筛选"),
    session: AsyncSession = Depends(get_async_session),
    current_user: UserAccount = Depends(require_admin),
):
    """List all collect strategies."""
    repo = CollectStrategyRepository(session)
    strategies = await repo.list_strategies(strategy_type=strategy_type, is_enabled=is_enabled)

    items = [CollectStrategyResponse.model_validate(s) for s in strategies]
    return StrategyListResponse(items=items, total=len(items))


@router.post(
    "/strategies",
    response_model=CollectStrategyResponse,
    summary="创建采集策略",
    description="创建新的采集策略配置"
)
async def create_strategy(
    request: CreateStrategyRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: UserAccount = Depends(require_admin),
):
    """Create a new collect strategy."""
    repo = CollectStrategyRepository(session)

    # Check if code exists
    existing = await repo.get_by_code(request.strategy_code)
    if existing:
        raise HTTPException(status_code=400, detail="Strategy code already exists")

    strategy = await repo.create_strategy(
        strategy_code=request.strategy_code,
        strategy_name=request.strategy_name,
        strategy_type=request.strategy_type,
        data_types=request.data_types,
        scope_ids=request.scope_ids,
        schedule_cron=request.schedule_cron,
        fetch_config=request.fetch_config,
        description=request.description,
        created_by=current_user.user_id,
    )
    await session.commit()

    return CollectStrategyResponse.model_validate(strategy)


@router.get(
    "/strategies/{strategy_id}",
    response_model=CollectStrategyResponse,
    summary="获取采集策略详情",
    description="获取指定采集策略的详细信息"
)
async def get_strategy(
    strategy_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: UserAccount = Depends(require_admin),
):
    """Get collect strategy details."""
    repo = CollectStrategyRepository(session)
    strategy = await repo.get_by_id(strategy_id)

    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    return CollectStrategyResponse.model_validate(strategy)


@router.put(
    "/strategies/{strategy_id}",
    response_model=CollectStrategyResponse,
    summary="更新采集策略",
    description="更新采集策略配置"
)
async def update_strategy(
    strategy_id: int,
    request: UpdateStrategyRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: UserAccount = Depends(require_admin),
):
    """Update collect strategy."""
    repo = CollectStrategyRepository(session)
    strategy = await repo.update_strategy(
        strategy_id,
        strategy_name=request.strategy_name,
        scope_ids=request.scope_ids,
        data_types=request.data_types,
        schedule_cron=request.schedule_cron,
        fetch_config=request.fetch_config,
        is_enabled=request.is_enabled,
        description=request.description,
    )

    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    await session.commit()
    return CollectStrategyResponse.model_validate(strategy)


@router.delete(
    "/strategies/{strategy_id}",
    summary="删除采集策略",
    description="删除采集策略配置"
)
async def delete_strategy(
    strategy_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: UserAccount = Depends(require_admin),
):
    """Delete collect strategy."""
    repo = CollectStrategyRepository(session)
    success = await repo.delete_strategy(strategy_id)

    if not success:
        raise HTTPException(status_code=404, detail="Strategy not found")

    await session.commit()
    return {"message": "Strategy deleted"}


# ============ Task Endpoints ============

@router.get(
    "/tasks",
    response_model=TaskListResponse,
    summary="获取采集任务列表",
    description="获取采集任务列表（分页）"
)
async def list_tasks(
    status: Optional[str] = Query(None, description="按状态筛选"),
    strategy_id: Optional[int] = Query(None, description="按策略筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
    current_user: UserAccount = Depends(require_admin),
):
    """List collect tasks."""
    repo = CollectTaskRepository(session)
    tasks, total = await repo.list_tasks(
        status=status,
        strategy_id=strategy_id,
        page=page,
        page_size=page_size,
    )

    items = [CollectTaskResponse.model_validate(t) for t in tasks]
    return TaskListResponse(items=items, total=total, page=page, page_size=page_size)


@router.post(
    "/tasks",
    response_model=CollectTaskResponse,
    summary="触发采集任务",
    description="手动触发采集任务"
)
async def trigger_task(
    request: CreateTaskRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: UserAccount = Depends(require_admin),
):
    """Trigger a new collect task."""
    task_repo = CollectTaskRepository(session)
    strategy_repo = CollectStrategyRepository(session)

    # If strategy_id provided, validate it exists
    if request.strategy_id:
        strategy = await strategy_repo.get_by_id(request.strategy_id)
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

    # Generate unique task code
    task_code = f"TASK-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

    task = await task_repo.create_task(
        task_code=task_code,
        task_type=request.task_type,
        strategy_id=request.strategy_id,
        triggered_by=current_user.user_id,
    )

    # Start task execution (async background task would be ideal here)
    # For now, we just create the task record
    task.status = "running"
    task.started_at = datetime.now()

    await session.commit()
    return CollectTaskResponse.model_validate(task)


@router.get(
    "/tasks/{task_id}",
    response_model=CollectTaskResponse,
    summary="获取采集任务详情",
    description="获取指定采集任务的详细信息"
)
async def get_task(
    task_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: UserAccount = Depends(require_admin),
):
    """Get collect task details."""
    repo = CollectTaskRepository(session)
    task = await repo.get_by_id(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return CollectTaskResponse.model_validate(task)


@router.post(
    "/tasks/{task_id}/cancel",
    summary="取消采集任务",
    description="取消正在执行的采集任务"
)
async def cancel_task(
    task_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: UserAccount = Depends(require_admin),
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

    await session.commit()
    return {"message": "Task cancelled"}


@router.get(
    "/tasks/active",
    response_model=List[CollectTaskResponse],
    summary="获取活动任务",
    description="获取当前正在执行或待执行的任务"
)
async def get_active_tasks(
    session: AsyncSession = Depends(get_async_session),
    current_user: UserAccount = Depends(require_admin),
):
    """Get all active tasks."""
    repo = CollectTaskRepository(session)
    tasks = await repo.get_active_tasks()

    return [CollectTaskResponse.model_validate(t) for t in tasks]


# ============ Options Endpoints ============

@router.get(
    "/options/scope-types",
    summary="获取范围类型选项",
    description="获取所有可用的范围类型选项"
)
async def get_scope_types():
    """Get scope type options."""
    return SCOPE_TYPE_OPTIONS


@router.get(
    "/options/strategy-types",
    summary="获取策略类型选项",
    description="获取所有可用的策略类型选项"
)
async def get_strategy_types():
    """Get strategy type options."""
    return STRATEGY_TYPE_OPTIONS


@router.get(
    "/options/task-statuses",
    summary="获取任务状态选项",
    description="获取所有可用的任务状态选项"
)
async def get_task_statuses():
    """Get task status options."""
    return TASK_STATUS_OPTIONS


@router.get(
    "/options/data-types",
    summary="获取数据类型选项",
    description="获取所有可用的数据类型选项"
)
async def get_data_types():
    """Get data type options."""
    return DATA_TYPE_OPTIONS
