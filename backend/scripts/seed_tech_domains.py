"""
Seed tech domain data.
初始化技术领域数�?
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.core.config import settings
from app.domains.academic.models.tech_domain import TechDomain


# 初始技术领域数据（6大技术领域）
TECH_DOMAINS_DATA = [
    {
        "domain_code": "ai",
        "domain_name": "人工智能",
        "domain_name_en": "Artificial Intelligence",
        "domain_desc": "人工智能相关技�?,
        "sort_order": 1,
    },
    {
        "domain_code": "robotics",
        "domain_name": "机器�?,
        "domain_name_en": "Robotics",
        "domain_desc": "机器人技术相关领�?,
        "sort_order": 2,
    },
    {
        "domain_code": "data_science",
        "domain_name": "数据科学",
        "domain_name_en": "Data Science",
        "domain_desc": "数据科学与分�?,
        "sort_order": 3,
    },
    {
        "domain_code": "networks",
        "domain_name": "网络与通信",
        "domain_name_en": "Networks & Communications",
        "domain_desc": "计算机网络与通信技�?,
        "sort_order": 4,
    },
    {
        "domain_code": "systems",
        "domain_name": "系统与软�?,
        "domain_name_en": "Systems & Software",
        "domain_desc": "计算机系统与软件工程",
        "sort_order": 5,
    },
    {
        "domain_code": "security",
        "domain_name": "信息安全",
        "domain_name_en": "Information Security",
        "domain_desc": "信息安全与密码学",
        "sort_order": 6,
    },
]


async def seed_tech_domains():
    """Seed tech domains."""
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Check if data already exists
        result = await session.execute(select(TechDomain).limit(1))
        if result.scalar_one_or_none():
            print("Tech domains already exist, skipping seed.")
            return

        # Insert tech domains
        for domain_data in TECH_DOMAINS_DATA:
            domain = TechDomain(**domain_data)
            session.add(domain)

        await session.commit()
        print(f"Seeded {len(TECH_DOMAINS_DATA)} tech domains.")


async def main():
    """Main entry point."""
    print("Seeding tech domains...")
    await seed_tech_domains()
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
