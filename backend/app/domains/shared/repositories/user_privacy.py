"""
User Repository - user privacy.

Split from user_repository.py; methods are mixed into UserRepository / UserScopeRepository.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from app.domains.shared.models.iam import UserAccount


class UserPrivacyMixin:
    """User privacy consent operations."""

    session: AsyncSession

    if TYPE_CHECKING:
        # Provided by UserAccountMixin on the composed UserRepository
        async def get_by_id(self, user_id: int) -> UserAccount | None: ...

    async def update_privacy_consent_and_commit(
        self,
        user_id: int,
        privacy_policy_accepted_at: datetime | None = None,
        privacy_policy_version: str | None = None,
        terms_of_use_accepted_at: datetime | None = None,
        terms_of_use_version: str | None = None,
        storage_consent_level: str | None = None,
    ) -> bool:
        """Update user privacy consent fields and commit."""
        user = await self.get_by_id(user_id)
        if not user:
            return False

        if privacy_policy_accepted_at is not None:
            user.privacy_policy_accepted_at = privacy_policy_accepted_at
        if privacy_policy_version is not None:
            user.privacy_policy_version = privacy_policy_version
        if terms_of_use_accepted_at is not None:
            user.terms_of_use_accepted_at = terms_of_use_accepted_at
        if terms_of_use_version is not None:
            user.terms_of_use_version = terms_of_use_version
        if storage_consent_level is not None:
            user.storage_consent_level = storage_consent_level

        await self.session.commit()
        return True

    async def get_privacy_consent_status(self, user_id: int) -> dict | None:
        """Get user privacy consent status."""
        user = await self.get_by_id(user_id)
        if not user:
            return None
        return {
            "privacy_policy_accepted_at": user.privacy_policy_accepted_at,
            "privacy_policy_version": user.privacy_policy_version,
            "terms_of_use_accepted_at": user.terms_of_use_accepted_at,
            "terms_of_use_version": user.terms_of_use_version,
            "storage_consent_level": user.storage_consent_level,
        }
