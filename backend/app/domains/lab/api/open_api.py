"""Open-API read endpoints for the lab domain (scope: lab:read)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.lab.services import open_api_provider  # noqa: F401  (search-registry side effect)
from app.core.exceptions import NotFoundError
from app.domains.lab.services.lab_stats_service import LabStatsService
from app.domains.lab.services.lab_talent_service import LabTalentService
from app.domains.shared.api.open_api_auth import require_api_key
from app.domains.shared.schemas.open_api import OpenApiPage

router = APIRouter(prefix="/open-api/lab", tags=["Open API — Lab"])

_require = require_api_key("lab:read")

# PII redaction for external consumers
_PII_FIELDS = ("email", "social_links")


def _redact(data: dict) -> dict:
    return {k: v for k, v in data.items() if k not in _PII_FIELDS}


@router.get("/talents", summary="实验室人才列表（实验室/研究方向/角色筛选）")
async def list_lab_talents(
    keyword: str | None = Query(None),
    parent_lab: str | None = Query(None, description="所属实验室"),
    lab_name: str | None = Query(None, description="子实验室"),
    role_type: str | None = Query(None),
    research_area: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
    _principal: dict = Depends(_require),
) -> OpenApiPage:
    summaries, total = await LabTalentService(session).list_talents(
        keyword=keyword,
        parent_lab=parent_lab,
        lab_name=lab_name,
        role_type=role_type,
        research_area=research_area,
        page=page,
        page_size=page_size,
    )
    items = [_redact(s.model_dump(mode="json")) for s in summaries]
    return OpenApiPage(items=items, total=total, page=page, page_size=page_size)


@router.get("/talents/{talent_id}", summary="实验室人才详情")
async def get_lab_talent(
    talent_id: int,
    session: AsyncSession = Depends(get_async_session),
    _principal: dict = Depends(_require),
) -> dict:
    try:
        detail = await LabTalentService(session).get_talent_detail(talent_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Talent not found") from None
    return _redact(detail.model_dump(mode="json"))


@router.get("/stats", summary="实验室域统计")
async def lab_stats(
    session: AsyncSession = Depends(get_async_session),
    _principal: dict = Depends(_require),
) -> dict:
    stats = await LabStatsService(session).get_stats()
    return stats.model_dump(mode="json")
