"""
Tech Element API endpoints.
技术要素相关接口
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.repositories.tech_element_repository import TechElementRepository
from app.repositories.talent_repository import TalentRepository
from app.schemas.common import PaginatedResponse
from app.schemas.tech_element import (
    TechElementResponse,
    TechElementListResponse,
    TechElementStatsResponse,
    TechElementSummary,
    CountryDistributionItem,
    CountryDistributionResponse,
    SchoolDistributionItem,
    SchoolDistributionResponse,
    TalentInTechElement,
    OverallStatsResponse,
)

router = APIRouter(prefix="/tech-elements", tags=["Tech Elements"])


@router.get(
    "",
    response_model=TechElementListResponse,
    summary="获取技术要素列表",
    description="返回所有启用的技术要素及其技术方向",
)
async def list_tech_elements(
    session: AsyncSession = Depends(get_async_session),
):
    """Get all tech elements with their directions."""
    repo = TechElementRepository(session)
    elements = await repo.get_all_elements()

    items = [
        TechElementResponse(
            tech_element_id=e.tech_element_id,
            element_code=e.element_code,
            element_name=e.element_name,
            element_name_en=e.element_name_en,
            element_desc=e.element_desc,
            sort_order=e.sort_order,
            directions=[
                {
                    'tech_direction_id': d.tech_direction_id,
                    'direction_code': d.direction_code,
                    'direction_name': d.direction_name,
                    'direction_name_en': d.direction_name_en,
                    'tech_element_id': d.tech_element_id,
                    'sort_order': d.sort_order,
                }
                for d in e.directions if d.is_enabled
            ]
        )
        for e in elements
    ]

    return TechElementListResponse(items=items, total=len(items))


@router.get(
    "/summary",
    response_model=TechElementSummary,
    summary="获取技术要素概要统计",
    description="返回技术要素总数、技术方向总数、关联人才总数",
)
async def get_tech_element_summary(
    session: AsyncSession = Depends(get_async_session),
):
    """Get tech element summary statistics."""
    repo = TechElementRepository(session)
    stats = await repo.get_element_stats()
    return TechElementSummary(**stats)


@router.get(
    "/overall-stats",
    response_model=OverallStatsResponse,
    summary="获取总体统计",
    description="返回用户权限范围内的总体统计数据（人才总数、教授数、学生数、国家数、院校数等）",
)
async def get_overall_stats(
    session: AsyncSession = Depends(get_async_session),
):
    """Get overall statistics for user's permission scope."""
    repo = TechElementRepository(session)
    stats = await repo.get_overall_stats()
    return OverallStatsResponse(**stats)


@router.get(
    "/overall-countries",
    response_model=CountryDistributionResponse,
    summary="获取总体国家分布",
    description="返回用户权限范围内所有人才的国家分布",
)
async def get_overall_country_distribution(
    session: AsyncSession = Depends(get_async_session),
):
    """Get overall country distribution."""
    repo = TechElementRepository(session)
    items = await repo.get_country_distribution()
    return CountryDistributionResponse(items=[CountryDistributionItem(**item) for item in items])


