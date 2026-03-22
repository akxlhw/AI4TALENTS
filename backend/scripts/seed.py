"""
Database seeding script.
Initializes the database with required initial data.
"""
import asyncio
import sys
import hashlib
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import AsyncSessionLocal
from app.models.country import Country
from app.models.iam import UserAccount, UserSchoolScope
from app.models.statistics import OverviewStatSnapshot
from app.models.enums import UserRoleType, ScopeType


def hash_password(password: str) -> str:
    """Hash password using SHA256 (for MVP, use bcrypt in production)."""
    return hashlib.sha256(password.encode()).hexdigest()


async def seed_database():
    """Seed database with initial data."""
    print("Starting database seeding...")

    async with AsyncSessionLocal() as session:
        # ============================================
        # Seed Countries
        # ============================================
        print("\nSeeding countries...")
        countries_data = [
            ("US", "美国", "United States", 1),
            ("CN", "中国", "China", 2),
            ("GB", "英国", "United Kingdom", 3),
            ("DE", "德国", "Germany", 4),
            ("JP", "日本", "Japan", 5),
            ("FR", "法国", "France", 6),
            ("CA", "加拿大", "Canada", 7),
            ("AU", "澳大利亚", "Australia", 8),
            ("SG", "新加坡", "Singapore", 9),
            ("KR", "韩国", "South Korea", 10),
            ("CH", "瑞士", "Switzerland", 11),
            ("NL", "荷兰", "Netherlands", 12),
            ("SE", "瑞典", "Sweden", 13),
            ("IT", "意大利", "Italy", 14),
            ("ES", "西班牙", "Spain", 15),
        ]

        for code, name_cn, name_en, sort_order in countries_data:
            country = Country(
                country_code=code,
                country_name_cn=name_cn,
                country_name_en=name_en,
                sort_order=sort_order,
                is_active=True,
            )
            session.add(country)

        await session.flush()
        print(f"  Seeded {len(countries_data)} countries")

        # ============================================
        # Seed Admin User
        # ============================================
        print("\nSeeding admin user...")
        admin_password = hash_password("admin123")

        admin = UserAccount(
            username="admin",
            email="admin@talent.local",
            password_hash=admin_password,
            role_type=UserRoleType.SUPER_ADMIN.value,
            is_active=True,
            status="active",
            display_name="系统管理员",
        )
        session.add(admin)
        await session.flush()

        # Grant admin access to all schools
        admin_scope = UserSchoolScope(
            user_id=admin.user_id,
            scope_type=ScopeType.ALL.value,
            scope_value="*",
            granted_by=admin.user_id,
            granted_at=datetime.now(),
            is_active=True,
        )
        session.add(admin_scope)

        print("  Admin user created (username: admin, password: admin123)")

        # ============================================
        # Seed Demo User
        # ============================================
        print("\nSeeding demo user...")
        demo_password = hash_password("demo123")

        demo = UserAccount(
            username="demo",
            email="demo@talent.local",
            password_hash=demo_password,
            role_type=UserRoleType.USER.value,
            is_active=True,
            status="active",
            display_name="演示用户",
        )
        session.add(demo)

        print("  Demo user created (username: demo, password: demo123)")

        # ============================================
        # Seed Initial Overview Snapshot
        # ============================================
        print("\nSeeding initial statistics snapshot...")
        version = f"v1.0_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        snapshot = OverviewStatSnapshot(
            stat_version=version,
            generated_at=datetime.now().isoformat(),
            school_count=0,
            professor_count=0,
            student_count=0,
            talent_count=0,
            is_active=1,
        )
        session.add(snapshot)

        print(f"  Initial snapshot created ({version})")

        # Commit all changes
        await session.commit()

        print("\n" + "="*50)
        print("Database seeding completed successfully!")
        print("="*50)
        print("\nCreated users:")
        print("  - admin / admin123 (Super Admin)")
        print("  - demo / demo123 (User)")
        print("\n Please change default passwords in production!")


if __name__ == "__main__":
    asyncio.run(seed_database())
