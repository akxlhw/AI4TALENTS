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
from app.schemas.v1_4 import (
    JDParseRequest,
    JDFeaturesResponse,
    JDMatchRequest,
    MatchResponse,
    MatchResultItemResponse,
    MatchConfigRequest,
)
from app.services.llm import LLMGateway
from app.services.llm.errors import EmptyJDError, LLMError
from app.services.jd_match.jd_match_service import JDMatchService, MatchConfig
from app.services.config_service import ConfigService

router = APIRouter(prefix="/jd-match", tags=["JD Match"])


async def get_llm_gateway(session: AsyncSession) -> LLMGateway:
    """
    Get LLM gateway instance from database configuration.

    Raises:
        HTTPException: If LLM is disabled or not configured
    """
    config_service = ConfigService(session)
    llm_config = await config_service.get_llm_config()

    if not llm_config.enabled:
        raise HTTPException(
            status_code=503,
            detail="LLM 功能未启用。请在系统配置中启用 LLM 并配置 API Key。"
        )

    if not llm_config.api_key:
        raise HTTPException(
            status_code=503,
            detail="LLM API Key 未配置。请在系统配置中设置 API Key。"
        )

    return LLMGateway(
        api_key=llm_config.api_key,
        api_base=llm_config.api_base or "https://api.deepseek.com/v1",
        model=llm_config.model or "deepseek-chat",
        embedding_model=llm_config.embedding_model or "deepseek-embedding",
        timeout=llm_config.timeout or 60,
    )


@router.post(
    "/parse",
    response_model=JDFeaturesResponse,
    summary="解析 JD 文本",
    description="使用 LLM 解析职位描述，提取技能、经验、研究方向等关键特征",
)
async def parse_jd(
    request: JDParseRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Parse JD text and extract features.

    **Extracted Features:**
    - `skills`: Required technical skills
    - `experience`: Experience requirement
    - `research_areas`: Research area requirements
    - `role_type`: Identified role type
    - `education_level`: Education level requirement

    **Note:** This endpoint requires LLM to be enabled.
    """
    try:
        llm_gateway = await get_llm_gateway(session)

        service = JDMatchService(
            session=session,
            llm_gateway=llm_gateway,
        )

        features = await service.parse_jd(request.jd_text)

        return JDFeaturesResponse(
            skills=features.skills,
            experience=features.experience,
            research_areas=features.research_areas,
            role_type=features.role_type,
            education_level=features.education_level,
        )

    except HTTPException:
        raise
    except EmptyJDError:
        raise HTTPException(status_code=400, detail="JD 文本不能为空")
    except LLMError as e:
        raise HTTPException(status_code=502, detail=f"LLM 错误: {e.message}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
):
    """
    Match talents based on JD.

    **Process:**
    1. Parse JD text using LLM
    2. Extract required skills and research areas
    3. Search for matching talents in database
    4. Calculate match scores for each candidate
    5. Return sorted results with match reasons

    **Match Score Components:**
    - Skill score (default weight: 0.5)
    - Research score (default weight: 0.4)
    - Experience score (default weight: 0.05)
    - Education score (default weight: 0.05)

    **Note:** This endpoint requires LLM to be enabled.
    """
    start_time = time.time()

    try:
        llm_gateway = await get_llm_gateway(session)

        # Build config
        config_dict = request.config or MatchConfigRequest()
        config = MatchConfig(
            weights=config_dict.weights,
            filters=config_dict.filters,
            limit=config_dict.limit,
        )

        # Get user ID from request (if authenticated)
        user_id = 1  # Default for now, should get from auth

        # Create service
        service = JDMatchService(
            session=session,
            llm_gateway=llm_gateway,
        )

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
                skill_score=item.skill_score,
                research_score=item.research_score,
                experience_score=item.experience_score,
                match_reasons=item.match_reasons,
                highlight_skills=item.highlight_skills,
            )
            for item in result.items
        ]

        return MatchResponse(
            session_id=result.session_id,
            total=result.total,
            items=items,
            took_ms=result.took_ms,
        )

    except HTTPException:
        raise
    except EmptyJDError:
        raise HTTPException(status_code=400, detail="JD 文本不能为空")
    except LLMError as e:
        raise HTTPException(status_code=502, detail=f"LLM 错误: {e.message}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/sessions/{session_id}",
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
    # TODO: Implement session retrieval from database
    raise HTTPException(status_code=404, detail="Session not found")
