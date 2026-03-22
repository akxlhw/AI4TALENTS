"""
Repository for favorite talent operations.
"""
from typing import List, Optional, Tuple

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.iam import FavoriteTalent
from app.models.talent import Talent
from app.models.school import School


class FavoriteRepository:
    """Repository for FavoriteTalent queries."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_favorite(
        self, user_id: int, talent_id: int, notes: Optional[str] = None
    ) -> FavoriteTalent:
        """
        Add a talent to user's favorites.

        Args:
            user_id: User ID
            talent_id: Talent ID
            notes: Optional notes about the talent

        Returns:
            Created FavoriteTalent instance
        """
        favorite = FavoriteTalent(
            user_id=user_id,
            talent_id=talent_id,
            notes=notes,
            is_active=True,
        )
        self.session.add(favorite)
        await self.session.flush()
        await self.session.refresh(favorite)
        return favorite

    async def get_by_user_and_talent(
        self, user_id: int, talent_id: int
    ) -> Optional[FavoriteTalent]:
        """
        Get a favorite by user and talent IDs.

        Args:
            user_id: User ID
            talent_id: Talent ID

        Returns:
            FavoriteTalent instance or None
        """
        result = await self.session.execute(
            select(FavoriteTalent).where(
                and_(
                    FavoriteTalent.user_id == user_id,
                    FavoriteTalent.talent_id == talent_id,
                    FavoriteTalent.is_active == True,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, favorite_id: int) -> Optional[FavoriteTalent]:
        """
        Get a favorite by ID.

        Args:
            favorite_id: Favorite ID

        Returns:
            FavoriteTalent instance or None
        """
        result = await self.session.execute(
            select(FavoriteTalent).where(FavoriteTalent.favorite_id == favorite_id)
        )
        return result.scalar_one_or_none()

    async def list_user_favorites(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        role_type: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> Tuple[List[FavoriteTalent], int]:
        """
        Get paginated list of user's favorite talents.

        Args:
            user_id: User ID
            page: Page number (1-based)
            page_size: Items per page
            role_type: Optional filter by role type
            keyword: Optional search keyword

        Returns:
            Tuple of (list of favorites, total count)
        """
        query = (
            select(FavoriteTalent)
            .options(
                selectinload(FavoriteTalent.talent),
                selectinload(FavoriteTalent.talent).selectinload(Talent.school),
            )
            .where(
                and_(
                    FavoriteTalent.user_id == user_id,
                    FavoriteTalent.is_active == True,
                )
            )
            .order_by(FavoriteTalent.created_at.desc())
        )

        # Apply role filter
        if role_type:
            query = query.join(Talent).where(Talent.role_type == role_type)

        # Apply keyword filter
        if keyword:
            keyword_pattern = f"%{keyword}%"
            query = query.join(Talent).where(
                Talent.name.ilike(keyword_pattern)
            )

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.session.execute(query)
        favorites = list(result.scalars().all())

        return favorites, total

    async def get_user_favorite_ids(self, user_id: int) -> List[int]:
        """
        Get all talent IDs favorited by a user.

        Args:
            user_id: User ID

        Returns:
            List of talent IDs
        """
        result = await self.session.execute(
            select(FavoriteTalent.talent_id).where(
                and_(
                    FavoriteTalent.user_id == user_id,
                    FavoriteTalent.is_active == True,
                )
            )
        )
        return [row[0] for row in result.all()]

    async def update_favorite(
        self, favorite_id: int, notes: Optional[str] = None
    ) -> Optional[FavoriteTalent]:
        """
        Update a favorite's notes.

        Args:
            favorite_id: Favorite ID
            notes: New notes value

        Returns:
            Updated FavoriteTalent instance or None
        """
        favorite = await self.get_by_id(favorite_id)
        if favorite:
            favorite.notes = notes
            await self.session.flush()
            await self.session.refresh(favorite)
        return favorite

    async def remove_favorite(self, user_id: int, talent_id: int) -> bool:
        """
        Remove a talent from user's favorites (soft delete).

        Args:
            user_id: User ID
            talent_id: Talent ID

        Returns:
            True if removed, False if not found
        """
        favorite = await self.get_by_user_and_talent(user_id, talent_id)
        if favorite:
            favorite.is_active = False
            await self.session.flush()
            return True
        return False

    async def hard_remove_favorite(self, user_id: int, talent_id: int) -> bool:
        """
        Permanently remove a talent from user's favorites.

        Args:
            user_id: User ID
            talent_id: Talent ID

        Returns:
            True if removed, False if not found
        """
        favorite = await self.get_by_user_and_talent(user_id, talent_id)
        if favorite:
            await self.session.delete(favorite)
            await self.session.flush()
            return True
        return False
