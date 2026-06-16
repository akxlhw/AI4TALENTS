"""
Homepage API endpoint.
首页聚合数据接口
"""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import get_cache_connection
from app.core.database import get_async_session
from app.domains.academic.schemas.homepage import (
    HomepageHighlightsResponse,
    HotResearchTopicItem,
    HotTechDomainItem,
    TopCountryItem,
    TopSchoolItem,
)
from app.domains.academic.services.homepage_service import HomepageService
from app.domains.shared.services.cache_keys import CacheKeys, CacheTTL
from app.domains.shared.services.cache_service import CacheService

router = APIRouter(prefix="/homepage", tags=["Homepage"])

HIGHLIGHT_LIMITS = {
    "tech_domains": 6,
    "countries": 5,
    "schools": 5,
    "research_topics": 10,
}


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
    - top_domestic_schools: 国内顶尖院校列表 (按人才数Top5)
    - top_overseas_schools: 海外顶尖院校列表 (按人才数Top5)
    - hot_research_topics: 热门研究方向列表 (按人才数Top10)
    """
    # Initialize cache service
    cache_conn = await get_cache_connection()
    cache = CacheService(cache_conn)

    async def fetch_highlights():
        """Fetch highlights data from database."""
        service = HomepageService(session)

        # Fetch all data in parallel
        hot_tech_domains = await service.get_hot_tech_domains(
            limit=HIGHLIGHT_LIMITS["tech_domains"]
        )
        top_countries = await service.get_top_countries(limit=HIGHLIGHT_LIMITS["countries"])
        top_domestic_schools = await service.get_top_schools(
            limit=HIGHLIGHT_LIMITS["schools"], country_code="CN"
        )
        top_overseas_schools = await service.get_top_schools(
            limit=HIGHLIGHT_LIMITS["schools"], country_code="__OVERSEAS__"
        )
        hot_research_topics = await service.get_hot_research_topics(
            limit=HIGHLIGHT_LIMITS["research_topics"]
        )

        return {
            "hot_tech_domains": hot_tech_domains,
            "top_countries": top_countries,
            "top_domestic_schools": top_domestic_schools,
            "top_overseas_schools": top_overseas_schools,
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
        top_domestic_schools = cached_data.get("top_domestic_schools", [])
        top_overseas_schools = cached_data.get("top_overseas_schools", [])
        hot_research_topics = cached_data.get("hot_research_topics", [])
    else:
        # Fallback to direct database query
        service = HomepageService(session)
        hot_tech_domains = await service.get_hot_tech_domains(
            limit=HIGHLIGHT_LIMITS["tech_domains"]
        )
        top_countries = await service.get_top_countries(limit=HIGHLIGHT_LIMITS["countries"])
        top_domestic_schools = await service.get_top_schools(
            limit=HIGHLIGHT_LIMITS["schools"], country_code="CN"
        )
        top_overseas_schools = await service.get_top_schools(
            limit=HIGHLIGHT_LIMITS["schools"], country_code="__OVERSEAS__"
        )
        hot_research_topics = await service.get_hot_research_topics(
            limit=HIGHLIGHT_LIMITS["research_topics"]
        )

    now = datetime.now()
    version = now.strftime("%Y%m%d-%H%M%S")

    return HomepageHighlightsResponse(
        hot_tech_domains=[HotTechDomainItem(**item) for item in hot_tech_domains],
        top_countries=[TopCountryItem(**item) for item in top_countries],
        top_domestic_schools=[TopSchoolItem(**item) for item in top_domestic_schools],
        top_overseas_schools=[TopSchoolItem(**item) for item in top_overseas_schools],
        hot_research_topics=[HotResearchTopicItem(**item) for item in hot_research_topics],
        version=version,
        generated_at=now.isoformat(),
    )
