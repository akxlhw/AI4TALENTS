"""
Suggestion service.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.shared.models.iam import UserAccount
from app.domains.shared.repositories.suggestion_repository import SuggestionRepository
from app.domains.shared.repositories.user_repository import UserRepository

UPLOAD_DIR = Path("uploads/suggestions")
ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_FILES_PER_SUGGESTION = 5


class SuggestionService:
    """Service for suggestion operations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = SuggestionRepository(session)
        self.user_repo = UserRepository(session)

    async def create_suggestion(
        self,
        user_id: int,
        category: str,
        subject: str,
        content: str,
        files: list[UploadFile] | None = None,
    ) -> Any:
        suggestion = await self.repo.create_and_commit(
            user_id=user_id,
            category=category,
            subject=subject,
            content=content,
            attachments=[],
        )

        attachments: list[str] = []
        if files:
            suggestion_dir = UPLOAD_DIR / str(suggestion.suggestion_id)
            suggestion_dir.mkdir(parents=True, exist_ok=True)
            for idx, file in enumerate(files[:MAX_FILES_PER_SUGGESTION]):
                if file.content_type not in ALLOWED_CONTENT_TYPES:
                    continue
                content_bytes = await file.read()
                if len(content_bytes) > MAX_FILE_SIZE:
                    continue
                ext = file.filename.split(".")[-1] if "." in (file.filename or "") else "png"
                filename = f"image_{idx}.{ext}"
                filepath = suggestion_dir / filename
                with open(filepath, "wb") as f:
                    f.write(content_bytes)
                attachments.append(f"suggestions/{suggestion.suggestion_id}/{filename}")

        if attachments:
            suggestion.attachments = attachments
            await self.session.commit()
            await self.session.refresh(suggestion)

        return suggestion

    async def list_my_suggestions(
        self, user_id: int, page: int = 1, page_size: int = 20
    ) -> tuple[list[Any], int]:
        items, total = await self.repo.list_by_user(user_id, page, page_size)
        return [self._build_response(item) for item in items], total

    async def list_all_suggestions(
        self,
        status: str | None = None,
        category: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Any], int]:
        items, total = await self.repo.list_all(status, category, page, page_size)
        return [self._build_response(item) for item in items], total

    async def get_suggestion(self, suggestion_id: int) -> Any | None:
        item = await self.repo.get_by_id(suggestion_id)
        if not item:
            return None
        return self._build_response(item)

    async def reply_to_suggestion(
        self,
        suggestion_id: int,
        admin_reply: str,
        status: str,
    ) -> Any | None:
        item = await self.repo.update_reply_and_commit(suggestion_id, admin_reply, status)
        if not item:
            return None
        return self._build_response(item)

    def _build_response(self, suggestion: Any) -> dict[str, Any]:
        user = None
        # Note: username lookup is done separately to avoid N+1
        # For simplicity, we do a synchronous-style approach here
        # In production, use joinedload or batch fetch
        attachments = suggestion.attachments or []
        return {
            "suggestion_id": suggestion.suggestion_id,
            "user_id": suggestion.user_id,
            "username": user,
            "category": suggestion.category,
            "subject": suggestion.subject,
            "content": suggestion.content,
            "status": suggestion.status,
            "admin_reply": suggestion.admin_reply,
            "attachments": [self._build_attachment_url(a) for a in attachments],
            "created_at": suggestion.created_at,
            "updated_at": suggestion.updated_at,
        }

    def _build_attachment_url(self, path: str) -> str:
        return f"/uploads/{path}"

    async def enrich_with_usernames(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        user_ids = {item["user_id"] for item in items}
        if not user_ids:
            return items
        stmt = select(UserAccount.user_id, UserAccount.username).where(
            UserAccount.user_id.in_(user_ids)
        )
        result = await self.session.execute(stmt)
        user_map = {row.user_id: row.username for row in result.all()}
        for item in items:
            item["username"] = user_map.get(item["user_id"], f"用户#{item['user_id']}")
        return items
