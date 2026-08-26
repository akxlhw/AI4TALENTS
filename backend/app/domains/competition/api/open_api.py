"""Open-API read endpoints for the competition domain (scope: competition:read)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.competition.services import open_api_provider  # noqa: F401  (search-registry side effect)
from app.domains.competition.services.comp_stats_service import CompStatsService
from app.domains.competition.services.comp_talent_service import CompTalentService
from app.domains.shared.api.open_api_auth import require_api_key
from app.domains.shared.api.open_api_helpers import read_jsonl_body
from app.domains.shared.services.audit_service import AuditService
from app.domains.shared.schemas.open_api import OpenApiPage

router = APIRouter(prefix="/open-api/competition", tags=["Open API — Competition"])

_require = require_api_key("competition:read")
_require_write = require_api_key("competition:write")


@router.get("/talents", summary="竞赛人才列表（关键词/国家/学校/评分筛选）")
async def list_competition_talents(
    keyword: str | None = Query(None),
    country_code: str | None = Query(None),
    school: str | None = Query(None),
    min_rating: int | None = Query(None, ge=0),
    rank_title: str | None = Query(None, description="如 candidate/master/etc."),
    sort_by: str = Query(
        "rating_desc", description="rating_desc/contests_desc/medals_desc/recent_desc"
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
    _principal: dict = Depends(_require),
) -> OpenApiPage:
    summaries, total = await CompTalentService(session).list_talents(
        keyword=keyword,
        country_code=country_code,
        school=school,
        min_rating=min_rating,
        rank_title=rank_title,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )
    items = [s.model_dump(mode="json") for s in summaries]
    return OpenApiPage(items=items, total=total, page=page, page_size=page_size)


@router.get("/talents/{talent_id}", summary="竞赛人才详情（含参赛史）")
async def get_competition_talent(
    talent_id: int,
    session: AsyncSession = Depends(get_async_session),
    _principal: dict = Depends(_require),
) -> dict:
    detail = await CompTalentService(session).get_detail(talent_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Talent not found")
    return detail.model_dump(mode="json")


@router.get("/stats", summary="竞赛域统计")
async def competition_stats(
    session: AsyncSession = Depends(get_async_session),
    _principal: dict = Depends(_require),
) -> dict:
    overview = await CompStatsService(session).get_overview()
    return overview.model_dump(mode="json")


@router.post("/import", summary="竞赛人才 JSONL 导入（scope: competition:write）")
async def open_api_competition_import(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    principal: dict = Depends(_require_write),
) -> dict:
    """Single-contest full-replace import (schema v1.0 JSONL)."""
    from app.domains.competition.services.comp_import_service import (
        CompImportError,
        CompImportService,
    )

    content, err = await read_jsonl_body(request)
    if err:
        raise HTTPException(status_code=400, detail=err)
    try:
        report = await CompImportService(session).import_jsonl(content)
    except CompImportError as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from None
    await session.commit()
    await AuditService.log_data_operation(
        user_id=None,
        operation="import",
        resource_type="competition_talent",
        resource_id=report.contest_external_id,
        status="success",
        detail={"principal": principal["key_name"]},
        event_subtype="import",
    )
    return report.model_dump(mode="json")
