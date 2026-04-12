"""
Search API endpoint.
Provides talent search functionality with multiple modes.
v1.4 Enhanced with fulltext, semantic, and hybrid search.
"""

from __future__ import annotations

import time
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.config import settings
from app.repositories.talent_repository import TalentRepository
from app.schemas.overview import SearchResponse, SearchTalentResult
from app.schemas.v1_4 import (
    EnhancedSearchResponse,
    SemanticSearchResult,
    SearchMode,
)
from app.services.search.search_service import SearchService
from app.services.search.errors import EmptyQueryError
from app.services.llm import create_llm_gateway

router = APIRouter(prefix="/search", tags=["Search"])


@router.get(
    "/talents",
    response_model=SearchResponse,
    summary="搜索人才",
    description="根据关键词搜索人才，支持按角色类型筛选",
)
async def search_talents(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    role_type: str | None = Query(None, description="按角色类型筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Search talents by keyword (basic search, no LLM calls).

    Searches in:
    - Name (Chinese)
    - Name (English)
    - Current title/position

    Supports filtering by role_type.
    Results are ordered by citation count.
    """
    repo = TalentRepository(session)

    all_results = await repo.search(
        keyword=q,
        limit=1000,
        role_type=role_type,
    )

    total = len(all_results)
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
            highlight=None,
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


@router.get(
    "/v2/talents",
    response_model=EnhancedSearchResponse,
    summary="增强搜索 (v1.4)",
    description="支持多种搜索模式：关键词、全文、语义、混合",
)
async def enhanced_search_talents(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    mode: str = Query(
        SearchMode.KEYWORD,
        description="搜索模式: keyword, fulltext, semantic, hybrid"
    ),
    fuzzy: bool = Query(False, description="启用模糊匹配"),
    role_type: str | None = Query(None, description="按角色类型筛选"),
    school_id: int | None = Query(None, description="按院校筛选"),
    min_citations: int | None = Query(None, description="最低引用数"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Enhanced talent search with multiple modes.

    **Search Modes:**
    - `keyword`: Basic keyword matching (default, no LLM)
    - `fulltext`: PostgreSQL full-text search with GIN index
    - `semantic`: Vector similarity search using pre-computed embeddings
    - `hybrid`: Combines fulltext and semantic search

    **Filters:**
    - `role_type`: Filter by role (professor, student, etc.)
    - `school_id`: Filter by school
    - `min_citations`: Minimum citation count
    """
    start_time = time.time()

    # Validate mode
    valid_modes = [SearchMode.KEYWORD, SearchMode.FULLTEXT, SearchMode.SEMANTIC, SearchMode.HYBRID]
    if mode not in valid_modes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode. Must be one of: {valid_modes}"
        )

    # Build filters
    filters = {}
    if role_type:
        filters["role_type"] = role_type
    if school_id:
        filters["school_id"] = school_id
    if min_citations:
        filters["min_citations"] = min_citations

    try:
        # Create embedding service for semantic/hybrid search
        embed_service = None
        if mode in [SearchMode.SEMANTIC, SearchMode.HYBRID]:
            if settings.LLM_ENABLED:
                llm_gateway = create_llm_gateway()
                if llm_gateway:
                    from app.services.embedding.embedding_service import EmbeddingService
                    embed_service = EmbeddingService(
                        session=session,
                        llm_gateway=llm_gateway,
                    )

        # Create search service
        search_service = SearchService(
            session=session,
            embedding_service=embed_service,
        )

        # Execute search
        results = await search_service.search(
            query=q,
            mode=mode,
            filters=filters,
            fuzzy=fuzzy,
            page=page,
            page_size=page_size,
        )

        # Calculate elapsed time
        took_ms = (time.time() - start_time) * 1000

        # Build response - results is a SearchResult dataclass
        items = []
        for item in results.items:
            # item is a dict, not an ORM object
            items.append(SemanticSearchResult(
                talent_id=item.get("talent_id"),
                name=item.get("name"),
                name_en=item.get("name_en"),
                role_type=item.get("role_type"),
                school_name=item.get("school_name"),
                current_title=item.get("title"),
                works_count=item.get("works_count", 0),
                cited_by_count=item.get("cited_by_count", 0),
                h_index=item.get("h_index", 0),
                topic_tags=item.get("topic_tags", []),
                research_interests=item.get("research_interests"),
                similarity_score=None,
                highlight=None,
            ))

        return EnhancedSearchResponse(
            items=items,
            total=results.total,
            query=q,
            mode=mode,
            page=page,
            page_size=page_size,
            took_ms=took_ms,
        )

    except EmptyQueryError:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
