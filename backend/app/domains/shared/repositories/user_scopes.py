"""
User Repository - user scopes.

Split from user_repository.py; methods are mixed into UserRepository / UserScopeRepository.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.shared.models.iam import UserAccount, UserSchoolScope


class ScopeCrudMixin:
    """User scope CRUD and default-view operations."""

    session: AsyncSession

    # Valid scope types
    SCOPE_TYPES = ["school", "country", "tech_domain", "all"]

    async def get_user_scopes(
        self,
        user_id: int,
        active_only: bool = True,
        scope_type: str | None = None,
    ) -> list[UserSchoolScope]:
        """
        Get all scopes for a user.

        Args:
            user_id: User ID
            active_only: Only return active scopes
            scope_type: Filter by scope type (optional)

        Returns:
            List of UserSchoolScope instances
        """
        query = select(UserSchoolScope).where(UserSchoolScope.user_id == user_id)

        if active_only:
            query = query.where(UserSchoolScope.is_active.is_(True))

        if scope_type:
            query = query.where(UserSchoolScope.scope_type == scope_type)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def add_scope(
        self,
        user_id: int,
        scope_type: str,
        scope_value: str,
        granted_by: int,
        expires_at: datetime | None = None,
        notes: str | None = None,
    ) -> UserSchoolScope:
        """
        Add a scope to a user.

        Args:
            user_id: User ID
            scope_type: 'school', 'country', 'tech_domain', or 'all'
            scope_value: school_id, country_code, tech_domain_id, or '*'
            granted_by: User ID who granted the scope
            expires_at: Optional expiration date
            notes: Optional notes

        Returns:
            Created UserSchoolScope instance
        """
        if scope_type not in self.SCOPE_TYPES:
            raise ValueError(f"Invalid scope_type. Must be one of: {self.SCOPE_TYPES}")

        scope = UserSchoolScope(
            user_id=user_id,
            scope_type=scope_type,
            scope_value=scope_value,
            granted_by=granted_by,
            granted_at=datetime.now(),
            expires_at=expires_at,
            is_active=True,
            notes=notes,
        )
        self.session.add(scope)
        await self.session.flush()
        return scope

    async def add_scope_and_commit(
        self,
        user_id: int,
        scope_type: str,
        scope_value: str,
        granted_by: int,
        expires_at: datetime | None = None,
        notes: str | None = None,
    ) -> UserSchoolScope:
        """Add a scope to a user and commit."""
        scope = await self.add_scope(
            user_id, scope_type, scope_value, granted_by, expires_at, notes
        )
        await self.session.commit()
        return scope

    async def remove_scope(self, scope_id: int) -> bool:
        """
        Remove a school scope.

        Args:
            scope_id: Scope ID

        Returns:
            True if removed, False if not found
        """
        result = await self.session.execute(
            select(UserSchoolScope).where(UserSchoolScope.scope_id == scope_id)
        )
        scope = result.scalar_one_or_none()
        if scope:
            scope.is_active = False
            return True
        return False

    async def remove_scope_and_commit(self, scope_id: int) -> bool:
        """Remove a school scope and commit."""
        success = await self.remove_scope(scope_id)
        if success:
            await self.session.commit()
        return success

    async def get_user_default_view(self, user_id: int) -> str:
        """
        Get user's default view preference.

        Args:
            user_id: User ID

        Returns:
            Default view ('tech_domain' or 'country_school')
        """
        user_result = await self.session.execute(
            select(UserAccount).where(UserAccount.user_id == user_id)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            return "tech_domain"

        return user.default_view or "tech_domain"

    async def update_default_view_and_commit(self, user_id: int, default_view: str) -> bool:
        """
        Update user's default view preference and commit.

        Args:
            user_id: User ID
            default_view: Default view ('tech_domain' or 'country_school')

        Returns:
            True if updated, False if user not found
        """
        user_result = await self.session.execute(
            select(UserAccount).where(UserAccount.user_id == user_id)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            return False

        user.default_view = default_view
        await self.session.commit()
        return True
