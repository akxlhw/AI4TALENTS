"""
Talent list/detail query endpoints.
人才列表、详情与代表作品查询接口

Split from talents.py; routes keep the original /talents prefix.

Architecture: Endpoint -> Service -> Repository
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.academic.schemas.overview import (
    SelectedWorkResponse,
    TalentDetail,
    TalentSummary,
    TechTagItem,
)
from app.domains.academic.services.talent_service import TalentService
from app.domains.shared.schemas.common import PaginatedResponse

router = APIRouter(prefix="/talents", tags=["Talents"])


@router.get(
    "",
    response_model=PaginatedResponse[TalentSummary],
    summary="获取人才列表",
    description="分页查询人才列表，支持多种筛选条件",
)
async def list_talents(
    school_id: int | None = Query(None, description="按学校ID筛选"),
    country_code: str | None = Query(None, description="按国家代码筛选 (如 US, CN)"),
    role_type: str | None = Query(
        None, description="按角色类型筛选 (professor/student/graduated/unknown)"
    ),
    min_works: int | None = Query(None, description="最小论文数"),
    min_citations: int | None = Query(None, description="最小引用数"),
    keyword: str | None = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get paginated list of talents.

    Supports filtering by:
    - school_id: Filter by school
    - country_code: Filter by country code (via school)
    - role_type: Filter by role type
    - min_works: Minimum works count
    - min_citations: Minimum citation count
    - keyword: Search in name, English name, and title
    """
    service = TalentService(session)
    talents, total = await service.get_talent_list(
        school_id=school_id,
        country_code=country_code,
        role_type=role_type,
        min_works=min_works,
        min_citations=min_citations,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )

    items = [
        TalentSummary(
            talent_id=talent.talent_id,
            name=talent.name,
            name_en=talent.name_en,
            orcid=talent.orcid,
            role_type=talent.role_type,
            role_confidence=talent.role_confidence,
            school_id=talent.primary_school_id,
            school_name=talent.primary_school_name,
            # Primary institutions
            education_school_id=talent.education_school_id,
            education_school_name=(
                talent.education_school.school_name if talent.education_school else None
            ),
            company_school_id=talent.company_school_id,
            company_school_name=(
                talent.company_school.school_name if talent.company_school else None
            ),
            current_title=talent.current_title,
            works_count=talent.works_count,
            cited_by_count=talent.cited_by_count,
            h_index=talent.h_index,
            topic_tags=talent.topic_tags or [],
            openalex_topics=talent.openalex_topics or [],
        )
        for talent in talents
    ]

    return PaginatedResponse.create(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{talent_id}",
    response_model=TalentDetail,
    summary="获取人才详情",
    description="返回人才的详细信息，包括研究兴趣、代表作品等",
)
async def get_talent(
    talent_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get detailed information about a specific talent.

    Returns:
    - Basic talent information
    - School affiliation
    - Research statistics
    - Role profile
    - Selected works
    - Tech tags
    """
    service = TalentService(session)
    talent = await service.get_talent_by_id(talent_id)

    if not talent:
        raise HTTPException(status_code=404, detail="Talent not found")

    # Build selected works list
    selected_works = [
        SelectedWorkResponse(
            work_id=work.work_id,
            title=work.title,
            publication_year=work.publication_year,
            venue_name=work.venue_name,
            citation_count=work.citation_count,
            doi=work.doi,
        )
        for work in (talent.selected_works or [])
    ]

    # Fetch tech tags
    tech_tag_rows = await service.get_talent_tech_tags(talent_id)
    tech_tags = [
        TechTagItem(
            tech_domain_id=domain.tech_domain_id,
            tech_domain_name=domain.domain_name,
            tech_direction_id=direction.tech_direction_id if direction else None,
            tech_direction_name=direction.direction_name if direction else None,
        )
        for _tag, domain, direction in tech_tag_rows
    ]

    return TalentDetail(
        talent_id=talent.talent_id,
        name=talent.name,
        name_en=talent.name_en,
        orcid=talent.orcid,
        role_type=talent.role_type,
        role_confidence=talent.role_confidence,
        school_id=talent.primary_school_id,
        school_name=talent.primary_school_name,
        # Primary institutions
        education_school_id=talent.education_school_id,
        education_school_name=(
            talent.education_school.school_name if talent.education_school else None
        ),
        company_school_id=talent.company_school_id,
        company_school_name=talent.company_school.school_name if talent.company_school else None,
        current_title=talent.current_title,
        works_count=talent.works_count,
        cited_by_count=talent.cited_by_count,
        h_index=talent.h_index,
        latest_active_year=talent.latest_active_year,
        topic_tags=talent.topic_tags or [],
        openalex_topics=talent.openalex_topics or [],
        tech_tags=tech_tags,
        summary=talent.summary,
        department_name=talent.department_name,
        lab_name=talent.lab_name,
        role_reason=talent.role_profile.role_reason if talent.role_profile else None,
        academic_age=talent.role_profile.academic_age if talent.role_profile else None,
        selected_works=selected_works,
    )


@router.get(
    "/{talent_id}/works",
    response_model=list[SelectedWorkResponse],
    summary="获取人才代表作品",
    description="返回人才的代表作品列表",
)
async def get_talent_works(
    talent_id: int,
    limit: int = Query(10, ge=1, le=50, description="返回数量限制"),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get selected works for a specific talent.

    Returns list of representative works ordered by citation count.
    """
    service = TalentService(session)

    # Verify talent exists
    if not await service.talent_exists(talent_id):
        raise HTTPException(status_code=404, detail="Talent not found")

    works = await service.get_selected_works(talent_id, limit=limit)

    return [
        SelectedWorkResponse(
            work_id=work.work_id,
            title=work.title,
            publication_year=work.publication_year,
            venue_name=work.venue_name,
            citation_count=work.citation_count,
            doi=work.doi,
        )
        for work in works
    ]
