"""
User Repository - user access.

Split from user_repository.py; methods are mixed into UserRepository / UserScopeRepository.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.shared.models.enums import UserRoleType
from app.domains.shared.models.iam import UserAccount, UserSchoolScope


class AccessCheckMixin:
    """User school / tech-domain / country access checks."""

    session: AsyncSession

    async def check_user_has_access(
        self,
        user_id: int,
        school_id: int,
    ) -> bool:
        """
        Check if user has access to a specific school.

        Args:
            user_id: User ID
            school_id: School ID to check

        Returns:
            True if user has access, False otherwise
        """
        # Get user to check role
        from sqlalchemy import text

        user_result = await self.session.execute(
            select(UserAccount).where(UserAccount.user_id == user_id)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            return False

        # Super admin has access to all
        if user.role_type == UserRoleType.SUPER_ADMIN.value:
            return True

        # Get school country_code directly
        school_result = await self.session.execute(
            text("SELECT country_code FROM core_school WHERE school_id = :school_id").bindparams(
                school_id=school_id
            )
        )
        row = school_result.fetchone()
        if not row:
            return False
        country_code = row[0]

        # Check scopes
        scopes_result = await self.session.execute(
            select(UserSchoolScope).where(
                and_(
                    UserSchoolScope.user_id == user_id,
                    UserSchoolScope.is_active.is_(True),
                )
            )
        )
        scopes = scopes_result.scalars().all()

        for scope in scopes:
            # Check expiration
            if scope.expires_at and scope.expires_at < datetime.now():
                continue

            if scope.scope_type == "all":
                return True

            if scope.scope_type == "country":
                if country_code and scope.scope_value == country_code:
                    return True

            if scope.scope_type == "school":
                if scope.scope_value == str(school_id):
                    return True

        return False

    async def get_accessible_school_ids(self, user_id: int) -> list[int]:
        """
        Get list of school IDs the user can access.

        Args:
            user_id: User ID

        Returns:
            List of accessible school IDs
        """
        from sqlalchemy import text

        # Get user to check role
        user_result = await self.session.execute(
            select(UserAccount).where(UserAccount.user_id == user_id)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            return []

        # Super admin has access to all
        if user.role_type == UserRoleType.SUPER_ADMIN.value:
            result = await self.session.execute(text("SELECT school_id FROM core_school"))
            return [row[0] for row in result.fetchall()]

        # Get scopes
        scopes_result = await self.session.execute(
            select(UserSchoolScope).where(
                and_(
                    UserSchoolScope.user_id == user_id,
                    UserSchoolScope.is_active.is_(True),
                )
            )
        )
        scopes = list(scopes_result.scalars().all())

        accessible_ids = set()

        for scope in scopes:
            # Check expiration
            if scope.expires_at and scope.expires_at < datetime.now():
                continue

            if scope.scope_type == "all":
                result = await self.session.execute(text("SELECT school_id FROM core_school"))
                return [row[0] for row in result.fetchall()]

            if scope.scope_type == "country":
                result = await self.session.execute(
                    text("SELECT school_id FROM core_school WHERE country_code = :code").bindparams(
                        code=scope.scope_value
                    )
                )
                for row in result.fetchall():
                    accessible_ids.add(row[0])

            if scope.scope_type == "school":
                try:
                    accessible_ids.add(int(scope.scope_value))
                except ValueError:
                    pass

        return list(accessible_ids)

    async def check_tech_domain_access(
        self,
        user_id: int,
        tech_domain_id: int,
    ) -> bool:
        """
        Check if user has access to a specific tech domain.

        Args:
            user_id: User ID
            tech_domain_id: Tech Domain ID to check

        Returns:
            True if user has access, False otherwise
        """

        # Get user to check role
        user_result = await self.session.execute(
            select(UserAccount).where(UserAccount.user_id == user_id)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            return False

        # Super admin has access to all
        if user.role_type == UserRoleType.SUPER_ADMIN.value:
            return True

        # Check scopes
        scopes_result = await self.session.execute(
            select(UserSchoolScope).where(
                and_(
                    UserSchoolScope.user_id == user_id,
                    UserSchoolScope.is_active.is_(True),
                )
            )
        )
        scopes = scopes_result.scalars().all()

        for scope in scopes:
            # Check expiration
            if scope.expires_at and scope.expires_at < datetime.now():
                continue

            if scope.scope_type == "all":
                return True

            if scope.scope_type == "tech_domain":
                if scope.scope_value == str(tech_domain_id):
                    return True

        return False

    async def get_accessible_tech_domain_ids(self, user_id: int) -> list[int]:
        """
        Get list of tech domain IDs the user can access.

        Args:
            user_id: User ID

        Returns:
            List of accessible tech domain IDs
        """
        from sqlalchemy import text

        # Get user to check role
        user_result = await self.session.execute(
            select(UserAccount).where(UserAccount.user_id == user_id)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            return []

        # Super admin has access to all
        if user.role_type == UserRoleType.SUPER_ADMIN.value:
            result = await self.session.execute(
                text("SELECT tech_domain_id FROM config_tech_domain")
            )
            return [row[0] for row in result.fetchall()]

        # Get scopes
        scopes_result = await self.session.execute(
            select(UserSchoolScope).where(
                and_(
                    UserSchoolScope.user_id == user_id,
                    UserSchoolScope.is_active.is_(True),
                )
            )
        )
        scopes = list(scopes_result.scalars().all())

        accessible_ids = set()

        for scope in scopes:
            # Check expiration
            if scope.expires_at and scope.expires_at < datetime.now():
                continue

            if scope.scope_type == "all":
                result = await self.session.execute(
                    text("SELECT tech_domain_id FROM config_tech_domain")
                )
                return [row[0] for row in result.fetchall()]

            if scope.scope_type == "tech_domain":
                try:
                    accessible_ids.add(int(scope.scope_value))
                except ValueError:
                    pass

        return list(accessible_ids)

    async def get_accessible_country_codes(self, user_id: int) -> list[str]:
        """
        Get list of country codes the user can access.

        Args:
            user_id: User ID

        Returns:
            List of accessible country codes
        """
        from sqlalchemy import text

        # Get user to check role
        user_result = await self.session.execute(
            select(UserAccount).where(UserAccount.user_id == user_id)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            return []

        # Super admin has access to all - get distinct country_codes
        if user.role_type == UserRoleType.SUPER_ADMIN.value:
            result = await self.session.execute(
                text("SELECT DISTINCT country_code FROM core_school WHERE country_code IS NOT NULL")
            )
            return [row[0] for row in result.fetchall() if row[0]]

        # Get scopes
        scopes_result = await self.session.execute(
            select(UserSchoolScope).where(
                and_(
                    UserSchoolScope.user_id == user_id,
                    UserSchoolScope.is_active.is_(True),
                )
            )
        )
        scopes = list(scopes_result.scalars().all())

        accessible_codes = set()

        for scope in scopes:
            # Check expiration
            if scope.expires_at and scope.expires_at < datetime.now():
                continue

            if scope.scope_type == "all":
                result = await self.session.execute(
                    text(
                        "SELECT DISTINCT country_code FROM core_school WHERE country_code IS NOT NULL"
                    )
                )
                return [row[0] for row in result.fetchall() if row[0]]

            if scope.scope_type == "country":
                if scope.scope_value and scope.scope_value != "*":
                    accessible_codes.add(scope.scope_value)

        return list(accessible_codes)
