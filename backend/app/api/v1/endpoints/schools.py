"""
Schools API endpoints.
Provides school list, detail, and statistics.
"""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.school import School
from app.repositories.school_repository import SchoolRepository
from app.repositories.talent_repository import TalentRepository
from app.schemas.common import PaginatedResponse
from app.schemas.overview import SchoolDetail, SchoolStats, SchoolSummary, TalentSummary

router = APIRouter(prefix="/schools", tags=["Schools"])


@router.get(
    "",
    response_model=PaginatedResponse[SchoolSummary],
    summary="获取学校列表",
    description="分页查询学校列表，支持按国家和关键词筛选",
)
async def list_schools(
    country_code: str | None = Query(None, description="按国家代码筛选 (ISO 3166-1 alpha-2)"),
    keyword: str | None = Query(None, description="搜索关键词"),
    is_top_school: bool | None = Query(None, description="按Top院校筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=5000, description="每页数量"),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get paginated list of schools.

    Supports filtering by:
    - country_code: Filter schools by country code (ISO 3166-1 alpha-2)
    - keyword: Search in school name and alias
    - is_top_school: Filter by top school status
    """
    repo = SchoolRepository(session)
    schools, total = await repo.get_list(
        country_code=country_code,
        keyword=keyword,
        is_top_school=is_top_school,
        page=page,
        page_size=page_size,
    )

    items = [
        SchoolSummary(
            school_id=school.school_id,
            school_name=school.school_name,
            school_alias=school.school_alias,
            country_code=school.country_code,
            country_name=school.country_name,
            professor_count=school.professor_count,
            student_count=school.student_count,
            homepage_url=school.homepage_url,
            is_top_school=getattr(school, 'is_top_school', False),
        )
        for school in schools
    ]

    return PaginatedResponse.create(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


# ============================================
# Top School APIs - MUST be before /{school_id}
# ============================================

@router.get(
    "/top-schools",
    response_model=PaginatedResponse[SchoolSummary],
    summary="获取Top院校列表",
    description="获取管理员配置的Top院校列表",
)
async def list_top_schools(
    country_code: str | None = Query(None, description="按国家代码筛选 (ISO 3166-1 alpha-2)"),
    keyword: str | None = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=5000, description="每页数量"),
    session: AsyncSession = Depends(get_async_session),
):
    """获取Top院校列表"""
    repo = SchoolRepository(session)

    # Query with is_top_school filter
    schools, total = await repo.get_list(
        country_code=country_code,
        keyword=keyword,
        is_top_school=True,
        page=page,
        page_size=page_size,
    )

    items = [
        SchoolSummary(
            school_id=school.school_id,
            school_name=school.school_name,
            school_alias=school.school_alias,
            country_code=school.country_code,
            country_name=school.country_name,
            professor_count=school.professor_count,
            student_count=school.student_count,
            homepage_url=school.homepage_url,
            is_top_school=True,
        )
        for school in schools
    ]

    return PaginatedResponse.create(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{school_id}/talents",
    response_model=PaginatedResponse[TalentSummary],
    summary="获取学校人才列表",
    description="分页查询指定学校的人才列表，支持按角色类型筛选",
)
async def get_school_talents(
    school_id: int,
    role_type: str | None = Query(None, description="按角色类型筛选 (professor/student/graduated/unknown)"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=5000, description="每页数量"),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get paginated list of talents for a specific school.

    Supports filtering by:
    - role_type: Filter by role type
    """
    school_repo = SchoolRepository(session)
    talent_repo = TalentRepository(session)

    # Verify school exists
    school = await school_repo.get_by_id(school_id)
    if not school:
        raise HTTPException(status_code=404, detail="School not found")

    talents, total = await talent_repo.get_list(
        school_id=school_id,
        role_type=role_type,
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
    "/{school_id}/stats",
    response_model=SchoolStats,
    summary="获取学校统计",
    description="返回学校的人才统计数据",
)
async def get_school_stats(
    school_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get statistics for a specific school.

    Returns talent counts by role type.
    """
    school_repo = SchoolRepository(session)

    # Verify school exists
    school = await school_repo.get_by_id(school_id)
    if not school:
        raise HTTPException(status_code=404, detail="School not found")

    talent_counts = await school_repo.get_talent_counts(school_id)

    return SchoolStats(
        professor_count=talent_counts["professor"],
        student_count=talent_counts["student"],
        talent_count=talent_counts["total"],
        graduate_count=talent_counts["graduated"],
        unknown_count=talent_counts["unknown"],
    )


@router.get(
    "/{school_id}",
    response_model=SchoolDetail,
    summary="获取学校详情",
    description="返回学校的详细信息，包括介绍、主页链接和人才统计",
)
async def get_school(
    school_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get detailed information about a specific school.

    Returns:
    - Basic school information
    - Country information
    - Talent statistics by role
    """
    school_repo = SchoolRepository(session)

    school = await school_repo.get_by_id(school_id)
    if not school:
        raise HTTPException(status_code=404, detail="School not found")

    # Get talent counts
    talent_counts = await school_repo.get_talent_counts(school_id)

    return SchoolDetail(
        school_id=school.school_id,
        school_name=school.school_name,
        school_alias=school.school_alias,
        country_code=school.country_code,
        country_name=school.country_name,
        school_intro=school.school_intro,
        homepage_url=school.homepage_url,
        professor_count=talent_counts["professor"],
        student_count=talent_counts["student"],
        talent_count=talent_counts["total"],
        graduate_count=talent_counts["graduated"],
        unknown_count=talent_counts["unknown"],
        is_top_school=getattr(school, 'is_top_school', False),
    )


# ============================================
# Top School Management APIs
# ============================================

@router.put(
    "/{school_id}/set-top",
    summary="设置为Top院校",
    description="将指定学校设置为Top院校",
)
async def set_top_school(
    school_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    """设置学校为Top院校"""
    repo = SchoolRepository(session)
    school = await repo.get_by_id(school_id)
    if not school:
        raise HTTPException(status_code=404, detail="School not found")

    school.is_top_school = True
    await session.commit()

    return {"message": "School set as top school", "school_id": school_id}


@router.put(
    "/{school_id}/unset-top",
    summary="取消Top院校",
    description="取消指定学校的Top院校标记",
)
async def unset_top_school(
    school_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    """取消学校的Top院校标记"""
    repo = SchoolRepository(session)
    school = await repo.get_by_id(school_id)
    if not school:
        raise HTTPException(status_code=404, detail="School not found")

    school.is_top_school = False
    await session.commit()

    return {"message": "School unset as top school", "school_id": school_id}


@router.post(
    "/batch-set-top",
    summary="批量设置Top院校",
    description="批量将多个学校设置为Top院校",
)
async def batch_set_top_schools(
    school_ids: list[int] = Body(..., description="学校ID列表"),
    session: AsyncSession = Depends(get_async_session),
):
    """批量设置Top院校"""
    if not school_ids:
        raise HTTPException(status_code=400, detail="school_ids cannot be empty")

    result = await session.execute(
        update(School)
        .where(School.school_id.in_(school_ids))
        .values(is_top_school=True)
    )
    await session.commit()

    return {
        "message": f"Set {result.rowcount} schools as top schools",
        "updated_count": result.rowcount,
    }


@router.post(
    "/batch-unset-top",
    summary="批量取消Top院校",
    description="批量取消多个学校的Top院校标记",
)
async def batch_unset_top_schools(
    school_ids: list[int] = Body(..., description="学校ID列表"),
    session: AsyncSession = Depends(get_async_session),
):
    """批量取消Top院校"""
    if not school_ids:
        raise HTTPException(status_code=400, detail="school_ids cannot be empty")

    result = await session.execute(
        update(School)
        .where(School.school_id.in_(school_ids))
        .values(is_top_school=False)
    )
    await session.commit()

    return {
        "message": f"Unset {result.rowcount} schools as top schools",
        "updated_count": result.rowcount,
    }
