"""Open-API read endpoints for the open-source domain (scope: open_source:read)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.exceptions import NotFoundError
from app.domains.open_source.services.os_developer_service import OSDeveloperService
from app.domains.shared.api.open_api_auth import require_api_key
from app.domains.shared.schemas.open_api import OpenApiPage

router = APIRouter(prefix="/open-api/open-source", tags=["Open API — Open Source"])

_require = require_api_key("open_source:read")

# PII redaction for external consumers
_PII_FIELDS = ("email", "social_links", "blog_url")


def _redact(record: dict) -> dict:
    return {k: v for k, v in record.items() if k not in _PII_FIELDS}


def _orm_to_dict(d: Any) -> dict:
    return {
        "developer_id": d.developer_id,
        "github_login": d.github_login,
        "name": d.name,
        "bio": d.bio,
        "location": d.location,
        "company": d.company,
        "avatar_url": d.avatar_url,
        "followers_count": d.followers_count,
        "public_repos_count": d.public_repos_count,
        "total_stars_received": d.total_stars_received,
        "primary_languages": d.primary_languages,
        "tech_tags": d.tech_tags,
        "is_student": d.is_student,
    }


@router.get("/talents", summary="开源人才列表（技术要素/语言/地区筛选）")
async def list_open_source_talents(
    keyword: str | None = Query(None, description="关键词（姓名/简介/公司/地区）"),
    tech_elements: list[str] | None = Query(None, description="技术要素，任一命中"),
    languages: list[str] | None = Query(None),
    location: str | None = Query(None),
    min_stars: int | None = Query(None, ge=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
    _principal: dict = Depends(_require),
) -> OpenApiPage:
    developers, total = await OSDeveloperService(session).list_developers(
        q=keyword or "",
        tech_elements=tech_elements,
        languages=languages,
        location=location,
        min_stars=min_stars,
        page=page,
        page_size=page_size,
    )
    items = [_orm_to_dict(d) for d in developers]
    return OpenApiPage(items=items, total=total, page=page, page_size=page_size)


@router.get("/talents/{developer_id}", summary="开源人才详情")
async def get_open_source_talent(
    developer_id: int,
    session: AsyncSession = Depends(get_async_session),
    _principal: dict = Depends(_require),
) -> dict:
    try:
        detail = await OSDeveloperService(session).get_developer_detail(developer_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Developer not found") from None
    return _redact(detail.model_dump(mode="json"))


@router.get("/stats", summary="开源域统计")
async def open_source_stats(
    session: AsyncSession = Depends(get_async_session),
    _principal: dict = Depends(_require),
) -> dict:
    stats = await OSDeveloperService(session).get_stats()
    return stats.model_dump(mode="json")
