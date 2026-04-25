"""
Countries API endpoint.
Returns list of countries with school counts.
Aggregated from core_school table using country_code.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.countries import COUNTRY_NAMES_CN, COUNTRY_NAMES_EN
from app.core.database import get_async_session
from app.repositories.school_repository import SchoolRepository
from app.schemas.overview import CountryListResponse, CountrySummary

router = APIRouter(prefix="/countries", tags=["Countries"])


@router.get(
    "",
    response_model=CountryListResponse,
    summary="获取国家列表",
    description="返回所有国家及其学校数量统计（从院校数据聚合）",
)
async def list_countries(
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get list of all countries with school counts.

    Countries are aggregated from core_school table by country_code.
    Returns countries ordered by school count (descending), including:
    - Country code (ISO 3166-1 alpha-2)
    - Country name (CN and EN) from constants
    - Number of schools in each country
    - Number of professors in each country
    """
    repo = SchoolRepository(session)
    rows = await repo.get_country_stats()

    # Build response with country names from constants
    items = []
    for row in rows:
        country_code = row.country_code
        items.append(
            CountrySummary(
                country_code=country_code,
                country_name_cn=COUNTRY_NAMES_CN.get(country_code, country_code),
                country_name_en=COUNTRY_NAMES_EN.get(country_code, country_code),
                school_count=row.school_count,
                professor_count=int(row.professor_count or 0),
            )
        )

    return CountryListResponse(
        items=items,
        total=len(items),
    )
