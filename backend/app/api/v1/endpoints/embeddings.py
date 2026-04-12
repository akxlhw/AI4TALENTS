"""
Embedding generation API endpoints.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import require_user
from app.core.database import get_async_session
from app.models.talent import Talent
from app.models.embedding import TalentEmbedding

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
    last_generated: Optional[str]
    progress_percent: float


class EmbeddingGenerateResponse(BaseModel):
    """Response for embedding generation trigger."""
    message: str
    total_talents: int
    status: str


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
    description="获取人才向量嵌入的生成状态"
)
async def get_embedding_status(
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_super_admin),
):
    """Get embedding generation status."""
    # Count total visible talents
    total_result = await session.execute(
        select(func.count()).select_from(Talent).where(Talent.is_visible == True)
    )
    total_talents = total_result.scalar() or 0

    # Count talents with embeddings
    embedded_result = await session.execute(
        select(func.count()).select_from(TalentEmbedding)
    )
    embedded_talents = embedded_result.scalar() or 0

    # Get last embedding creation time
    last_result = await session.execute(
        select(TalentEmbedding.created_at)
        .order_by(TalentEmbedding.created_at.desc())
        .limit(1)
    )
    last_row = last_result.scalar_one_or_none()
    last_generated = last_row.isoformat() if last_row else None

    pending = max(0, total_talents - embedded_talents)
    progress = (embedded_talents / total_talents * 100) if total_talents > 0 else 0

    return EmbeddingStatusResponse(
        total_talents=total_talents,
        embedded_talents=embedded_talents,
        pending_talents=pending,
        last_generated=last_generated,
        progress_percent=round(progress, 1),
    )


@router.get(
    "/progress",
    summary="获取生成进度",
    description="获取当前向量生成的实时进度"
)
async def get_generation_progress(
    current_user: dict = Depends(require_super_admin),
):
    """Get current generation progress."""
    return _embedding_progress


@router.post(
    "/generate",
    response_model=EmbeddingGenerateResponse,
    summary="触发生成任务",
    description="触发批量向量嵌入生成任务（后台异步执行）"
)
async def trigger_generation(
    force: bool = False,
    batch_size: int = 100,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_super_admin),
):
    """Trigger embedding generation task."""
    global _embedding_progress

    # Check if already running
    if _embedding_progress["status"] == "running":
        raise HTTPException(
            status_code=400,
            detail="Embedding generation is already running"
        )

    # Check LLM configuration
    from app.core.config import settings
    if not settings.LLM_ENABLED:
        raise HTTPException(
            status_code=400,
            detail="LLM is not enabled. Please configure LLM settings first."
        )

    # Count talents
    total_result = await session.execute(
        select(func.count()).select_from(Talent).where(Talent.is_visible == True)
    )
    total_talents = total_result.scalar() or 0

    if total_talents == 0:
        raise HTTPException(
            status_code=400,
            detail="No talents to process"
        )

    # Start background task
    import asyncio
    from datetime import datetime

    _embedding_progress["status"] = "running"
    _embedding_progress["processed"] = 0
    _embedding_progress["total"] = total_talents
    _embedding_progress["failed"] = 0
    _embedding_progress["started_at"] = datetime.utcnow().isoformat()
    _embedding_progress["completed_at"] = None
    _embedding_progress["error_message"] = None

    asyncio.create_task(_run_embedding_generation(force, batch_size))

    logger.info(f"Embedding generation triggered by user {current_user.get('user_id')}")

    return EmbeddingGenerateResponse(
        message="Embedding generation started",
        total_talents=total_talents,
        status="running",
    )


@router.post(
    "/cancel",
    summary="取消生成任务",
    description="取消正在运行的向量生成任务"
)
async def cancel_generation(
    current_user: dict = Depends(require_super_admin),
):
    """Cancel running generation task."""
    global _embedding_progress

    if _embedding_progress["status"] != "running":
        raise HTTPException(
            status_code=400,
            detail="No generation task is running"
        )

    _embedding_progress["status"] = "cancelled"
    _embedding_progress["completed_at"] = datetime.utcnow().isoformat()

    return {"message": "Generation task cancelled"}


async def _run_embedding_generation(force: bool, batch_size: int):
    """Run embedding generation in background."""
    global _embedding_progress

    from datetime import datetime
    from app.core.database import AsyncSessionLocal
    from app.services.llm import create_llm_gateway
    from app.services.embedding.embedding_service import EmbeddingService

    try:
        llm_gateway = create_llm_gateway()
        if not llm_gateway:
            _embedding_progress["status"] = "error"
            _embedding_progress["error_message"] = "Failed to create LLM gateway"
            return

        async with AsyncSessionLocal() as session:
            # Get talent IDs
            query = select(Talent.talent_id).where(
                Talent.is_visible == True
            ).order_by(Talent.talent_id)

            result = await session.execute(query)
            talent_ids = [row[0] for row in result.fetchall()]

            if not force:
                # Exclude already embedded talents
                from app.repositories.embedding_repository import EmbeddingRepository
                repo = EmbeddingRepository(session)
                existing_ids = await repo.get_existing_talent_ids()
                talent_ids = [tid for tid in talent_ids if tid not in existing_ids]

            _embedding_progress["total"] = len(talent_ids)

            if not talent_ids:
                _embedding_progress["status"] = "completed"
                _embedding_progress["completed_at"] = datetime.utcnow().isoformat()
                return

            # Create embedding service
            embed_service = EmbeddingService(
                session=session,
                llm_gateway=llm_gateway,
                rate_limit_delay=1.0,
            )

            # Process in batches
            processed = 0
            failed = 0

            for i in range(0, len(talent_ids), batch_size):
                if _embedding_progress["status"] == "cancelled":
                    logger.info("Embedding generation cancelled")
                    return

                batch = talent_ids[i:i + batch_size]

                try:
                    stats = await embed_service.batch_generate_embeddings(
                        talent_ids=batch,
                        batch_size=batch_size,
                        force_regenerate=False,
                    )
                    processed += stats.get("processed", 0)
                    failed += stats.get("failed", 0)

                    _embedding_progress["processed"] = processed
                    _embedding_progress["failed"] = failed

                    await session.commit()

                except Exception as e:
                    logger.error(f"Batch {i // batch_size + 1} failed: {e}")
                    failed += len(batch)
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
