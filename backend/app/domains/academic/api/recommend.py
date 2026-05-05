"""
Recommend API endpoint.
Provides talent recommendation functionality.
v1.4 Feature.
"""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.academic.schemas.v1_4 import (
    RecommendRequest,
    RecommendResponse,
    RecommendResultItem,
)
from app.domains.academic.services.embedding.embedding_service import EmbeddingService
from app.domains.shared.services.llm.errors import RecommendError
from app.domains.academic.services.recommend.recommend_service import RecommendService

router = APIRouter(prefix="/recommend", tags=["Recommend"])


@router.post(
    "/talents",
    response_model=RecommendResponse,
    summary="智能推荐相似人才",
    description="基于参考人才推荐研究方向和技能相似的人才",
)
async def recommend_talents(
    request: RecommendRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get talent recommendations based on reference talents.

    Finds talents with similar research interests and skills to the reference talents.

    **Reference Talents:**
    Provide 1-10 talent IDs as reference. The system will analyze their
    profiles and find matching candidates.

    **Example Request:**
    ```json
    {
        "reference_talent_ids": [1, 2, 3],
        "limit": 10,
        "filters": {"school_id": 5}
    }
    ```

    **Note:** Requires pre-computed embeddings in database.
    """
    time.time()

    # Validate reference IDs
    if not request.reference_talent_ids:
        raise HTTPException(status_code=400, detail="Reference talent IDs cannot be empty")

    try:
        # Create services
        embed_service = EmbeddingService(session=session)
        recommend_service = RecommendService(
            session=session,
            embed_service=embed_service,
        )

        # Execute recommendation
        result = await recommend_service.get_similar(
            reference_talent_ids=request.reference_talent_ids,
            limit=request.limit,
            filters=request.filters,
        )

        # Build response
        items = [
            RecommendResultItem(
                talent_id=item.talent_id,
                name=item.name,
                title=item.title,
                school_name=item.school_name,
                similarity_score=item.similarity_score,
                reasons=item.reasons,
            )
            for item in result.items
        ]

        return RecommendResponse(
            reference_talents=result.reference_talents,
            total=result.total,
            items=items,
            mode=result.mode,
            took_ms=result.took_ms,
        )

    except RecommendError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get(
    "/talents/{talent_id}/similar",
    response_model=RecommendResponse,
    summary="查找相似人才",
    description="根据单个人才快速查找相似人才",
)
async def find_similar_talents(
    talent_id: int,
    limit: int = 10,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Quick endpoint to find similar talents for a single talent.

    This is a convenience wrapper around the main recommend endpoint.
    """
    time.time()

    try:
        embed_service = EmbeddingService(session=session)
        recommend_service = RecommendService(
            session=session,
            embed_service=embed_service,
        )

        result = await recommend_service.get_similar(
            reference_talent_ids=[talent_id],
            limit=limit,
        )

        items = [
            RecommendResultItem(
                talent_id=item.talent_id,
                name=item.name,
                title=item.title,
                school_name=item.school_name,
                similarity_score=item.similarity_score,
                reasons=item.reasons,
            )
            for item in result.items
        ]

        return RecommendResponse(
            reference_talents=result.reference_talents,
            total=result.total,
            items=items,
            mode=result.mode,
            took_ms=result.took_ms,
        )

    except RecommendError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
