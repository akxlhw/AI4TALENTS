"""
Seed tech element data.
初始化技术要素和技术方向数据
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
from app.models.tech_element import TechElement, TechDirection
from app.models.talent import Talent
from app.models.country import Country


# 初始技术要素数据
TECH_ELEMENTS_DATA = [
    {
        "element_code": "ai",
        "element_name": "人工智能",
        "element_name_en": "Artificial Intelligence",
        "element_desc": "人工智能相关技术",
        "sort_order": 1,
        "directions": [
            {"direction_code": "ml", "direction_name": "机器学习", "direction_name_en": "Machine Learning"},
            {"direction_code": "dl", "direction_name": "深度学习", "direction_name_en": "Deep Learning"},
            {"direction_code": "nlp", "direction_name": "自然语言处理", "direction_name_en": "Natural Language Processing"},
            {"direction_code": "cv", "direction_name": "计算机视觉", "direction_name_en": "Computer Vision"},
            {"direction_code": "rl", "direction_name": "强化学习", "direction_name_en": "Reinforcement Learning"},
        ]
    },
    {
        "element_code": "robotics",
        "element_name": "机器人",
        "element_name_en": "Robotics",
        "element_desc": "机器人技术相关领域",
        "sort_order": 2,
        "directions": [
            {"direction_code": "robot_control", "direction_name": "机器人控制", "direction_name_en": "Robot Control"},
            {"direction_code": "human_robot", "direction_name": "人机交互", "direction_name_en": "Human-Robot Interaction"},
            {"direction_code": "autonomous", "direction_name": "自主系统", "direction_name_en": "Autonomous Systems"},
        ]
    },
    {
        "element_code": "data_science",
        "element_name": "数据科学",
        "element_name_en": "Data Science",
        "element_desc": "数据科学与分析",
        "sort_order": 3,
        "directions": [
            {"direction_code": "big_data", "direction_name": "大数据", "direction_name_en": "Big Data"},
            {"direction_code": "data_mining", "direction_name": "数据挖掘", "direction_name_en": "Data Mining"},
            {"direction_code": "visualization", "direction_name": "可视化", "direction_name_en": "Visualization"},
        ]
    },
    {
        "element_code": "networks",
        "element_name": "网络与通信",
        "element_name_en": "Networks & Communications",
        "element_desc": "计算机网络与通信技术",
        "sort_order": 4,
        "directions": [
            {"direction_code": "iot", "direction_name": "物联网", "direction_name_en": "IoT"},
            {"direction_code": "5g", "direction_name": "5G通信", "direction_name_en": "5G Communications"},
            {"direction_code": "network_security", "direction_name": "网络安全", "direction_name_en": "Network Security"},
        ]
    },
    {
        "element_code": "systems",
        "element_name": "系统与软件",
        "element_name_en": "Systems & Software",
        "element_desc": "计算机系统与软件工程",
        "sort_order": 5,
        "directions": [
            {"direction_code": "distributed", "direction_name": "分布式系统", "direction_name_en": "Distributed Systems"},
            {"direction_code": "cloud", "direction_name": "云计算", "direction_name_en": "Cloud Computing"},
            {"direction_code": "software_eng", "direction_name": "软件工程", "direction_name_en": "Software Engineering"},
        ]
    },
    {
        "element_code": "security",
        "element_name": "信息安全",
        "element_name_en": "Information Security",
        "element_desc": "信息安全与密码学",
        "sort_order": 6,
        "directions": [
            {"direction_code": "cryptography", "direction_name": "密码学", "direction_name_en": "Cryptography"},
            {"direction_code": "privacy", "direction_name": "隐私保护", "direction_name_en": "Privacy"},
            {"direction_code": "blockchain", "direction_name": "区块链", "direction_name_en": "Blockchain"},
        ]
    },
]


async def seed_tech_elements():
    """Seed tech elements and directions."""
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Check if data already exists
        result = await session.execute(select(TechElement).limit(1))
        if result.scalar_one_or_none():
            print("Tech elements already exist, skipping seed.")
            return

        # Insert tech elements and directions
        for element_data in TECH_ELEMENTS_DATA:
            directions_data = element_data.pop("directions")
            element = TechElement(**element_data)
            session.add(element)
            await session.flush()  # Get the element_id

            for dir_data in directions_data:
                direction = TechDirection(
                    **dir_data,
                    tech_element_id=element.tech_element_id
                )
                session.add(direction)

        await session.commit()
        print(f"Seeded {len(TECH_ELEMENTS_DATA)} tech elements with their directions.")


async def assign_tech_tags():
    """Assign tech tags to talents based on topic_tags."""
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Mapping of keywords to tech directions
    KEYWORD_TO_DIRECTION = {
        "machine learning": "ml",
        "deep learning": "dl",
        "neural network": "dl",
        "nlp": "nlp",
        "natural language": "nlp",
        "computer vision": "cv",
        "image": "cv",
        "robot": "robot_control",
        "autonomous": "autonomous",
        "data mining": "data_mining",
        "big data": "big_data",
        "iot": "iot",
        "internet of things": "iot",
        "security": "network_security",
        "cryptography": "cryptography",
        "privacy": "privacy",
        "blockchain": "blockchain",
        "cloud": "cloud",
        "distributed": "distributed",
        "software": "software_eng",
        "reinforcement learning": "rl",
        "artificial intelligence": "ml",
        "ai": "ml",
    }

    async with async_session() as session:
        # Get all talents
        result = await session.execute(select(Talent))
        talents = result.scalars().all()

        if not talents:
            print("No talents found to assign tags.")
            return

        # Get all tech directions
        result = await session.execute(select(TechDirection))
        directions = {d.direction_code: d for d in result.scalars().all()}

        # Get all tech elements
        result = await session.execute(select(TechElement))
        elements = {e.element_code: e for e in result.scalars().all()}

        from app.models.tech_element import TalentTechTag

        tags_added = 0
        for talent in talents:
            if not talent.topic_tags:
                continue

            # Find matching tech directions based on topic tags
            matched_directions = set()
            for tag in talent.topic_tags:
                tag_lower = tag.lower()
                for keyword, dir_code in KEYWORD_TO_DIRECTION.items():
                    if keyword in tag_lower and dir_code in directions:
                        matched_directions.add(dir_code)

            # Create tech tags
            for dir_code in matched_directions:
                direction = directions[dir_code]
                element = elements.get(direction.tech_element_id)
                if not element:
                    # Find element by querying
                    result = await session.execute(
                        select(TechElement).where(TechElement.tech_element_id == direction.tech_element_id)
                    )
                    element = result.scalar_one_or_none()

                if element:
                    tag = TalentTechTag(
                        talent_id=talent.talent_id,
                        tech_element_id=direction.tech_element_id,
                        tech_direction_id=direction.tech_direction_id,
                        tag_level="primary",
                        tag_source="auto_mapping",
                        confidence_score=0.75,
                    )
                    session.add(tag)
                    tags_added += 1

        await session.commit()
        print(f"Added {tags_added} tech tags to talents.")


async def main():
    """Main entry point."""
    print("Seeding tech elements...")
    await seed_tech_elements()

    print("\nAssigning tech tags to talents...")
    await assign_tech_tags()

    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
