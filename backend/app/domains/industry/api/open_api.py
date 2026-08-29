"""Open-API read endpoints for the industry domain (scope: industry:read)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.exceptions import NotFoundError
from app.domains.industry.services.industry_import_service import IndustryImportService
from app.domains.industry.services.industry_position_service import IndustryPositionService
from app.domains.industry.services.industry_talent_service import IndustryTalentService
from app.domains.industry.services.open_api_provider import IndustrySearchProvider
from app.domains.shared.api.open_api_auth import require_api_key
from app.domains.shared.api.open_api_helpers import read_jsonl_body
from app.domains.shared.schemas.open_api import OpenApiPage
from app.domains.shared.services.audit_service import AuditService
from app.domains.shared.services.open_api.registry import register_search_provider

router = APIRouter(prefix="/open-api/industry", tags=["Open API — Industry"])

_require = require_api_key("industry:read")
_require_write = require_api_key("industry:write")

# Explicit registration (a real call survives lint; bare side-effect imports do not)
register_search_provider("industry", IndustrySearchProvider)


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
    items = [s.model_dump(mode="json") for s in summaries]
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
    return detail.model_dump(mode="json")


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


@router.post("/import", summary="行业人才 JSONL 导入（scope: industry:write）")
async def open_api_industry_import(
    request: Request,
    position_id: int = Query(..., description="目标岗位 ID"),
    batch: str | None = Query(None, description="导入批次标识"),
    session: AsyncSession = Depends(get_async_session),
    principal: dict = Depends(_require_write),
) -> dict:
    """Push channel parity with POST /industry/import (incremental upsert)."""
    content, err = await read_jsonl_body(request)
    if err:
        raise HTTPException(status_code=400, detail=err)
    report = await IndustryImportService(session).import_jsonl(
        content, position_id=position_id, batch=batch
    )
    await session.commit()
    await AuditService.log_data_operation(
        user_id=None,
        operation="import",
        resource_type="industry_talent",
        resource_id=str(position_id),
        status="success" if not report.aborted else "failure",
        detail={"principal": principal["key_name"], "batch": batch},
        event_subtype="import",
    )
    return report.model_dump(mode="json")
