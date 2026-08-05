"""
Open Source Repository - favourites queries.

Split from core.py; methods are mixed into OpenSourceCoreRepository.
"""

from __future__ import annotations

from typing import Any
from typing import cast as tcast

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.open_source.models.open_source import (
    OSDeveloper,
    OSFavourite,
)


class FavouritesMixin:
    """Favourite CRUD operations."""

    session: AsyncSession

    async def list_favourites(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        keyword: str | None = None,
    ) -> tuple[list[OSFavourite], int]:
        """List favourites for a user with optional keyword filter."""
        stmt = (
            select(OSFavourite)
            .join(OSDeveloper, OSFavourite.developer_id == OSDeveloper.developer_id)
            .where(OSFavourite.user_id == user_id, OSFavourite.is_active.is_(True))
        )

        if keyword:
            pattern = f"%{keyword}%"
            stmt = stmt.where(
                or_(
                    OSDeveloper.name.ilike(pattern),
                    OSDeveloper.github_login.ilike(pattern),
                )
            )

        total = await self.session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        stmt = (
            stmt.order_by(OSFavourite.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_favourite_ids(
        self,
        user_id: int,
    ) -> list[int]:
        """Get favourite developer IDs for a user."""
        result = await self.session.execute(
            select(OSFavourite.developer_id).where(
                OSFavourite.user_id == user_id, OSFavourite.is_active.is_(True)
            )
        )
        return list(result.scalars().all())

    async def get_favourite(
        self,
        user_id: int,
        developer_id: int,
    ) -> OSFavourite | None:
        """Get a specific favourite record."""
        result = await self.session.execute(
            select(OSFavourite).where(
                OSFavourite.user_id == user_id, OSFavourite.developer_id == developer_id
            )
        )
        return tcast(OSFavourite | None, result.scalar_one_or_none())

    async def create_favourite(
        self,
        user_id: int,
        developer_id: int,
        notes: str | None = None,
    ) -> OSFavourite:
        """Create a new favourite."""
        favourite = OSFavourite(
            user_id=user_id,
            developer_id=developer_id,
            notes=notes,
        )
        self.session.add(favourite)
        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(favourite)
        return favourite

    async def update_favourite(
        self,
        favourite: OSFavourite,
        data: dict[str, Any],
    ) -> OSFavourite:
        """Update an existing favourite."""
        for field, value in data.items():
            setattr(favourite, field, value)
        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(favourite)
        return favourite

    async def delete_favourite(
        self,
        favourite: OSFavourite,
    ) -> None:
        """Soft-delete a favourite by setting is_active=False."""
        favourite.is_active = tcast(Any, False)
        await self.session.flush()
        await self.session.commit()

    # ========== TalentPool ==========
