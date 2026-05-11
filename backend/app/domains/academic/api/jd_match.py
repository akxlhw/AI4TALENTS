"""
JD Match API endpoint.
Provides JD parsing and talent matching functionality.
v1.4 Feature.
"""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.academic.schemas.v1_4 import (
    JDFeaturesResponse,
    JDMatchRequest,
    JDParseRequest,
    MatchConfigRequest,
    MatchResponse,
    MatchResultItemResponse,
)
from app.domains.academic.services.jd_match.jd_match_service import JDMatchService, MatchConfig
from app.domains.shared.api.auth import get_current_user
from app.domains.shared.services.llm.errors import EmptyJDError, LLMError

router = APIRouter(prefix="/jd-match", tags=["JD Match"])


@router.post(
    "/parse",
    response_model=JDFeaturesResponse,
    summary="解析 JD 文本",
    description="使用 LLM 解析职位描述，提取研究方向关键词（英文）",
)
async def parse_jd(
    request: JDParseRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Parse JD text and extract features.

    v1.4.1: Simplified to only extract research_areas (English keywords).

    **Extracted Features:**
    - `research_areas`: Research area requirements (English keywords)

    **Note:** This endpoint requires LLM to be enabled.
    """
    try:
        service = await JDMatchService.create_from_session(session)

        features = await service.parse_jd(request.jd_text)

        return JDFeaturesResponse(
            research_areas=features.research_areas,
        )

    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except EmptyJDError:
        raise HTTPException(status_code=400, detail="JD 文本不能为空") from None
    except LLMError as e:
        raise HTTPException(status_code=502, detail=f"LLM 错误: {e.message}") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post(
    "/match",
    response_model=MatchResponse,
    summary="岗位匹配人才",
    description="根据职位描述(JD)匹配合适的人才，返回按匹配度排序的候选人列表",
)
async def match_talents(
    request: JDMatchRequest,
    fastapi_request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict | None = Depends(get_current_user),
):
    """
    Match talents based on JD.

    v1.4.1: Simplified to only calculate research direction matching.

    **Process:**
    1. Parse JD text using LLM
    2. Extract research_areas (English keywords)
    3. Search for matching talents by:
       - Research topics (openalex_topics)
       - Paper titles (raw_work.title)
    4. Calculate match score (denominator limit: 5)
    5. Return sorted results with match reasons

    **Match Score:**
    - Research score: Based on keyword matching against topics and paper titles

    **Note:** This endpoint requires LLM to be enabled.
    """
    time.time()

    try:
        service = await JDMatchService.create_from_session(session)

        # Build config
        config_dict = request.config or MatchConfigRequest()
        config = MatchConfig(
            weights=config_dict.weights,
            filters=config_dict.filters,
            limit=config_dict.limit,
        )

        # Get user ID from authentication
        if not current_user:
            raise HTTPException(
                status_code=401, detail="用户未认证，无法创建 JD 匹配会话"
            )
        user_id = current_user["user_id"]

        # Execute match
        result = await service.match(
            jd_text=request.jd_text,
            config=config,
            user_id=user_id,
        )

        # Build response
        items = [
            MatchResultItemResponse(
                talent_id=item.talent_id,
                name=item.name,
                title=item.title,
                school_name=item.school_name,
                overall_score=item.overall_score,
                research_score=item.research_score,
                match_reasons=item.match_reasons,
            )
            for item in result.items
        ]

        return MatchResponse(
            session_id=result.session_id,
            total=result.total,
            items=items,
            took_ms=result.took_ms,
        )

    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except HTTPException:
        raise
    except EmptyJDError:
        raise HTTPException(status_code=400, detail="JD 文本不能为空") from None
    except LLMError as e:
        raise HTTPException(status_code=502, detail=f"LLM 错误: {e.message}") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get(
    "/sessions/{session_id}",
    response_model=dict,
    summary="获取匹配会话",
    description="获取历史匹配会话详情",
)
async def get_match_session(
    session_id: int,
    db_session: AsyncSession = Depends(get_async_session),
):
    """
    Get historical match session.

    Returns the JD text, parsed features, and match results for a previous session.
    """
    service = await JDMatchService.create_from_session(db_session)
    result = await service.get_session(session_id)
    if not result:
        raise HTTPException(status_code=404, detail="Session not found")
    return result
