"""
Overview API endpoint.
Returns homepage statistics.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.school import School
from app.models.talent import Talent
from app.models.tech_element import TechDirection, TechElement
from app.repositories.stat_repository import StatisticsRepository
from app.schemas.overview import OverviewResponse, OverviewStats

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
    - Total number of tech elements
    - Total number of tech directions
    """
    repo = StatisticsRepository(session)
    stats = await repo.get_active_overview_stats()

    if not stats:
        raise HTTPException(
            status_code=404,
            detail="No statistics available. Please run the build process first.",
        )

    # 实时计算国家数（有人才的国家）
    country_result = await session.execute(
        select(func.count(func.distinct(School.country_code)))
        .join(Talent, Talent.school_id == School.school_id)
        .where(Talent.is_visible.is_(True))
        .where(School.country_code.isnot(None))
    )
    country_count = country_result.scalar() or 0

    # 实时计算技术要素数
    tech_element_result = await session.execute(
        select(func.count(TechElement.tech_element_id))
        .where(TechElement.is_enabled.is_(True))
    )
    tech_element_count = tech_element_result.scalar() or 0

    # 实时计算技术方向数
    tech_direction_result = await session.execute(
        select(func.count(TechDirection.tech_direction_id))
        .where(TechDirection.is_enabled.is_(True))
    )
    tech_direction_count = tech_direction_result.scalar() or 0

    return OverviewResponse(
        stats=OverviewStats(
            school_count=stats.school_count,
            professor_count=stats.professor_count,
            student_count=stats.student_count,
            talent_count=stats.talent_count,
            country_count=country_count,
            tech_element_count=tech_element_count,
            tech_direction_count=tech_direction_count,
        ),
        version=stats.stat_version,
        generated_at=stats.generated_at,
    )
