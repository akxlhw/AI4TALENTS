"""
Search API endpoint.
Provides talent search functionality.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.repositories.talent_repository import TalentRepository
from app.schemas.overview import SearchResponse, SearchTalentResult

router = APIRouter(prefix="/search", tags=["Search"])


@router.get(
    "/talents",
    response_model=SearchResponse,
    summary="搜索人才",
    description="根据关键词搜索人才，支持按角色类型筛选",
)
async def search_talents(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    role_type: Optional[str] = Query(None, description="按角色类型筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Search talents by keyword.

    Searches in:
    - Name (Chinese)
    - Name (English)
    - Current title/position

    Supports filtering by role_type.
    Results are ordered by citation count.
    """
    repo = TalentRepository(session)

    # For pagination in search, we need to get all matches and slice
    # This is a simple implementation; for production, consider using
    # full-text search capabilities of PostgreSQL or Elasticsearch
    all_results = await repo.search(
        keyword=q,
        limit=1000,  # Get enough results for pagination
        role_type=role_type,
    )

    total = len(all_results)

    # Apply pagination
    offset = (page - 1) * page_size
    paginated_results = all_results[offset : offset + page_size]

    items = [
        SearchTalentResult(
            talent_id=talent.talent_id,
            name=talent.name,
            name_en=talent.name_en,
            role_type=talent.role_type,
            school_name=talent.school.school_name if talent.school else None,
            current_title=talent.current_title,
            works_count=talent.works_count,
            cited_by_count=talent.cited_by_count,
            h_index=talent.h_index,
            topic_tags=talent.topic_tags or [],
            highlight=None,  # Could be enhanced with keyword highlighting
        )
        for talent in paginated_results
    ]

    return SearchResponse(
        items=items,
        total=total,
        query=q,
        page=page,
        page_size=page_size,
    )
