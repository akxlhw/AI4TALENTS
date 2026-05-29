"""
Repository for user operations.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.shared.models.enums import UserRoleType
from app.domains.shared.models.iam import UserAccount, UserSchoolScope


class UserRepository:
    """Repository for User queries and operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: int) -> UserAccount | None:
        """
        Get user by ID.

        Args:
            user_id: User ID

        Returns:
            UserAccount instance or None
        """
        result = await self.session.execute(
            select(UserAccount).where(UserAccount.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> UserAccount | None:
        """
        Get user by username.

        Args:
            username: Username

        Returns:
            UserAccount instance or None
        """
        result = await self.session.execute(
            select(UserAccount).where(UserAccount.username == username)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> UserAccount | None:
        """
        Get user by email.

        Args:
            email: Email address

        Returns:
            UserAccount instance or None
        """
        result = await self.session.execute(select(UserAccount).where(UserAccount.email == email))
        return result.scalar_one_or_none()

    async def get_by_employee_id(self, employee_id: str) -> UserAccount | None:
        """
        Get user by employee ID.

        Args:
            employee_id: Employee ID (e.g., h00123456)

        Returns:
            UserAccount instance or None
        """
        result = await self.session.execute(
            select(UserAccount).where(UserAccount.employee_id == employee_id)
        )
        return result.scalar_one_or_none()

    async def get_with_scopes(self, user_id: int) -> UserAccount | None:
        """
        Get user with school scopes loaded.

        Args:
            user_id: User ID

        Returns:
            UserAccount instance with scopes or None
        """
        result = await self.session.execute(
            select(UserAccount)
            .options(selectinload(UserAccount.school_scopes))
            .where(UserAccount.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create_user(
        self,
        username: str,
        email: str,
        password_hash: str,
        role: str = UserRoleType.USER.value,
        display_name: str | None = None,
        employee_id: str | None = None,
        is_active: bool = True,
        status: str = "active",
    ) -> UserAccount:
        """
        Create a new user.

        Args:
            username: Username
            email: Email address
            password_hash: Hashed password
            role: User role
            display_name: Display name
            employee_id: Employee ID (e.g., h00123456)
            is_active: Whether the account is active
            status: Account status

        Returns:
            Created UserAccount instance
        """
        user = UserAccount(
            username=username,
            email=email,
            password_hash=password_hash,
            role_type=role,
            display_name=display_name or username,
            employee_id=employee_id,
            is_active=is_active,
            status=status,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def create_user_and_commit(
        self,
        username: str,
        email: str,
        password_hash: str,
        role: str = UserRoleType.USER.value,
        display_name: str | None = None,
        employee_id: str | None = None,
        is_active: bool = True,
        status: str = "active",
    ) -> UserAccount:
        """Create a new user and commit."""
        user = await self.create_user(
            username, email, password_hash, role, display_name, employee_id, is_active, status
        )
        await self.session.commit()
        return user

    async def update_last_login(
        self,
        user_id: int,
        ip_address: str | None = None,
    ) -> None:
        """
        Update user's last login time and IP.

        Args:
            user_id: User ID
            ip_address: Client IP address
        """
        user = await self.get_by_id(user_id)
        if user:
            user.last_login_at = datetime.now()
            user.last_login_ip = ip_address

    async def update_last_login_and_commit(
        self,
        user_id: int,
        ip_address: str | None = None,
    ) -> None:
        """Update user's last login time and IP, then commit."""
        await self.update_last_login(user_id, ip_address)
        await self.session.commit()

    async def update_password(
        self,
        user_id: int,
        new_password_hash: str,
    ) -> bool:
        """
        Update user's password.

        Args:
            user_id: User ID
            new_password_hash: New hashed password

        Returns:
            True if updated, False if user not found
        """
        user = await self.get_by_id(user_id)
        if user:
            user.password_hash = new_password_hash
            return True
        return False

    async def update_password_and_commit(
        self,
        user_id: int,
        new_password_hash: str,
    ) -> bool:
        """Update user's password and commit."""
        success = await self.update_password(user_id, new_password_hash)
        if success:
            await self.session.commit()
        return success

    async def list_users(
        self,
        role: str | None = None,
        is_active: bool | None = None,
        status: str | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[UserAccount], int]:
        """
        List users with optional filters and sorting.

        Args:
            role: Filter by role
            is_active: Filter by active status
            status: Filter by status string
            created_after: Filter by registration time >=
            created_before: Filter by registration time <=
            sort_by: Sort field ('created_at', 'last_login_at', 'username')
            sort_order: 'asc' or 'desc'
            page: Page number
            page_size: Items per page

        Returns:
            Tuple of (list of users, total count)
        """
        query = select(UserAccount)

        if role:
            query = query.where(UserAccount.role_type == role)
        if is_active is not None:
            query = query.where(UserAccount.is_active == is_active)
        if status is not None:
            query = query.where(UserAccount.status == status)
        if created_after is not None:
            query = query.where(UserAccount.created_at >= created_after)
        if created_before is not None:
            query = query.where(UserAccount.created_at <= created_before)

        # Count
        from sqlalchemy import func

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Sorting
        sort_column = {
            "created_at": UserAccount.created_at,
            "last_login_at": UserAccount.last_login_at,
            "username": UserAccount.username,
        }.get(sort_by, UserAccount.created_at)

        if sort_order.lower() == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        # Paginate
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.session.execute(query)
        users = list(result.scalars().all())

        return users, total

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


class UserScopeRepository:
    """Repository for user scope operations (school/country/tech_domain)."""

    # Valid scope types
    SCOPE_TYPES = ["school", "country", "tech_domain", "all"]

    def __init__(self, session: AsyncSession):
        self.session = session

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
            result = await self.session.execute(text("SELECT tech_domain_id FROM config_tech_domain"))
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
                result = await self.session.execute(text("SELECT tech_domain_id FROM config_tech_domain"))
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
                    text("SELECT DISTINCT country_code FROM core_school WHERE country_code IS NOT NULL")
                )
                return [row[0] for row in result.fetchall() if row[0]]

            if scope.scope_type == "country":
                if scope.scope_value and scope.scope_value != "*":
                    accessible_codes.add(scope.scope_value)

        return list(accessible_codes)

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

    async def update_user_and_commit(
        self,
        user_id: int,
        display_name: str | None = None,
        department: str | None = None,
        role: str | None = None,
        is_active: bool | None = None,
    ) -> UserAccount | None:
        """
        Update user fields and commit.

        Args:
            user_id: User ID
            display_name: Display name
            department: Department
            role: Role
            is_active: Active status

        Returns:
            Updated UserAccount or None
        """
        user = await self.get_by_id(user_id)
        if not user:
            return None

        if display_name is not None:
            user.display_name = display_name
        if department is not None:
            user.department = department
        if role is not None:
            user.role_type = role
        if is_active is not None:
            user.is_active = is_active
            user.status = "active" if is_active else "inactive"

        await self.session.commit()
        return user
