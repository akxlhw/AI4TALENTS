"""
Open Source — Stats, JD Match, and Embedding endpoints.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.open_source.api.auth import get_current_user, require_admin
from app.domains.open_source.schemas.open_source import (
    OSEmbeddingGenerateRequest,
    OSEmbeddingStatusResponse,
    OSJDMatchRequest,
    OSJDMatchResponse,
    OSJDMatchResultItem,
    OSStatsResponse,
)
from app.domains.open_source.services.background_state import embedding_progress
from app.domains.open_source.services.open_source_service import OpenSourceService
from app.domains.shared.schemas.common import SuccessResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/open-source", tags=["Open Source Talent"])


# ============= Stats =============


@router.get("/stats", response_model=OSStatsResponse)
async def get_stats(
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    service = OpenSourceService(session)
    stats = await service.get_stats()
    return OSStatsResponse(**stats)


# ============= JD Match =============


@router.post("/jd-match", response_model=OSJDMatchResponse)
async def jd_match(
    data: OSJDMatchRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """JD matching. Returns keyword-based candidates."""
    service = OpenSourceService(session)
    result = await service.jd_match(
        jd_text=data.jd_text,
        filters=data.filters,
        top_k=data.top_k,
    )
    # Fallback to keyword search if service returns empty
    if not result.get("matches"):
        items, _ = await service.list_developers(
            q=data.jd_text[:50],
            page=1,
            page_size=data.top_k,
        )
        results = []
        for dev in items:
            score = min(95, 50 + (dev.total_stars_received // 100))
            results.append(
                OSJDMatchResultItem(
                    developer_id=dev.developer_id,
                    github_login=dev.github_login,
                    name=dev.name,
                    avatar_url=dev.avatar_url,
                    match_score=score,
                    tech_score=score + 5,
                    activity_score=score - 5,
                    reason=f"Strong open source contributor with {dev.total_stars_received} stars",
                )
            )
        return OSJDMatchResponse(
            results=results,
            total=len(results),
            query_summary=data.jd_text[:50] + "..." if len(data.jd_text) > 50 else data.jd_text,
        )
    return OSJDMatchResponse(**result)


# ============= Embeddings =============


@router.get("/embeddings/status", response_model=OSEmbeddingStatusResponse)
async def get_embedding_status(
    session: AsyncSession = Depends(get_async_session),
    _user: dict = Depends(require_admin),
):
    service = OpenSourceService(session)
    status = await service.get_embedding_status_with_config()
    return OSEmbeddingStatusResponse(
        total_developers=status["total_developers"],
        embedded_count=status["embedded_count"],
        pending_count=status["pending_count"],
        progress_percent=status["progress_percent"],
        dimension=status["dimension"],
        model_name=status["model_name"],
    )


@router.post("/embeddings/generate")
async def generate_embeddings(
    req: OSEmbeddingGenerateRequest,
    session: AsyncSession = Depends(get_async_session),
    _user: dict = Depends(require_admin),
):
    """Trigger batch embedding generation for all visible developers."""
    if embedding_progress["status"] == "running":
        raise HTTPException(status_code=400, detail="Embedding generation is already running")

    service = OpenSourceService(session)
    total = await service.trigger_batch_embedding(batch_size=req.batch_size, force=req.force)

    dev_ids = await service.get_visible_developer_ids()
    embedding_progress["status"] = "running"
    embedding_progress["processed"] = 0
    embedding_progress["total"] = total
    embedding_progress["failed"] = 0
    embedding_progress["started_at"] = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
    embedding_progress["completed_at"] = None
    embedding_progress["error_message"] = None

    asyncio.create_task(
        OpenSourceService.run_embedding_generation_background(
            developer_ids=dev_ids,
            batch_size=req.batch_size,
            force=req.force,
            progress_dict=embedding_progress,
        )
    )

    return SuccessResponse(
        message=f"Embedding generation started for {total} developers"
    )


@router.get("/embeddings/progress")
async def get_embedding_progress(
    _user: dict = Depends(require_admin),
):
    """Get current embedding generation progress."""
    return {
        "status": embedding_progress["status"],
        "processed": embedding_progress["processed"],
        "total": embedding_progress["total"],
        "failed": embedding_progress["failed"],
        "started_at": embedding_progress["started_at"],
        "completed_at": embedding_progress["completed_at"],
        "error_message": embedding_progress["error_message"],
    }


@router.post("/embeddings/cancel")
async def cancel_embedding_generation(
    _user: dict = Depends(require_admin),
):
    """Cancel running embedding generation."""
    if embedding_progress["status"] != "running":
        raise HTTPException(status_code=400, detail="No generation task is running")

    embedding_progress["status"] = "cancelled"
    embedding_progress["completed_at"] = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()

    return SuccessResponse(message="Generation task cancelled")


@router.post("/embeddings/generate/{developer_id}")
async def generate_single_embedding(
    developer_id: int,
    session: AsyncSession = Depends(get_async_session),
    _user: dict = Depends(require_admin),
):
    service = OpenSourceService(session)
    dev = await service.get_developer(developer_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Developer not found")

    await service.generate_single_embedding(developer_id)

    return SuccessResponse(message=f"Embedding generated for developer {developer_id}")
