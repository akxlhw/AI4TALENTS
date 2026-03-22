"""
Overview API endpoint.
Returns homepage statistics.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
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
    """
    repo = StatisticsRepository(session)
    stats = await repo.get_active_overview_stats()

    if not stats:
        raise HTTPException(
            status_code=404,
            detail="No statistics available. Please run the build process first.",
        )

    return OverviewResponse(
        stats=OverviewStats(
            school_count=stats.school_count,
            professor_count=stats.professor_count,
            student_count=stats.student_count,
            talent_count=stats.talent_count,
        ),
        version=stats.stat_version,
        generated_at=stats.generated_at,
    )
