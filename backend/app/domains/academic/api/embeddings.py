"""
Embedding generation API endpoints.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_async_session
from app.domains.academic.services.embedding_domain_service import EmbeddingDomainService
from app.domains.shared.api.auth import require_user
from app.domains.shared.schemas.common import SuccessResponse
from app.domains.shared.services.config_service import ConfigService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/embeddings", tags=["Embeddings"])


def require_super_admin(current_user: dict = Depends(require_user)) -> dict:
    """Require super_admin role."""
    if current_user.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Super admin access required")
    return current_user


class EmbeddingStatusResponse(BaseModel):
    """Response for embedding status."""

    total_talents: int
    embedded_talents: int
    pending_talents: int
    last_generated: str | None
    progress_percent: float


class EmbeddingGenerateResponse(BaseModel):
    """Response for embedding generation trigger."""

    message: str
    total_talents: int
    status: str


class EmbeddingProgressResponse(BaseModel):
    """Response for embedding generation progress."""

    status: str
    processed: int
    total: int
    failed: int
    started_at: str | None
    completed_at: str | None
    error_message: str | None


# Global progress tracking (in-memory, resets on restart)
_embedding_progress = {
    "status": "idle",  # idle, running, completed, error
    "processed": 0,
    "total": 0,
    "failed": 0,
    "started_at": None,
    "completed_at": None,
    "error_message": None,
}


@router.get(
    "/status",
    response_model=EmbeddingStatusResponse,
    summary="获取向量嵌入状态",
    description="获取人才向量嵌入的生成状态",
)
async def get_embedding_status(
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_super_admin),
):
    """Get embedding generation status."""
    service = EmbeddingDomainService(session)
    status = await service.get_embedding_status()

    total_talents = status["total_talents"]
    embedded_talents = status["embedded_talents"]
    pending = max(0, total_talents - embedded_talents)
    progress = (embedded_talents / total_talents * 100) if total_talents > 0 else 0

    return EmbeddingStatusResponse(
        total_talents=total_talents,
        embedded_talents=embedded_talents,
        pending_talents=pending,
        last_generated=status["last_generated"],
        progress_percent=round(progress, 1),
    )


@router.get(
    "/progress",
    response_model=EmbeddingProgressResponse,
    summary="获取生成进度",
    description="获取当前向量生成的实时进度",
)
async def get_generation_progress(
    current_user: dict = Depends(require_super_admin),
):
    """Get current generation progress."""
    return EmbeddingProgressResponse(**_embedding_progress)


@router.post(
    "/generate",
    response_model=EmbeddingGenerateResponse,
    summary="触发生成任务",
    description="触发批量向量嵌入生成任务（后台异步执行）",
)
async def trigger_generation(
    force: bool = False,
    batch_size: int = settings.EMBEDDING_BATCH_SIZE,
    vector_types: str = "research",  # Comma-separated: "research,papers"
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_super_admin),
):
    """Trigger embedding generation task."""
    global _embedding_progress

    # Check if already running
    if _embedding_progress["status"] == "running":
        raise HTTPException(status_code=400, detail="Embedding generation is already running")

    # Check LLM configuration from database
    config_service = ConfigService(session)
    llm_config = await config_service.get_llm_config()

    if not llm_config.enabled:
        raise HTTPException(
            status_code=400, detail="LLM 功能未启用。请在系统配置中启用 LLM 并配置 API Key。"
        )

    if not llm_config.api_key:
        raise HTTPException(
            status_code=400, detail="LLM API Key 未配置。请在系统配置中设置 API Key。"
        )

    if not llm_config.embedding_model:
        raise HTTPException(
            status_code=400,
            detail="嵌入模型未配置。请在系统配置中设置嵌入模型名称（如 text-embedding-3-small, bge-m3）。",
        )

    # 检查嵌入 API 地址（API Key 可以为空，本地部署不需要）
    if not llm_config.embedding_api_base:
        raise HTTPException(
            status_code=400, detail="嵌入 API 地址未配置。请在系统配置中设置嵌入模型的 API 地址。"
        )

    # Parse vector types
    types_list = [t.strip() for t in vector_types.split(",") if t.strip()]
    valid_types = {"research", "papers"}
    for t in types_list:
        if t not in valid_types:
            raise HTTPException(
                status_code=400, detail=f"Invalid vector type: {t}. Valid types: research, papers"
            )

    # Count talents
    embed_service = EmbeddingDomainService(session)
    status = await embed_service.get_embedding_status()
    total_talents = status["total_talents"]

    if total_talents == 0:
        raise HTTPException(status_code=400, detail="No talents to process")

    # Start background task
    import asyncio
    from datetime import datetime, timezone

    _embedding_progress["status"] = "running"
    _embedding_progress["processed"] = 0
    _embedding_progress["total"] = total_talents * len(types_list)
    _embedding_progress["failed"] = 0
    _embedding_progress["started_at"] = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
    _embedding_progress["completed_at"] = None
    _embedding_progress["error_message"] = None

    asyncio.create_task(_run_embedding_generation(force, batch_size, types_list))

    logger.info(
        f"Embedding generation triggered by user {current_user.get('user_id')} for types: {types_list}"
    )

    return EmbeddingGenerateResponse(
        message=f"Embedding generation started for types: {', '.join(types_list)}",
        total_talents=total_talents,
        status="running",
    )


@router.post(
    "/cancel",
    response_model=SuccessResponse,
    summary="取消生成任务",
    description="取消正在运行的向量生成任务",
)
async def cancel_generation(
    current_user: dict = Depends(require_super_admin),
):
    """Cancel running generation task."""
    global _embedding_progress

    if _embedding_progress["status"] != "running":
        raise HTTPException(status_code=400, detail="No generation task is running")

    _embedding_progress["status"] = "cancelled"
    _embedding_progress["completed_at"] = (
        datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
    )

    return SuccessResponse(message="Generation task cancelled")


async def _run_embedding_generation(force: bool, batch_size: int, vector_types: list[str]):
    """Run embedding generation in background."""
    global _embedding_progress

    await EmbeddingDomainService.run_background_generation(
        force=force,
        batch_size=batch_size,
        vector_types=vector_types,
        progress_tracker=_embedding_progress,
    )
