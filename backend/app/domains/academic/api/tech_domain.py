"""
Tech Domain API endpoints.
技术领域相关接口
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import get_cache_connection
from app.core.database import get_async_session
from app.domains.academic.schemas.tech_domain import (
    CountryDistributionItem,
    CountryDistributionResponse,
    OverallStatsResponse,
    SchoolDistributionItem,
    SchoolDistributionResponse,
    TalentInTechDomain,
    TechDomainListResponse,
    TechDomainResponse,
    TechDomainStatsResponse,
    TechDomainSummary,
)
from app.domains.academic.services.tech_domain_service import TechDomainService
from app.domains.shared.schemas.common import PaginatedResponse
from app.domains.shared.services.cache_keys import CacheKeys, CacheTTL
from app.domains.shared.services.cache_service import CacheService

router = APIRouter(prefix="/tech-domains", tags=["Tech Domains"])


@router.get(
    "",
    response_model=TechDomainListResponse,
    summary="获取技术领域列表",
    description="返回所有启用的技术领域及其技术方向",
)
async def list_tech_domains(
    session: AsyncSession = Depends(get_async_session),
):
    """Get all tech domains with their directions."""
    service = TechDomainService(session)
    domains = await service.get_all_domains()

    items = [
        TechDomainResponse(
            tech_domain_id=d.tech_domain_id,
            domain_code=d.domain_code,
            domain_name=d.domain_name,
            domain_name_en=d.domain_name_en,
            domain_desc=d.domain_desc,
            sort_order=d.sort_order,
            directions=[
                {
                    "tech_direction_id": dir.tech_direction_id,
                    "direction_code": dir.direction_code,
                    "direction_name": dir.direction_name,
                    "direction_name_en": dir.direction_name_en,
                    "tech_domain_id": dir.tech_domain_id,
                    "sort_order": dir.sort_order,
                }
                for dir in d.directions
                if dir.is_enabled
            ],
        )
        for d in domains
    ]

    return TechDomainListResponse(items=items, total=len(items))


@router.get(
    "/summary",
    response_model=TechDomainSummary,
    summary="获取技术领域概要统计",
    description="返回技术领域总数、技术方向总数、关联人才总数",
)
async def get_tech_domain_summary(
    session: AsyncSession = Depends(get_async_session),
):
    """Get tech domain summary statistics."""
    service = TechDomainService(session)
    stats = await service.get_domain_stats()
    return TechDomainSummary(**stats)


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
    service = TechDomainService(session)
    cache_conn = await get_cache_connection()
    cache = CacheService(cache_conn)

    async def fetch_stats():
        return await service.get_overall_stats()

    stats = await cache.get_or_set(
        CacheKeys.STATS_OVERALL,
        factory=fetch_stats,
        ttl=CacheTTL.MEDIUM,
    )

    if not stats:
        # Fallback to direct query
        stats = await service.get_overall_stats()

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
    service = TechDomainService(session)
    items = await service.get_country_distribution()
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
    service = TechDomainService(session)
    items, total = await service.get_school_distribution(page=page, page_size=page_size)
    return SchoolDistributionResponse(
        items=[SchoolDistributionItem(**item) for item in items],
        total=total,
    )


@router.get(
    "/overall-talents",
    response_model=PaginatedResponse[TalentInTechDomain],
    summary="获取总体人才列表",
    description="返回用户权限范围内所有人才列表",
)
async def get_overall_talents(
    country_code: str | None = Query(None, description="按国家代码筛选 (ISO 3166-1 alpha-2)"),
    school_id: int | None = Query(None, description="按院校筛选"),
    role_type: str | None = Query(None, description="按角色类型筛选"),
    keyword: str | None = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    """Get overall talent list."""
    service = TechDomainService(session)
    talents, total = await service.get_talent_list(
        country_code=country_code,
        school_id=school_id,
        role_type=role_type,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )

    items = [
        TalentInTechDomain(
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
    "/{domain_id}",
    response_model=TechDomainResponse,
    summary="获取单个技术领域",
    description="返回指定技术领域的详细信息",
)
async def get_tech_domain(
    domain_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    """Get a specific tech domain by ID."""
    service = TechDomainService(session)
    domain = await service.get_domain_by_id(domain_id)

    if not domain:
        raise HTTPException(status_code=404, detail="Tech domain not found")

    return TechDomainResponse(
        tech_domain_id=domain.tech_domain_id,
        domain_code=domain.domain_code,
        domain_name=domain.domain_name,
        domain_name_en=domain.domain_name_en,
        domain_desc=domain.domain_desc,
        sort_order=domain.sort_order,
        directions=[
            {
                "tech_direction_id": d.tech_direction_id,
                "direction_code": d.direction_code,
                "direction_name": d.direction_name,
                "direction_name_en": d.direction_name_en,
                "tech_domain_id": d.tech_domain_id,
                "sort_order": d.sort_order,
            }
            for d in domain.directions
            if d.is_enabled
        ],
    )


@router.get(
    "/{domain_id}/stats",
    response_model=TechDomainStatsResponse,
    summary="获取技术领域统计",
    description="返回指定技术领域的人才数、覆盖国家数、覆盖院校数等统计",
)
async def get_domain_stats(
    domain_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    """Get statistics for a specific tech domain."""
    service = TechDomainService(session)

    # Verify domain exists
    domain = await service.get_domain_by_id(domain_id)
    if not domain:
        raise HTTPException(status_code=404, detail="Tech domain not found")

    cache_conn = await get_cache_connection()
    cache = CacheService(cache_conn)
    cache_key = CacheKeys.STATS_TECH_DOMAIN.format(domain_id=domain_id)

    async def fetch_stats():
        return await service.get_domain_stats(domain_id)

    stats = await cache.get_or_set(
        cache_key,
        factory=fetch_stats,
        ttl=CacheTTL.MEDIUM,
    )

    if not stats:
        # Fallback to direct query
        stats = await service.get_domain_stats(domain_id)

    return TechDomainStatsResponse(**stats)


@router.get(
    "/{domain_id}/countries",
    response_model=CountryDistributionResponse,
    summary="获取国家分布",
    description="返回指定技术领域的人才国家分布",
)
async def get_domain_country_distribution(
    domain_id: int,
    direction_id: int | None = Query(None, description="按技术方向筛选"),
    session: AsyncSession = Depends(get_async_session),
):
    """Get country distribution for a tech domain."""
    service = TechDomainService(session)

    # Verify domain exists
    domain = await service.get_domain_by_id(domain_id)
    if not domain:
        raise HTTPException(status_code=404, detail="Tech domain not found")

    items = await service.get_country_distribution(domain_id, direction_id)
    return CountryDistributionResponse(items=[CountryDistributionItem(**item) for item in items])


@router.get(
    "/{domain_id}/schools",
    response_model=SchoolDistributionResponse,
    summary="获取院校分布",
    description="返回指定技术领域的人才院校分布",
)
async def get_domain_school_distribution(
    domain_id: int,
    direction_id: int | None = Query(None, description="按技术方向筛选"),
    country_code: str | None = Query(None, description="按国家代码筛选 (ISO 3166-1 alpha-2)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    """Get school distribution for a tech domain."""
    service = TechDomainService(session)

    # Verify domain exists
    domain = await service.get_domain_by_id(domain_id)
    if not domain:
        raise HTTPException(status_code=404, detail="Tech domain not found")

    items, total = await service.get_school_distribution(
        domain_id=domain_id,
        direction_id=direction_id,
        country_code=country_code,
        page=page,
        page_size=page_size,
    )
    return SchoolDistributionResponse(
        items=[SchoolDistributionItem(**item) for item in items],
        total=total,
    )


@router.get(
    "/{domain_id}/talents",
    response_model=PaginatedResponse[TalentInTechDomain],
    summary="获取人才列表",
    description="返回指定技术领域的人才列表",
)
async def get_domain_talents(
    domain_id: int,
    direction_id: int | None = Query(None, description="按技术方向筛选"),
    country_code: str | None = Query(None, description="按国家代码筛选 (ISO 3166-1 alpha-2)"),
    school_id: int | None = Query(None, description="按院校筛选"),
    role_type: str | None = Query(None, description="按角色类型筛选"),
    keyword: str | None = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    """Get talent list for a tech domain."""
    service = TechDomainService(session)

    # Verify domain exists
    domain = await service.get_domain_by_id(domain_id)
    if not domain:
        raise HTTPException(status_code=404, detail="Tech domain not found")

    talents, total = await service.get_talent_list(
        domain_id=domain_id,
        direction_id=direction_id,
        country_code=country_code,
        school_id=school_id,
        role_type=role_type,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )

    items = [
        TalentInTechDomain(
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
