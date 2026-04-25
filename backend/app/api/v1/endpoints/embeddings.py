"""
Embedding generation API endpoints.
"""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import require_user
from app.core.database import get_async_session
from app.repositories.embedding_repository import EmbeddingRepository
from app.schemas.common import SuccessResponse
from app.services.config_service import ConfigService

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
    repo = EmbeddingRepository(session)
    status = await repo.get_embedding_status()

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
    batch_size: int = 100,
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

    # 检查嵌入模型配置
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

    # Count talents using repository
    repo = EmbeddingRepository(session)
    status = await repo.get_embedding_status()
    total_talents = status["total_talents"]

    if total_talents == 0:
        raise HTTPException(status_code=400, detail="No talents to process")

    # Start background task
    import asyncio
    from datetime import datetime

    _embedding_progress["status"] = "running"
    _embedding_progress["processed"] = 0
    _embedding_progress["total"] = total_talents * len(types_list)
    _embedding_progress["failed"] = 0
    _embedding_progress["started_at"] = datetime.utcnow().isoformat()
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
    _embedding_progress["completed_at"] = datetime.utcnow().isoformat()

    return SuccessResponse(message="Generation task cancelled")


async def _run_embedding_generation(force: bool, batch_size: int, vector_types: list[str]):
    """Run embedding generation in background."""
    global _embedding_progress

    from datetime import datetime

    from app.core.database import AsyncSessionLocal
    from app.services.embedding.embedding_service import EmbeddingService
    from app.services.llm import LLMGateway

    try:
        async with AsyncSessionLocal() as session:
            # Get LLM config from database
            config_service = ConfigService(session)
            llm_config = await config_service.get_llm_config()

            # 检查嵌入模型是否启用
            if not llm_config.embedding_enabled:
                _embedding_progress["status"] = "error"
                _embedding_progress["error_message"] = "嵌入模型未启用。请先启用嵌入模型功能。"
                return

            # 检查嵌入模型配置（独立配置，不复用对话模型配置）
            if not llm_config.embedding_model:
                _embedding_progress["status"] = "error"
                _embedding_progress["error_message"] = "嵌入模型名称未配置。请配置嵌入模型名称。"
                return

            if not llm_config.embedding_api_base:
                _embedding_progress["status"] = "error"
                _embedding_progress["error_message"] = (
                    "嵌入 API 地址未配置。请配置嵌入模型的 API 地址。"
                )
                return

            # Create LLM gateway with database config
            logger.info(
                f"Creating LLMGateway with embedding_api_base={llm_config.embedding_api_base}, embedding_model={llm_config.embedding_model}"
            )

            llm_gateway = LLMGateway(
                api_key=llm_config.api_key,
                api_base=llm_config.api_base,
                model=llm_config.model,
                embedding_model=llm_config.embedding_model,
                embedding_api_base=llm_config.embedding_api_base,
                embedding_api_key=llm_config.embedding_api_key,
                timeout=llm_config.timeout or 60,
                api_format=llm_config.api_format,
                embedding_api_format=llm_config.embedding_api_format,
            )

            logger.info(
                f"LLMGateway api_format={llm_gateway.api_format}, embedding_api_format={llm_gateway.embedding_api_format}"
            )

            # Get talent IDs using repository
            repo = EmbeddingRepository(session)
            talent_ids = await repo.get_visible_talent_ids()

            # 使用用户配置的嵌入模型名称
            embedding_model = llm_config.embedding_model

            _embedding_progress["total"] = len(talent_ids) * len(vector_types)

            if not talent_ids:
                _embedding_progress["status"] = "completed"
                _embedding_progress["completed_at"] = datetime.utcnow().isoformat()
                return

            # Create embedding service
            embed_service = EmbeddingService(
                session=session,
                llm_gateway=llm_gateway,
                rate_limit_delay=1.0,
                model_name=embedding_model,
            )

            # Process in batches with multiple vector types
            processed = 0
            failed = 0
            # MiniMax 有速率限制，使用较小的批次
            actual_batch_size = min(batch_size, 10)

            for i in range(0, len(talent_ids), actual_batch_size):
                if _embedding_progress["status"] == "cancelled":
                    logger.info("Embedding generation cancelled")
                    return

                batch = talent_ids[i : i + actual_batch_size]

                try:
                    stats = await embed_service.batch_generate_embeddings(
                        talent_ids=batch,
                        batch_size=actual_batch_size,
                        force_regenerate=force,
                        vector_types=vector_types,
                    )
                    processed += stats.get("processed", 0)
                    failed += stats.get("failed", 0)

                    # 实时更新进度
                    _embedding_progress["processed"] = processed
                    _embedding_progress["failed"] = failed
                    logger.info(
                        f"Progress: {processed}/{_embedding_progress['total']} processed, {failed} failed"
                    )

                except Exception as e:
                    logger.error(f"Batch {i // actual_batch_size + 1} failed: {e}")
                    failed += len(batch) * len(vector_types)
                    _embedding_progress["failed"] = failed

            # Mark as completed
            _embedding_progress["status"] = "completed"
            _embedding_progress["completed_at"] = datetime.utcnow().isoformat()

            logger.info(f"Embedding generation completed: processed={processed}, failed={failed}")

    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        _embedding_progress["status"] = "error"
        _embedding_progress["error_message"] = str(e)
        _embedding_progress["completed_at"] = datetime.utcnow().isoformat()
