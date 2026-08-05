"""
User Repository - user status.

Split from user_repository.py; methods are mixed into UserRepository / UserScopeRepository.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.shared.models.iam import UserAccount


class UserStatusMixin:
    """User activation / approval status operations."""

    session: AsyncSession

    if TYPE_CHECKING:
        # Provided by UserAccountMixin on the composed UserRepository
        async def get_by_id(self, user_id: int) -> UserAccount | None: ...

    async def deactivate_user(self, user_id: int) -> bool:
        """
        Deactivate a user account.

        Args:
            user_id: User ID

        Returns:
            True if deactivated, False if not found
        """
        user = await self.get_by_id(user_id)
        if user:
            user.is_active = False
            user.status = "inactive"
            return True
        return False

    async def deactivate_user_and_commit(self, user_id: int) -> bool:
        """Deactivate a user account and commit."""
        success = await self.deactivate_user(user_id)
        if success:
            await self.session.commit()
        return success

    async def activate_user(self, user_id: int) -> bool:
        """
        Activate a user account.

        Args:
            user_id: User ID

        Returns:
            True if activated, False if not found
        """
        user = await self.get_by_id(user_id)
        if user:
            user.is_active = True
            user.status = "active"
            return True
        return False

    async def activate_user_and_commit(self, user_id: int) -> bool:
        """Activate a user account and commit."""
        success = await self.activate_user(user_id)
        if success:
            await self.session.commit()
        return success

    async def approve_user_and_commit(self, user_id: int) -> UserAccount | None:
        """
        Approve a pending user registration.

        Args:
            user_id: User ID

        Returns:
            Updated UserAccount or None
        """
        user = await self.get_by_id(user_id)
        if not user or user.status != "pending_approval":
            return None
        user.is_active = True
        user.status = "active"
        await self.session.commit()
        return user

    async def reject_user_and_commit(self, user_id: int) -> UserAccount | None:
        """
        Reject a pending user registration.

        Args:
            user_id: User ID

        Returns:
            Updated UserAccount or None
        """
        user = await self.get_by_id(user_id)
        if not user or user.status != "pending_approval":
            return None
        user.is_active = False
        user.status = "rejected"
        await self.session.commit()
        return user