@router.get(
    "/overall-schools",
    response_model=SchoolDistributionResponse,
    summary="获取总体院校分布",
    description="返回用户权限范围内所有人才的院校分布",
)
async def get_overall_school_distribution(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    """Get overall school distribution."""
    repo = TechElementRepository(session)
    items, total = await repo.get_school_distribution(page=page, page_size=page_size)
    return SchoolDistributionResponse(
        items=[SchoolDistributionItem(**item) for item in items],
        total=total,
    )


@router.get(
    "/overall-talents",
    response_model=PaginatedResponse[TalentInTechElement],
    summary="获取总体人才列表",
    description="返回用户权限范围内所有人才列表",
)
async def get_overall_talents(
    country_id: Optional[int] = Query(None, description="按国家筛选"),
    school_id: Optional[int] = Query(None, description="按院校筛选"),
    role_type: Optional[str] = Query(None, description="按角色类型筛选"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    """Get overall talent list."""
    repo = TechElementRepository(session)
    talents, total = await repo.get_talent_list(
        country_id=country_id,
        school_id=school_id,
        role_type=role_type,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )

    items = [
        TalentInTechElement(
            talent_id=t.talent_id,
            name=t.name,
            name_en=t.name_en,
            role_type=t.role_type,
            school_name=t.school.school_name if t.school else None,
            current_title=t.current_title,
            h_index=t.h_index,
            works_count=t.works_count,
            topic_tags=t.topic_tags or [],
            openalex_topics=t.openalex_topics or [],
        )
        for t in talents
    ]

    return PaginatedResponse.create(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{element_id}",
    response_model=TechElementResponse,
    summary="获取单个技术要素",
    description="返回指定技术要素的详细信息",
)
async def get_tech_element(
    element_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    """Get a specific tech element by ID."""
    repo = TechElementRepository(session)
    element = await repo.get_element_by_id(element_id)

    if not element:
        raise HTTPException(status_code=404, detail="Tech element not found")

    return TechElementResponse(
        tech_element_id=element.tech_element_id,
        element_code=element.element_code,
        element_name=element.element_name,
        element_name_en=element.element_name_en,
        element_desc=element.element_desc,
        sort_order=element.sort_order,
        directions=[
            {
                'tech_direction_id': d.tech_direction_id,
                'direction_code': d.direction_code,
                'direction_name': d.direction_name,
                'direction_name_en': d.direction_name_en,
                'tech_element_id': d.tech_element_id,
                'sort_order': d.sort_order,
            }
            for d in element.directions if d.is_enabled
        ]
    )


@router.get(
    "/{element_id}/stats",
    response_model=TechElementStatsResponse,
    summary="获取技术要素统计",
    description="返回指定技术要素的人才数、覆盖国家数、覆盖院校数等统计",
)
async def get_element_stats(
    element_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    """Get statistics for a specific tech element."""
    repo = TechElementRepository(session)

    # Verify element exists
    element = await repo.get_element_by_id(element_id)
    if not element:
        raise HTTPException(status_code=404, detail="Tech element not found")

    stats = await repo.get_element_stats(element_id)
    return TechElementStatsResponse(**stats)


@router.get(
    "/{element_id}/countries",
    response_model=CountryDistributionResponse,
    summary="获取国家分布",
    description="返回指定技术要素的人才国家分布",
)
async def get_element_country_distribution(
    element_id: int,
    direction_id: Optional[int] = Query(None, description="按技术方向筛选"),
    session: AsyncSession = Depends(get_async_session),
):
    """Get country distribution for a tech element."""
    repo = TechElementRepository(session)

    # Verify element exists
    element = await repo.get_element_by_id(element_id)
    if not element:
        raise HTTPException(status_code=404, detail="Tech element not found")

    items = await repo.get_country_distribution(element_id, direction_id)
    return CountryDistributionResponse(items=[CountryDistributionItem(**item) for item in items])


@router.get(
    "/{element_id}/schools",
    response_model=SchoolDistributionResponse,
    summary="获取院校分布",
    description="返回指定技术要素的人才院校分布",
)
async def get_element_school_distribution(
    element_id: int,
    direction_id: Optional[int] = Query(None, description="按技术方向筛选"),
    country_id: Optional[int] = Query(None, description="按国家筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    """Get school distribution for a tech element."""
    repo = TechElementRepository(session)

    # Verify element exists
    element = await repo.get_element_by_id(element_id)
    if not element:
        raise HTTPException(status_code=404, detail="Tech element not found")

    items, total = await repo.get_school_distribution(
        element_id=element_id,
        direction_id=direction_id,
        country_id=country_id,
        page=page,
        page_size=page_size,
    )
    return SchoolDistributionResponse(
        items=[SchoolDistributionItem(**item) for item in items],
        total=total,
    )


@router.get(
    "/{element_id}/talents",
    response_model=PaginatedResponse[TalentInTechElement],
    summary="获取人才列表",
    description="返回指定技术要素的人才列表",
)
async def get_element_talents(
    element_id: int,
    direction_id: Optional[int] = Query(None, description="按技术方向筛选"),
    country_id: Optional[int] = Query(None, description="按国家筛选"),
    school_id: Optional[int] = Query(None, description="按院校筛选"),
    role_type: Optional[str] = Query(None, description="按角色类型筛选"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    """Get talent list for a tech element."""
    repo = TechElementRepository(session)

    # Verify element exists
    element = await repo.get_element_by_id(element_id)
    if not element:
        raise HTTPException(status_code=404, detail="Tech element not found")

    talents, total = await repo.get_talent_list(
        element_id=element_id,
        direction_id=direction_id,
        country_id=country_id,
        school_id=school_id,
        role_type=role_type,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )

    items = [
        TalentInTechElement(
            talent_id=t.talent_id,
            name=t.name,
            name_en=t.name_en,
            role_type=t.role_type,
            school_name=t.school.school_name if t.school else None,
            current_title=t.current_title,
            h_index=t.h_index,
            works_count=t.works_count,
            topic_tags=t.topic_tags or [],
            openalex_topics=t.openalex_topics or [],
        )
        for t in talents
    ]

    return PaginatedResponse.create(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )
