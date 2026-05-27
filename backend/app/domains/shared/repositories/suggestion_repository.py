"""
Suggestion repository.
"""

from __future__ import annotations

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.shared.models.suggestion import Suggestion


class SuggestionRepository:
    """Repository for suggestion queries."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_and_commit(
        self,
        user_id: int,
        category: str,
        subject: str,
        content: str,
        attachments: list[str] | None = None,
    ) -> Suggestion:
        suggestion = Suggestion(
            user_id=user_id,
            category=category,
            subject=subject,
            content=content,
            attachments=attachments or [],
        )
        self.session.add(suggestion)
        await self.session.commit()
        await self.session.refresh(suggestion)
        return suggestion

    async def get_by_id(self, suggestion_id: int) -> Suggestion | None:
        result = await self.session.execute(
            select(Suggestion).where(Suggestion.suggestion_id == suggestion_id)
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self, user_id: int, page: int = 1, page_size: int = 20
    ) -> tuple[list[Suggestion], int]:
        stmt = (
            select(Suggestion)
            .where(Suggestion.user_id == user_id)
            .order_by(desc(Suggestion.created_at))
        )
        total_result = await self.session.execute(
            select(func.count()).select_from(stmt.subquery())
        )
        total = total_result.scalar() or 0

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def list_all(
        self,
        status: str | None = None,
        category: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Suggestion], int]:
        stmt = select(Suggestion).order_by(desc(Suggestion.created_at))
        if status:
            stmt = stmt.where(Suggestion.status == status)
        if category:
            stmt = stmt.where(Suggestion.category == category)

        total_result = await self.session.execute(
            select(func.count()).select_from(stmt.subquery())
        )
        total = total_result.scalar() or 0

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def update_reply_and_commit(
        self,
        suggestion_id: int,
        admin_reply: str,
        status: str,
    ) -> Suggestion | None:
        suggestion = await self.get_by_id(suggestion_id)
        if not suggestion:
            return None
        suggestion.admin_reply = admin_reply
        suggestion.status = status
        await self.session.commit()
        await self.session.refresh(suggestion)
        return suggestion
