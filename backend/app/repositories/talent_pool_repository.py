"""
Talent Pool Repository.
人才池数据访问层
"""

from __future__ import annotations

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.iam import FavoriteTalent, TalentPool, TalentPoolMember
from app.models.talent import Talent


class TalentPoolRepository:
    """Repository for talent pool operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_pool(self, user_id: int, name: str, pool_type: str = "custom", desc: str = None) -> TalentPool:
        """Create a new talent pool."""
        pool = TalentPool(
            pool_name=name,
            pool_type=pool_type,
            owner_user_id=user_id,
            scope_desc=desc,
        )
        self.session.add(pool)
        await self.session.flush()
        return pool

    async def get_pool_by_id(self, pool_id: int) -> TalentPool | None:
        """Get talent pool by ID."""
        result = await self.session.execute(
            select(TalentPool).where(TalentPool.pool_id == pool_id)
        )
        return result.scalar_one_or_none()

    async def list_user_pools(self, user_id: int) -> list[TalentPool]:
        """List all talent pools for a user."""
        result = await self.session.execute(
            select(TalentPool)
            .where(and_(
                TalentPool.owner_user_id == user_id,
                TalentPool.pool_status == 'active'
            ))
            .order_by(TalentPool.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_pool(self, pool_id: int, name: str = None, desc: str = None, status: str = None) -> TalentPool | None:
        """Update talent pool."""
        pool = await self.get_pool_by_id(pool_id)
        if not pool:
            return None
        if name:
            pool.pool_name = name
        if desc is not None:
            pool.scope_desc = desc
        if status:
            pool.pool_status = status
        await self.session.flush()
        return pool

    async def delete_pool(self, pool_id: int) -> bool:
        """Delete talent pool (soft delete by setting status to archived)."""
        pool = await self.get_pool_by_id(pool_id)
        if not pool:
            return False
        pool.pool_status = 'archived'
        await self.session.flush()
        return True

    async def add_member(self, pool_id: int, talent_id: int, added_by: int, notes: str = None) -> TalentPoolMember:
        """Add talent to pool."""
        member = TalentPoolMember(
            pool_id=pool_id,
            talent_id=talent_id,
            added_by=added_by,
            notes=notes,
        )
        self.session.add(member)
        await self.session.flush()
        return member

    async def remove_member(self, pool_id: int, talent_id: int) -> bool:
        """Remove talent from pool."""
        result = await self.session.execute(
            select(TalentPoolMember).where(and_(
                TalentPoolMember.pool_id == pool_id,
                TalentPoolMember.talent_id == talent_id
            ))
        )
        member = result.scalar_one_or_none()
        if member:
            await self.session.delete(member)
            await self.session.flush()
            return True
        return False

    async def get_pool_members(self, pool_id: int, page: int = 1, page_size: int = 20) -> tuple[list[dict], int]:
        """Get members of a talent pool with pagination."""
        # Count query
        count_result = await self.session.execute(
            select(TalentPoolMember).where(TalentPoolMember.pool_id == pool_id)
        )
        all_members = count_result.scalars().all()
        total = len(all_members)

        # Main query with talent info
        offset = (page - 1) * page_size
        result = await self.session.execute(
            select(TalentPoolMember, Talent)
            .join(Talent, TalentPoolMember.talent_id == Talent.talent_id)
            .where(TalentPoolMember.pool_id == pool_id)
            .options(selectinload(Talent.school))
            .order_by(TalentPoolMember.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )

        items = []
        for member, talent in result.all():
            items.append({
                'member_id': member.member_id,
                'pool_id': member.pool_id,
                'talent_id': talent.talent_id,
                'name': talent.name,
                'name_en': talent.name_en,
                'role_type': talent.role_type,
                'school_id': talent.school_id,
                'school_name': talent.school.school_name if talent.school else None,
                'current_title': talent.current_title,
                'works_count': talent.works_count,
                'cited_by_count': talent.cited_by_count,
                'h_index': talent.h_index,
                'notes': member.notes,
                'added_at': member.created_at.isoformat() if member.created_at else None,
            })

        return items, total

    async def is_member(self, pool_id: int, talent_id: int) -> bool:
        """Check if talent is in pool."""
        result = await self.session.execute(
            select(TalentPoolMember).where(and_(
                TalentPoolMember.pool_id == pool_id,
                TalentPoolMember.talent_id == talent_id
            ))
        )
        return result.scalar_one_or_none() is not None


class FavoriteRepository:
    """Repository for favorite operations with followup status."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def update_followup_status(self, user_id: int, talent_id: int, status: str) -> FavoriteTalent | None:
        """Update followup status for a favorite."""
        result = await self.session.execute(
            select(FavoriteTalent).where(and_(
                FavoriteTalent.user_id == user_id,
                FavoriteTalent.talent_id == talent_id,
                FavoriteTalent.is_active.is_(True)
            ))
        )
        favorite = result.scalar_one_or_none()
        if favorite:
            favorite.followup_status = status
            await self.session.flush()
        return favorite

    async def get_favorites_by_status(self, user_id: int, status: str) -> list[FavoriteTalent]:
        """Get favorites filtered by followup status."""
        result = await self.session.execute(
            select(FavoriteTalent).where(and_(
                FavoriteTalent.user_id == user_id,
                FavoriteTalent.followup_status == status,
                FavoriteTalent.is_active.is_(True)
            ))
        )
        return list(result.scalars().all())
