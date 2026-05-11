"""
Overview API endpoint.
Returns homepage statistics.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.academic.schemas.overview import OverviewResponse, OverviewStats
from app.domains.academic.services.statistics_service import StatisticsService

router = APIRouter(tags=["Overview"])


@router.get(
    "/overview",
    response_model=OverviewResponse,
    summary="获取首页统计数据",
    description="返回系统概览统计数据，包括学校数、教授数、学生数等",
)
async def get_overview(
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get overview statistics for homepage.

    Returns statistics about:
    - Total number of schools
    - Total number of professors
    - Total number of students
    - Total number of talents
    - Total number of countries
    - Total number of tech domains
    - Total number of tech directions
    """
    service = StatisticsService(session)
    stats = await service.get_active_overview_stats()

    if not stats:
        raise HTTPException(
            status_code=404,
            detail="No statistics available. Please run the build process first.",
        )

    # 实时计算统计数据
    country_count = await service.get_country_count()
    tech_domain_count = await service.get_tech_domain_count()
    tech_direction_count = await service.get_tech_direction_count()

    return OverviewResponse(
        stats=OverviewStats(
            school_count=stats.school_count,
            professor_count=stats.professor_count,
            student_count=stats.student_count,
            talent_count=stats.talent_count,
            country_count=country_count,
            tech_domain_count=tech_domain_count,
            tech_direction_count=tech_direction_count,
        ),
        version=stats.stat_version,
        generated_at=stats.generated_at,
    )
