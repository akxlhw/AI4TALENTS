"""
Create initial admin user.

Usage:
    python scripts/create_admin.py --username admin --email admin@example.com --password admin123
"""
import asyncio
import argparse
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from app.core.database import AsyncSessionLocal
from app.core.auth import hash_password
from app.domains.shared.repositories.user_repository import UserRepository
from app.domains.shared.models.enums import UserRoleType


async def create_admin_user(
    username: str,
    email: str,
    password: str,
    role: str = UserRoleType.SUPER_ADMIN.value,
):
    """Create an admin user."""
    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)

        # Check if user already exists
        existing = await repo.get_by_username(username)
        if existing:
            print(f"User '{username}' already exists!")
            return False

        existing = await repo.get_by_email(email)
        if existing:
            print(f"Email '{email}' already registered!")
            return False

        # Create user
        password_hash = hash_password(password)
        user = await repo.create_user(
            username=username,
            email=email,
            password_hash=password_hash,
            role=role,
            display_name=username,
        )

        await session.commit()
        print(f"Created user: {user.username} (ID: {user.user_id}, Role: {user.role_type})")
        return True


async def list_users():
    """List all users."""
    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        users, total = await repo.list_users(page_size=100)

        print(f"\nTotal users: {total}")
        print("-" * 60)
        for user in users:
            status = "âœ? if user.is_active else "âœ?
            print(f"  [{status}] {user.username} ({user.email}) - {user.role_type}")
        print("-" * 60)


def main():
    parser = argparse.ArgumentParser(description="Create or manage admin users")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Create user command
    create_parser = subparsers.add_parser("create", help="Create a new user")
    create_parser.add_argument("--username", required=True, help="Username")
    create_parser.add_argument("--email", required=True, help="Email address")
    create_parser.add_argument("--password", required=True, help="Password")
    create_parser.add_argument(
        "--role",
        choices=["user", "admin", "super_admin"],
        default="super_admin",
        help="User role (default: super_admin)",
    )

    # List users command
    subparsers.add_parser("list", help="List all users")

    args = parser.parse_args()

    if args.command == "create":
        asyncio.run(create_admin_user(
            username=args.username,
            email=args.email,
            password=args.password,
            role=args.role,
        ))
    elif args.command == "list":
        asyncio.run(list_users())
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
