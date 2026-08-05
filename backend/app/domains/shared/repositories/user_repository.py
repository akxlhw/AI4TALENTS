"""
Repository for user operations.

Aggregates per-responsibility mixins (split from the original monolith)
so the public `UserRepository` / `UserScopeRepository` interfaces stay unchanged.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.shared.repositories.user_access import AccessCheckMixin
from app.domains.shared.repositories.user_account import UserAccountMixin
from app.domains.shared.repositories.user_privacy import UserPrivacyMixin
from app.domains.shared.repositories.user_scopes import ScopeCrudMixin
from app.domains.shared.repositories.user_status import UserStatusMixin


class UserRepository(UserAccountMixin, UserStatusMixin, UserPrivacyMixin):
    """Repository for User queries and operations."""

    def __init__(self, session: AsyncSession):
        self.session = session


class UserScopeRepository(ScopeCrudMixin, AccessCheckMixin):
    """Repository for user scope operations (school/country/tech_domain)."""

    def __init__(self, session: AsyncSession):
        self.session = session
