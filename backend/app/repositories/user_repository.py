"""
Repository for user operations.
"""
from typing import List, Optional
from datetime import datetime

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.iam import UserAccount, UserSchoolScope
from app.models.enums import UserRoleType


class UserRepository:
    """Repository for User queries and operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: int) -> Optional[UserAccount]:
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

    async def get_by_username(self, username: str) -> Optional[UserAccount]:
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

    async def get_by_email(self, email: str) -> Optional[UserAccount]:
        """
        Get user by email.

        Args:
            email: Email address

        Returns:
            UserAccount instance or None
        """
        result = await self.session.execute(
            select(UserAccount).where(UserAccount.email == email)
        )
        return result.scalar_one_or_none()

    async def get_with_scopes(self, user_id: int) -> Optional[UserAccount]:
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
        display_name: Optional[str] = None,
    ) -> UserAccount:
        """
        Create a new user.

        Args:
            username: Username
            email: Email address
            password_hash: Hashed password
            role: User role
            display_name: Display name

        Returns:
            Created UserAccount instance
        """
        user = UserAccount(
            username=username,
            email=email,
            password_hash=password_hash,
            role_type=role,
            display_name=display_name or username,
            is_active=True,
            status="active",
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def update_last_login(
        self,
        user_id: int,
        ip_address: Optional[str] = None,
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

    async def list_users(
        self,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[UserAccount], int]:
        """
        List users with optional filters.

        Args:
            role: Filter by role
            is_active: Filter by active status
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

        # Count
        from sqlalchemy import func
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Paginate
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size).order_by(UserAccount.user_id)

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


class UserScopeRepository:
    """Repository for user school scope operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_scopes(
        self,
        user_id: int,
        active_only: bool = True,
    ) -> List[UserSchoolScope]:
        """
        Get all school scopes for a user.

        Args:
            user_id: User ID
            active_only: Only return active scopes

        Returns:
            List of UserSchoolScope instances
        """
        query = select(UserSchoolScope).where(UserSchoolScope.user_id == user_id)

        if active_only:
            query = query.where(UserSchoolScope.is_active == True)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def add_scope(
        self,
        user_id: int,
        scope_type: str,
        scope_value: str,
        granted_by: int,
        expires_at: Optional[datetime] = None,
        notes: Optional[str] = None,
    ) -> UserSchoolScope:
        """
        Add a school scope to a user.

        Args:
            user_id: User ID
            scope_type: 'school', 'country', or 'all'
            scope_value: school_id, country_code, or '*'
            granted_by: User ID who granted the scope
            expires_at: Optional expiration date
            notes: Optional notes

        Returns:
            Created UserSchoolScope instance
        """
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
        from app.models.school import School

        user_result = await self.session.execute(
            select(UserAccount).where(UserAccount.user_id == user_id)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            return False

        # Super admin has access to all
        if user.role_type == UserRoleType.SUPER_ADMIN.value:
            return True

        # Get school to check country
        school_result = await self.session.execute(
            select(School).where(School.school_id == school_id)
        )
        school = school_result.scalar_one_or_none()

        if not school:
            return False

        # Check scopes
        scopes_result = await self.session.execute(
            select(UserSchoolScope).where(
                and_(
                    UserSchoolScope.user_id == user_id,
                    UserSchoolScope.is_active == True,
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
                # Check if school is in the country
                country_code = school.country.country_code if school.country else None
                if country_code and scope.scope_value == country_code:
                    return True

            if scope.scope_type == "school":
                if scope.scope_value == str(school_id):
                    return True

        return False

    async def get_accessible_school_ids(self, user_id: int) -> List[int]:
        """
        Get list of school IDs the user can access.

        Args:
            user_id: User ID

        Returns:
            List of accessible school IDs
        """
        from app.models.school import School

        # Get user to check role
        user_result = await self.session.execute(
            select(UserAccount).where(UserAccount.user_id == user_id)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            return []

        # Super admin has access to all
        if user.role_type == UserRoleType.SUPER_ADMIN.value:
            result = await self.session.execute(select(School.school_id))
            return [row[0] for row in result.fetchall()]

        # Get scopes
        scopes_result = await self.session.execute(
            select(UserSchoolScope).where(
                and_(
                    UserSchoolScope.user_id == user_id,
                    UserSchoolScope.is_active == True,
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
                result = await self.session.execute(select(School.school_id))
                return [row[0] for row in result.fetchall()]

            if scope.scope_type == "country":
                result = await self.session.execute(
                    select(School.school_id).where(
                        School.country.has(country_code=scope.scope_value)
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
