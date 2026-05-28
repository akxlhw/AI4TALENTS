"""
Suggestion API endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.shared.api.auth import require_super_admin, require_user
from app.domains.shared.schemas.common import PaginatedResponse, SuccessResponse
from app.domains.shared.schemas.suggestion import SuggestionReply
from app.domains.shared.services.suggestion_service import SuggestionService

router = APIRouter(prefix="/suggestions", tags=["Suggestions"])


@router.post("", response_model=SuccessResponse)
async def create_suggestion(
    category: str = Form(...),
    subject: str = Form(...),
    content: str = Form(...),
    files: list[UploadFile] = File(default=[]),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_user),
):
    """Create a new suggestion with optional image attachments."""
    service = SuggestionService(session)
    suggestion = await service.create_suggestion(
        user_id=int(current_user["user_id"]),
        category=category,
        subject=subject,
        content=content,
        files=files or None,
    )
    return SuccessResponse(message="建议已提交", data={"suggestion_id": suggestion.suggestion_id})


@router.get("/my", response_model=PaginatedResponse[dict])
async def list_my_suggestions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_user),
):
    """List current user's suggestions."""
    service = SuggestionService(session)
    items, total = await service.list_my_suggestions(
        user_id=int(current_user["user_id"]),
        page=page,
        page_size=page_size,
    )
    items = await service.enrich_with_usernames(items)
    return PaginatedResponse.create(items=items, total=total, page=page, page_size=page_size)


@router.get("", response_model=PaginatedResponse[dict])
async def list_all_suggestions(
    status: str | None = Query(None),
    category: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_super_admin),
):
    """List all suggestions (admin only)."""
    service = SuggestionService(session)
    items, total = await service.list_all_suggestions(
        status=status,
        category=category,
        page=page,
        page_size=page_size,
    )
    items = await service.enrich_with_usernames(items)
    return PaginatedResponse.create(items=items, total=total, page=page, page_size=page_size)


@router.get("/{suggestion_id}", response_model=dict)
async def get_suggestion(
    suggestion_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_super_admin),
):
    """Get suggestion detail (admin only)."""
    service = SuggestionService(session)
    item = await service.get_suggestion(suggestion_id)
    if item:
        items = await service.enrich_with_usernames([item])
        return items[0]
    return {"detail": "Not found"}


@router.put("/{suggestion_id}/reply", response_model=SuccessResponse)
async def reply_to_suggestion(
    suggestion_id: int,
    data: SuggestionReply,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_super_admin),
):
    """Reply to a suggestion (admin only)."""
    service = SuggestionService(session)
    item = await service.reply_to_suggestion(
        suggestion_id=suggestion_id,
        admin_reply=data.admin_reply or "",
        status=data.status,
    )
    if not item:
        return SuccessResponse(success=False, message="建议不存在")
    return SuccessResponse(message="回复已提交")
