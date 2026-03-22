"""
Countries API endpoint.
Returns list of countries with school counts.
"""
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.repositories.country_repository import CountryRepository
from app.schemas.overview import CountryListResponse, CountrySummary

router = APIRouter(prefix="/countries", tags=["Countries"])


@router.get(
    "",
    response_model=CountryListResponse,
    summary="获取国家列表",
    description="返回所有国家及其学校数量统计",
)
async def list_countries(
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get list of all countries with school counts.

    Returns countries ordered by sort_order, including:
    - Country ID and code
    - Country name (CN and EN)
    - Number of schools in each country
    - Number of professors in each country
    """
    repo = CountryRepository(session)
    countries_data = await repo.get_with_school_counts()

    # Build response with professor counts
    items = []
    for country_data in countries_data:
        professor_count = await repo.get_professor_count_by_country(
            country_data["country_id"]
        )
        items.append(
            CountrySummary(
                country_id=country_data["country_id"],
                country_code=country_data["country_code"],
                country_name_cn=country_data["country_name_cn"],
                country_name_en=country_data["country_name_en"],
                school_count=country_data["school_count"],
                professor_count=professor_count,
            )
        )

    return CountryListResponse(
        items=items,
        total=len(items),
    )
