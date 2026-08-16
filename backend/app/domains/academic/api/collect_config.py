"""
Tech domain collect configuration endpoint.
技术领域采集配置接口

Split from collect.py; routes keep the original /collect prefix.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.academic.schemas.collect import (
    TechDomainCollectListResponse,
    TechDomainCollectResponse,
)
from app.domains.academic.services.collect_service import CollectService
from app.domains.shared.api.auth import require_super_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/collect", tags=["Collect Configuration"])


# ============ Tech Domain Collect Config Endpoints ============


@router.get(
    "/tech-domains",
    response_model=TechDomainCollectListResponse,
    summary="获取技术领域采集配置列表",
    description="获取所有技术领域及其关联的顶会顶刊配置",
)
async def list_tech_domains_collect(
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_super_admin),
):
    """List all tech domains with collect configuration."""
    service = CollectService(session)
    items = await service.list_tech_domains_with_config()

    return TechDomainCollectListResponse(
        items=[TechDomainCollectResponse(**item) for item in items],
        total=len(items),
    )
