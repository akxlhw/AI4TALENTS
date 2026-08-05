"""
Open Source Repository - pools queries.

Split from core.py; methods are mixed into OpenSourceCoreRepository.
"""

from __future__ import annotations

from typing import Any
from typing import cast as tcast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.open_source.models.open_source import (
    OSDeveloper,
    OSPoolMember,
    OSTalentPool,
)


class PoolsMixin:
    """Talent pool and pool member operations."""

    session: AsyncSession

    async def list_talent_pools(
        self,
        user_id: int | None = None,
    ) -> list[OSTalentPool]:
        """List talent pools, optionally filtered by owner."""
        stmt = select(OSTalentPool)
        if user_id is not None:
            stmt = stmt.where(OSTalentPool.owner_user_id == user_id)
        stmt = stmt.order_by(OSTalentPool.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_talent_pool(
        self,
        pool_id: int,
    ) -> OSTalentPool | None:
        """Get talent pool by ID."""
        result = await self.session.execute(
            select(OSTalentPool).where(OSTalentPool.pool_id == pool_id)
        )
        return tcast(OSTalentPool | None, result.scalar_one_or_none())

    async def create_talent_pool(
        self,
        data: dict[str, Any],
    ) -> OSTalentPool:
        """Create a new talent pool."""
        pool = OSTalentPool(**data)
        self.session.add(pool)
        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(pool)
        return pool

    async def update_talent_pool(
        self,
        pool_id: int,
        data: dict[str, Any],
    ) -> OSTalentPool | None:
        """Update talent pool by ID."""
        pool = await self.get_talent_pool(pool_id)
        if pool is None:
            return None
        for field, value in data.items():
            setattr(pool, field, value)
        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(pool)
        return pool

    async def delete_talent_pool(
        self,
        pool_id: int,
    ) -> None:
        """Delete talent pool by ID."""
        pool = await self.get_talent_pool(pool_id)
        if pool:
            await self.session.delete(pool)
            await self.session.flush()
            await self.session.commit()

    async def get_pool_member(
        self,
        pool_id: int,
        developer_id: int,
    ) -> OSPoolMember | None:
        """Get a specific pool member."""
        result = await self.session.execute(
            select(OSPoolMember).where(
                OSPoolMember.pool_id == pool_id,
                OSPoolMember.developer_id == developer_id,
            )
        )
        return tcast(OSPoolMember | None, result.scalar_one_or_none())

    async def add_pool_member(
        self,
        pool_id: int,
        developer_id: int,
    ) -> OSPoolMember:
        """Add a developer to a talent pool."""
        member = OSPoolMember(pool_id=pool_id, developer_id=developer_id)
        self.session.add(member)
        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(member)
        return member

    async def remove_pool_member(
        self,
        member: OSPoolMember,
    ) -> None:
        """Remove a member from a talent pool."""
        await self.session.delete(member)
        await self.session.flush()
        await self.session.commit()

    async def list_pool_members(
        self,
        pool_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[OSPoolMember], int]:
        """List members of a talent pool with pagination."""
        stmt = (
            select(OSPoolMember)
            .join(OSDeveloper, OSPoolMember.developer_id == OSDeveloper.developer_id)
            .where(OSPoolMember.pool_id == pool_id)
        )
        total = await self.session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total
