"""
Homepage API endpoint.
首页聚合数据接口
"""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import get_cache_connection
from app.core.database import get_async_session
from app.domains.academic.repositories.homepage_repository import HomepageRepository
from app.domains.academic.schemas.homepage import (
    HomepageHighlightsResponse,
    HotResearchTopicItem,
    HotTechDomainItem,
    TopCountryItem,
    TopSchoolItem,
)
from app.domains.shared.services.cache_keys import CacheKeys, CacheTTL
from app.domains.shared.services.cache_service import CacheService

router = APIRouter(prefix="/homepage", tags=["Homepage"])


@router.get(
    "/highlights",
    response_model=HomepageHighlightsResponse,
    summary="获取首页聚合数据",
    description="返回首页热点数据，包括热门技术领域、主要国家、Top院校",
)
async def get_highlights(
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get homepage highlights data.

    Returns:
    - hot_tech_domains: 热门技术领域列表 (按人才数Top6)
    - top_countries: 主要国家列表 (按人才数Top5)
    - top_schools: Top院校列表 (按人才数Top5)
    - hot_research_topics: 热门研究方向列表 (按人才数Top10)
    """
    # Initialize cache service
    cache_conn = await get_cache_connection()
    cache = CacheService(cache_conn)

    async def fetch_highlights():
        """Fetch highlights data from database."""
        repo = HomepageRepository(session)

        # Fetch all data in parallel
        hot_tech_domains = await repo.get_hot_tech_domains(limit=6)
        top_countries = await repo.get_top_countries(limit=5)
        top_schools = await repo.get_top_schools(limit=5)
        hot_research_topics = await repo.get_hot_research_topics(limit=10)

        return {
            "hot_tech_domains": hot_tech_domains,
            "top_countries": top_countries,
            "top_schools": top_schools,
            "hot_research_topics": hot_research_topics,
        }

    # Try cache first, fallback to database
    cached_data = await cache.get_or_set(
        CacheKeys.STATS_HOME_HIGHLIGHTS,
        factory=fetch_highlights,
        ttl=CacheTTL.MEDIUM,
    )

    if cached_data:
        hot_tech_domains = cached_data.get("hot_tech_domains", [])
        top_countries = cached_data.get("top_countries", [])
        top_schools = cached_data.get("top_schools", [])
        hot_research_topics = cached_data.get("hot_research_topics", [])
    else:
        # Fallback to direct database query
        repo = HomepageRepository(session)
        hot_tech_domains = await repo.get_hot_tech_domains(limit=6)
        top_countries = await repo.get_top_countries(limit=5)
        top_schools = await repo.get_top_schools(limit=5)
        hot_research_topics = await repo.get_hot_research_topics(limit=10)

    now = datetime.now()
    version = now.strftime("%Y%m%d-%H%M%S")

    return HomepageHighlightsResponse(
        hot_tech_domains=[HotTechDomainItem(**item) for item in hot_tech_domains],
        top_countries=[TopCountryItem(**item) for item in top_countries],
        top_schools=[TopSchoolItem(**item) for item in top_schools],
        hot_research_topics=[HotResearchTopicItem(**item) for item in hot_research_topics],
        version=version,
        generated_at=now.isoformat(),
    )
