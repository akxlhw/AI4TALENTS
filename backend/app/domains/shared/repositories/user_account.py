"""
User Repository - user account.

Split from user_repository.py; methods are mixed into UserRepository / UserScopeRepository.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.shared.models.enums import UserRoleType
from app.domains.shared.models.iam import UserAccount


class UserAccountMixin:
    """User account query and CRUD operations."""

    session: AsyncSession

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
