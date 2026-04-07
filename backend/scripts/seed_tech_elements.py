"""
Seed tech element data.
初始化技术要素数据
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
from app.models.tech_element import TechElement


# 初始技术要素数据（6大技术要素）
TECH_ELEMENTS_DATA = [
    {
        "element_code": "ai",
        "element_name": "人工智能",
        "element_name_en": "Artificial Intelligence",
        "element_desc": "人工智能相关技术",
        "sort_order": 1,
    },
    {
        "element_code": "robotics",
        "element_name": "机器人",
        "element_name_en": "Robotics",
        "element_desc": "机器人技术相关领域",
        "sort_order": 2,
    },
    {
        "element_code": "data_science",
        "element_name": "数据科学",
        "element_name_en": "Data Science",
        "element_desc": "数据科学与分析",
        "sort_order": 3,
    },
    {
        "element_code": "networks",
        "element_name": "网络与通信",
        "element_name_en": "Networks & Communications",
        "element_desc": "计算机网络与通信技术",
        "sort_order": 4,
    },
    {
        "element_code": "systems",
        "element_name": "系统与软件",
        "element_name_en": "Systems & Software",
        "element_desc": "计算机系统与软件工程",
        "sort_order": 5,
    },
    {
        "element_code": "security",
        "element_name": "信息安全",
        "element_name_en": "Information Security",
        "element_desc": "信息安全与密码学",
        "sort_order": 6,
    },
]


async def seed_tech_elements():
    """Seed tech elements."""
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Check if data already exists
        result = await session.execute(select(TechElement).limit(1))
        if result.scalar_one_or_none():
            print("Tech elements already exist, skipping seed.")
            return

        # Insert tech elements
        for element_data in TECH_ELEMENTS_DATA:
            element = TechElement(**element_data)
            session.add(element)

        await session.commit()
        print(f"Seeded {len(TECH_ELEMENTS_DATA)} tech elements.")


async def main():
    """Main entry point."""
    print("Seeding tech elements...")
    await seed_tech_elements()
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
