"""Open-API read endpoints for the industry domain (scope: industry:read)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.industry.services import open_api_provider  # noqa: F401  (search-registry side effect)
from app.core.exceptions import NotFoundError
from app.domains.industry.services.industry_position_service import IndustryPositionService
from app.domains.industry.services.industry_talent_service import IndustryTalentService
from app.domains.shared.api.open_api_auth import require_api_key
from app.domains.shared.schemas.open_api import OpenApiPage

router = APIRouter(prefix="/open-api/industry", tags=["Open API — Industry"])

_require = require_api_key("industry:read")

# PII redaction for external consumers (contact links)
_PII_FIELDS = ("profile_url",)


def _redact(data: dict) -> dict:
    return {k: v for k, v in data.items() if k not in _PII_FIELDS}


@router.get("/talents", summary="行业人才列表（岗位/状态/匹配分筛选）")
async def list_industry_talents(
    keyword: str | None = Query(None),
    position_id: int | None = Query(None),
    min_score: float | None = Query(None, ge=0, le=100),
    status: str | None = Query(None, description="new/connected/terminated"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
    _principal: dict = Depends(_require),
) -> OpenApiPage:
    summaries, total = await IndustryTalentService(session).list_talents(
        keyword=keyword,
        position_id=position_id,
        min_score=min_score,
        status=status,
        page=page,
        page_size=page_size,
    )
    items = [_redact(s.model_dump(mode="json")) for s in summaries]
    return OpenApiPage(items=items, total=total, page=page, page_size=page_size)


@router.get("/talents/{talent_id}", summary="行业人才详情（含岗位匹配）")
async def get_industry_talent(
    talent_id: int,
    session: AsyncSession = Depends(get_async_session),
    _principal: dict = Depends(_require),
) -> dict:
    try:
        detail = await IndustryTalentService(session).get_talent_detail(talent_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Talent not found") from None
    return _redact(detail.model_dump(mode="json"))


@router.get("/stats", summary="行业域统计（岗位粒度）")
async def industry_stats(
    session: AsyncSession = Depends(get_async_session),
    _principal: dict = Depends(_require),
) -> dict:
    positions = await IndustryPositionService(session).list_positions()
    return {
        "total_positions": len(positions),
        "positions": [
            {
                "position_id": p.position_id,
                "title": p.title,
                "status": p.status,
                "candidate_count": p.candidate_count,
                "avg_match_score": p.avg_match_score,
            }
            for p in positions
        ],
    }
