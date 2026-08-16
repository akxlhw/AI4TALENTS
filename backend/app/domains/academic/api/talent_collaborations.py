"""
Talent collaboration network endpoints.
人才合作网络接口

Split from talents.py; routes keep the original /talents prefix.

Architecture: Endpoint -> Service -> Repository
"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.academic.services.talent_service import TalentService
from app.domains.shared.schemas.common import (
    CountResponse,
    SyncStatusResponse,
    TaskStartResponse,
)

router = APIRouter(prefix="/talents", tags=["Talents"])


@router.post(
    "/collaborations/generate-sample",
    response_model=CountResponse,
    summary="生成示例合作数据",
    description="为测试目的生成随机合作数据",
)
async def generate_sample_collaborations(
    num_samples: int = Query(100, ge=10, le=1000, description="生成合作数量"),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Generate sample collaboration data for testing.
    """
    from app.domains.academic.services.collaboration_service import CollaborationService

    service = CollaborationService(session)
    try:
        count = await service.generate_sample_collaborations(num_samples)
        return CountResponse(message=f"已生成 {count} 条合作数据", count=count)
    finally:
        await service.close()


@router.get(
    "/{talent_id}/collaborations",
    response_model=dict,
    summary="获取合作网络",
    description="获取学者的合作关系数据",
)
async def get_talent_collaborations(
    talent_id: int,
    limit: int = Query(20, ge=1, le=50, description="返回合作者数量限制"),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get collaboration network for a talent.
    """
    from app.domains.academic.services.collaboration_service import CollaborationService

    talent_service = TalentService(session)

    # Verify talent exists
    if not await talent_service.talent_exists(talent_id):
        raise HTTPException(status_code=404, detail="Talent not found")

    # Get collaboration network
    collab_service = CollaborationService(session)
    try:
        network = await collab_service.get_collaboration_network(talent_id, limit)
        return network
    finally:
        await collab_service.close()


@router.post(
    "/collaborations/sync",
    response_model=TaskStartResponse,
    summary="同步合作网络数据",
    description="从已采集的论文数据中提取学者合作关系，无需重复调用 OpenAlex API",
)
async def sync_collaborations(
    background_tasks: BackgroundTasks,
    talent_id: int | None = Query(None, description="单个学者ID，为空则同步全部"),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Trigger collaboration data sync from local RawWork data.
    """
    from app.domains.academic.services.collaboration_service import (
        CollaborationService,
        _sync_progress,
    )

    if _sync_progress["status"] == "running":
        raise HTTPException(status_code=409, detail="同步任务正在进行中，请稍后再试")

    # Reset progress
    _sync_progress.update({"status": "pending", "processed": 0, "total": 0, "collaborations": 0})

    # Use FastAPI BackgroundTasks instead of manual threading
    # This keeps the task in the same event loop, avoiding "Future attached to a different loop" errors
    background_tasks.add_task(CollaborationService.run_background_sync, talent_id)

    return TaskStartResponse(
        message="同步任务已启动", talent_id=talent_id, sync_all=talent_id is None
    )


@router.get(
    "/collaborations/status",
    response_model=SyncStatusResponse,
    summary="获取同步状态",
    description="获取合作网络数据同步的进度状态",
)
async def get_sync_status(
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get collaboration sync status.
    """
    from app.domains.academic.services.collaboration_service import (
        CollaborationService,
        _sync_progress,
    )

    # Get current data status
    service = CollaborationService(session)
    try:
        data_status = await service.get_sync_status()
        return SyncStatusResponse(sync_progress=_sync_progress, data_status=data_status)
    finally:
        await service.close()
