"""
Open Source — Collection endpoints (repo-triggered + task management).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.open_source.api.auth import require_admin
from app.domains.open_source.schemas.open_source import (
    OSBatchCollectRequest,
    OSBatchCollectResponse,
    OSBatchCollectSkippedItem,
    OSCollectTaskCreate,
    OSCollectTaskResponse,
)
from app.domains.open_source.services.background_state import cancelled_task_ids
from app.domains.open_source.services.open_source_service import OpenSourceService
from app.domains.shared.schemas.common import PaginatedResponse, SuccessResponse

router = APIRouter(prefix="/open-source", tags=["Open Source Talent"])


# ============= Repo Collection =============


@router.post("/repo-configs/{repo_config_id}/collect", response_model=OSCollectTaskResponse)
async def collect_single_repo(
    repo_config_id: int,
    contributors_per_repo: int = Query(0, ge=0, le=2000),
    session: AsyncSession = Depends(get_async_session),
    user: dict = Depends(require_admin),
):
    """Start a background collection task for a single repository."""
    service = OpenSourceService(session)
    try:
        task, repo_full_name, tech_element = await service.collect_single_repo(
            repo_config_id=repo_config_id,
            contributors_per_repo=contributors_per_repo,
            created_by=int(user.get("sub", 0)),
        )
    except ValueError as e:
        status_code = 404 if "not found" in str(e).lower() else 400 if "disabled" in str(e).lower() else 409
        raise HTTPException(status_code=status_code, detail=str(e)) from e

    # Start background collection
    asyncio.create_task(
        service.run_repo_collection_background(
            task_id=task.task_id,
            repo_config_id=repo_config_id,
            repo_full_name=repo_full_name,
            tech_element=tech_element,
            contributors_per_repo=contributors_per_repo,
        )
    )
    return OSCollectTaskResponse.model_validate(task)


@router.post("/repo-configs/collect-batch", response_model=OSBatchCollectResponse)
async def collect_batch_repos(
    data: OSBatchCollectRequest,
    session: AsyncSession = Depends(get_async_session),
    user: dict = Depends(require_admin),
):
    """Start background collection tasks for multiple repositories."""
    service = OpenSourceService(session)
    created_tasks, skipped = await service.collect_batch_repos(
        repo_config_ids=data.repo_config_ids,
        contributors_per_repo=data.contributors_per_repo,
        created_by=int(user.get("sub", 0)),
    )

    # Start background collection for each created task
    for task in created_tasks:
        config_json = task.config_json or {}
        asyncio.create_task(
            service.run_repo_collection_background(
                task_id=task.task_id,
                repo_config_id=config_json.get("repo_config_id", 0),
                repo_full_name=config_json.get("repo_full_name", ""),
                tech_element=config_json.get("tech_element", ""),
                contributors_per_repo=config_json.get("contributors_per_repo", 0),
            )
        )

    return OSBatchCollectResponse(
        created=[OSCollectTaskResponse.model_validate(t) for t in created_tasks],
        skipped=[
            OSBatchCollectSkippedItem(
                repo_config_id=s["repo_config_id"],
                repo_full_name=s["repo_full_name"],
                reason=s["reason"],
            )
            for s in skipped
        ],
    )


# ============= Collect Tasks =============


@router.get("/collect/tasks", response_model=PaginatedResponse[OSCollectTaskResponse])
async def list_collect_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
    _user: dict = Depends(require_admin),
):
    service = OpenSourceService(session)
    items, total = await service.list_collect_tasks(page=page, page_size=page_size)
    return PaginatedResponse.create(
        items=[OSCollectTaskResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/collect/tasks", response_model=OSCollectTaskResponse, status_code=201)
async def create_collect_task(
    data: OSCollectTaskCreate,
    session: AsyncSession = Depends(get_async_session),
    user: dict = Depends(require_admin),
):
    task_name = data.task_name or f"Collection_{datetime.now(timezone.utc).replace(tzinfo=None).strftime('%Y%m%d_%H%M%S')}"
    config_json = data.model_dump(exclude_unset=True)
    service = OpenSourceService(session)
    task = await service.create_collect_task(
        task_name=task_name,
        config_json=config_json,
        created_by=int(user.get("sub", 0)),
    )
    return OSCollectTaskResponse.model_validate(task)


@router.get("/collect/tasks/{task_id}", response_model=OSCollectTaskResponse)
async def get_collect_task(
    task_id: int,
    session: AsyncSession = Depends(get_async_session),
    _user: dict = Depends(require_admin),
):
    service = OpenSourceService(session)
    task = await service.get_collect_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return OSCollectTaskResponse.model_validate(task)


@router.post("/collect/tasks/{task_id}/cancel")
async def cancel_collect_task(
    task_id: int,
    session: AsyncSession = Depends(get_async_session),
    _user: dict = Depends(require_admin),
):
    service = OpenSourceService(session)
    try:
        task = await service.cancel_collect_task(task_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    cancelled_task_ids.add(task_id)
    return SuccessResponse(message="Task cancelled")


@router.delete("/collect/tasks/{task_id}")
async def delete_collect_task(
    task_id: int,
    session: AsyncSession = Depends(get_async_session),
    _user: dict = Depends(require_admin),
):
    service = OpenSourceService(session)
    try:
        success = await service.delete_collect_task(task_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return SuccessResponse(message="Task deleted")
