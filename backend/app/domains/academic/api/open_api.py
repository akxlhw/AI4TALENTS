"""Open-API read endpoints for the academic domain (scope: academic:read)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.academic.services import open_api_provider  # noqa: F401  (search-registry side effect)
from app.domains.academic.services.talent_service import TalentService
from app.domains.shared.api.open_api_auth import require_api_key
from app.domains.shared.schemas.open_api import OpenApiPage

router = APIRouter(prefix="/open-api/academic", tags=["Open API — Academic"])

_require = require_api_key("academic:read")

# External-facing field whitelist (PII redaction: orcid / extra_data excluded)
_LIST_FIELDS = (
    "talent_id",
    "name",
    "name_en",
    "current_title",
    "role_type",
    "school_id",
    "works_count",
    "cited_by_count",
    "h_index",
    "topic_tags",
)


def _strip(talents: list) -> list[dict]:
    items = []
    for t in talents:
        items.append({f: getattr(t, f) for f in _LIST_FIELDS if getattr(t, f, None) is not None})
    return items


@router.get("/talents", summary="学术人才列表（关键词/角色/引用数筛选）")
async def list_academic_talents(
    keyword: str | None = Query(None, description="姓名/关键词"),
    role_type: str | None = Query(None),
    min_citations: int | None = Query(None, ge=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
    _principal: dict = Depends(_require),
) -> OpenApiPage:
    service = TalentService(session)
    if keyword:
        talents, total = await service.search_talents_basic(
            keyword, page=page, page_size=page_size, role_type=role_type
        )
    else:
        talents, total = await service.get_talent_list(
            role_type=role_type, min_citations=min_citations, page=page, page_size=page_size
        )
    return OpenApiPage(items=_strip(talents), total=total, page=page, page_size=page_size)


@router.get("/talents/{talent_id}", summary="学术人才详情")
async def get_academic_talent(
    talent_id: int,
    session: AsyncSession = Depends(get_async_session),
    _principal: dict = Depends(_require),
) -> dict:
    talent = await TalentService(session).get_talent_by_id(talent_id)
    if not talent:
        raise HTTPException(status_code=404, detail="Talent not found")
    return _strip([talent])[0]


@router.get("/stats", summary="学术域统计")
async def academic_stats(
    session: AsyncSession = Depends(get_async_session),
    _principal: dict = Depends(_require),
) -> dict:
    return await TalentService(session).get_statistics()
