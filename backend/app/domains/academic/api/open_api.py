"""Open-API read endpoints for the academic domain (scope: academic:read)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.academic.services.open_api_provider import AcademicSearchProvider
from app.domains.academic.services.talent_service import TalentService
from app.domains.shared.api.open_api_auth import require_api_key
from app.domains.shared.schemas.open_api import OpenApiPage
from app.domains.shared.services.open_api.registry import register_search_provider

router = APIRouter(prefix="/open-api/academic", tags=["Open API — Academic"])

_require = require_api_key("academic:read")

# Explicit registration (a real call survives lint; bare side-effect imports do not)
register_search_provider("academic", AcademicSearchProvider)

# External-facing field whitelist (extra_data excluded as internal raw payload;
# PII such as orcid is exposed — Open API is behind API-Key auth)
_LIST_FIELDS = (
    "talent_id",
    "name",
    "name_en",
    "orcid",
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
    service = TalentService(session)
    talent = await service.get_talent_by_id(talent_id)
    if not talent:
        raise HTTPException(status_code=404, detail="Talent not found")

    works = await service.get_selected_works(talent_id, limit=10)
    tech_tag_rows = await service.get_talent_tech_tags(talent_id)
    return {
        "talent_id": talent.talent_id,
        "name": talent.name,
        "name_en": talent.name_en,
        "orcid": talent.orcid,
        "current_title": talent.current_title,
        "role_type": talent.role_type,
        "role_confidence": talent.role_confidence,
        "school_id": talent.primary_school_id,
        "school_name": talent.primary_school_name,
        "education_school_name": (
            talent.education_school.school_name if talent.education_school else None
        ),
        "company_school_name": (
            talent.company_school.school_name if talent.company_school else None
        ),
        "works_count": talent.works_count,
        "cited_by_count": talent.cited_by_count,
        "h_index": talent.h_index,
        "latest_active_year": talent.latest_active_year,
        "topic_tags": talent.topic_tags or [],
        "openalex_topics": talent.openalex_topics or [],
        "summary": talent.summary,
        "department_name": talent.department_name,
        "lab_name": talent.lab_name,
        "selected_works": [
            {
                "work_id": w.work_id,
                "title": w.title,
                "publication_year": w.publication_year,
                "venue_name": w.venue_name,
                "citation_count": w.citation_count,
                "doi": w.doi,
            }
            for w in works
        ],
        "tech_tags": [
            {
                "tech_domain_id": domain.tech_domain_id,
                "tech_domain_name": domain.domain_name,
                "tech_direction_id": direction.tech_direction_id if direction else None,
                "tech_direction_name": direction.direction_name if direction else None,
            }
            for _tag, domain, direction in tech_tag_rows
        ],
    }


@router.get("/stats", summary="学术域统计")
async def academic_stats(
    session: AsyncSession = Depends(get_async_session),
    _principal: dict = Depends(_require),
) -> dict:
    return await TalentService(session).get_statistics()
