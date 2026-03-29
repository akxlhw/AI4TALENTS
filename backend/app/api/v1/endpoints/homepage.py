"""
Homepage API endpoint.
首页聚合数据接口
"""
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.repositories.homepage_repository import HomepageRepository
from app.schemas.homepage import (
    HomepageHighlightsResponse,
    HotTechElementItem,
    TopCountryItem,
    TopSchoolItem,
)

router = APIRouter(prefix="/homepage", tags=["Homepage"])


@router.get(
    "/highlights",
    response_model=HomepageHighlightsResponse,
    summary="获取首页聚合数据",
    description="返回首页热点数据，包括热门技术要素、主要国家、Top院校",
)
async def get_highlights(
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get homepage highlights data.

    Returns:
    - hot_tech_elements: 热门技术要素列表 (按人才数Top6)
    - top_countries: 主要国家列表 (按人才数Top5)
    - top_schools: Top院校列表 (按人才数Top5)
    """
    repo = HomepageRepository(session)

    # Fetch all data in parallel
    hot_tech_elements = await repo.get_hot_tech_elements(limit=6)
    top_countries = await repo.get_top_countries(limit=5)
    top_schools = await repo.get_top_schools(limit=5)

    now = datetime.now()
    version = now.strftime("%Y%m%d-%H%M%S")

    return HomepageHighlightsResponse(
        hot_tech_elements=[
            HotTechElementItem(**item) for item in hot_tech_elements
        ],
        top_countries=[
            TopCountryItem(**item) for item in top_countries
        ],
        top_schools=[
            TopSchoolItem(**item) for item in top_schools
        ],
        version=version,
        generated_at=now.isoformat(),
    )
