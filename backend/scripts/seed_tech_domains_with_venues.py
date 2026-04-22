"""
Seed tech domain data with venue mappings.
初始化技术领域数据和顶会顶刊映射配置

Usage:
    python -m scripts.seed_tech_domains_with_venues
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
from app.models.tech_domain import TechDomain, TechDirection


# 技术领域与顶会顶刊映射数据
TECH_DOMAINS_WITH_VENUES = [
    {
        "domain_code": "ai",
        "domain_name": "人工智能",
        "domain_name_en": "Artificial Intelligence",
        "domain_desc": "人工智能相关技术，包括机器学习、深度学习、NLP、计算机视觉等",
        "sort_order": 1,
        "directions": [
            {"direction_code": "ml", "direction_name": "机器学习", "direction_name_en": "Machine Learning"},
            {"direction_code": "dl", "direction_name": "深度学习", "direction_name_en": "Deep Learning"},
            {"direction_code": "nlp", "direction_name": "自然语言处理", "direction_name_en": "Natural Language Processing"},
            {"direction_code": "cv", "direction_name": "计算机视觉", "direction_name_en": "Computer Vision"},
            {"direction_code": "rl", "direction_name": "强化学习", "direction_name_en": "Reinforcement Learning"},
        ],
        "collect_sources": [
            {"id": "NeurIPS", "name": "Neural Information Processing Systems", "type": "conference"},
            {"id": "ICML", "name": "International Conference on Machine Learning", "type": "conference"},
            {"id": "ICLR", "name": "International Conference on Learning Representations", "type": "conference"},
            {"id": "ACL", "name": "Annual Meeting of the Association for Computational Linguistics", "type": "conference"},
            {"id": "EMNLP", "name": "Conference on Empirical Methods in Natural Language Processing", "type": "conference"},
            {"id": "NAACL", "name": "North American Chapter of the ACL", "type": "conference"},
            {"id": "CVPR", "name": "Conference on Computer Vision and Pattern Recognition", "type": "conference"},
            {"id": "ICCV", "name": "International Conference on Computer Vision", "type": "conference"},
            {"id": "ECCV", "name": "European Conference on Computer Vision", "type": "conference"},
            {"id": "AAAI", "name": "AAAI Conference on Artificial Intelligence", "type": "conference"},
            {"id": "IJCAI", "name": "International Joint Conference on Artificial Intelligence", "type": "conference"},
            {"id": "JMLR", "name": "Journal of Machine Learning Research", "type": "journal"},
            {"id": "T-PAMI", "name": "IEEE Transactions on Pattern Analysis and Machine Intelligence", "type": "journal"},
        ]
    },
    {
        "domain_code": "robotics",
        "domain_name": "机器人",
        "domain_name_en": "Robotics",
        "domain_desc": "机器人技术相关领域，包括机器人控制、人机交互、自主系统等",
        "sort_order": 2,
        "directions": [
            {"direction_code": "robot_control", "direction_name": "机器人控制", "direction_name_en": "Robot Control"},
            {"direction_code": "human_robot", "direction_name": "人机交互", "direction_name_en": "Human-Robot Interaction"},
            {"direction_code": "autonomous", "direction_name": "自主系统", "direction_name_en": "Autonomous Systems"},
        ],
        "collect_sources": [
            {"id": "ICRA", "name": "International Conference on Robotics and Automation", "type": "conference"},
            {"id": "IROS", "name": "International Conference on Intelligent Robots and Systems", "type": "conference"},
            {"id": "RSS", "name": "Robotics: Science and Systems", "type": "conference"},
            {"id": "HRI", "name": "ACM/IEEE International Conference on Human-Robot Interaction", "type": "conference"},
            {"id": "CoRL", "name": "Conference on Robot Learning", "type": "conference"},
            {"id": "TRO", "name": "IEEE Transactions on Robotics", "type": "journal"},
            {"id": "IJRR", "name": "International Journal of Robotics Research", "type": "journal"},
        ]
    },
    {
        "domain_code": "data_science",
        "domain_name": "数据科学",
        "domain_name_en": "Data Science",
        "domain_desc": "数据科学与分析，包括大数据、数据挖掘、可视化等",
        "sort_order": 3,
        "directions": [
            {"direction_code": "big_data", "direction_name": "大数据", "direction_name_en": "Big Data"},
            {"direction_code": "data_mining", "direction_name": "数据挖掘", "direction_name_en": "Data Mining"},
            {"direction_code": "visualization", "direction_name": "可视化", "direction_name_en": "Visualization"},
        ],
        "collect_sources": [
            {"id": "KDD", "name": "ACM SIGKDD Conference on Knowledge Discovery and Data Mining", "type": "conference"},
            {"id": "SIGMOD", "name": "ACM SIGMOD International Conference on Management of Data", "type": "conference"},
            {"id": "VLDB", "name": "Very Large Data Bases Conference", "type": "conference"},
            {"id": "ICDE", "name": "International Conference on Data Engineering", "type": "conference"},
            {"id": "ICDM", "name": "IEEE International Conference on Data Mining", "type": "conference"},
            {"id": "SDM", "name": "SIAM International Conference on Data Mining", "type": "conference"},
            {"id": "VIS", "name": "IEEE Visualization Conference", "type": "conference"},
            {"id": "TVCG", "name": "IEEE Transactions on Visualization and Computer Graphics", "type": "journal"},
        ]
    },
    {
        "domain_code": "networks",
        "domain_name": "网络与通信",
        "domain_name_en": "Networks & Communications",
        "domain_desc": "计算机网络与通信技术，包括物联网、5G、网络安全等",
        "sort_order": 4,
        "directions": [
            {"direction_code": "iot", "direction_name": "物联网", "direction_name_en": "IoT"},
            {"direction_code": "5g", "direction_name": "5G通信", "direction_name_en": "5G Communications"},
            {"direction_code": "network_security", "direction_name": "网络安全", "direction_name_en": "Network Security"},
        ],
        "collect_sources": [
            {"id": "SIGCOMM", "name": "ACM SIGCOMM Conference", "type": "conference"},
            {"id": "MobiCom", "name": "ACM International Conference on Mobile Computing and Networking", "type": "conference"},
            {"id": "MobiSys", "name": "ACM International Conference on Mobile Systems", "type": "conference"},
            {"id": "SenSys", "name": "ACM Conference on Embedded Networked Sensor Systems", "type": "conference"},
            {"id": "INFOCOM", "name": "IEEE Conference on Computer Communications", "type": "conference"},
            {"id": "NSDI", "name": "Symposium on Networked Systems Design and Implementation", "type": "conference"},
            {"id": "TON", "name": "IEEE/ACM Transactions on Networking", "type": "journal"},
        ]
    },
    {
        "domain_code": "systems",
        "domain_name": "系统与软件",
        "domain_name_en": "Systems & Software",
        "domain_desc": "计算机系统与软件工程，包括分布式系统、云计算、软件工程等",
        "sort_order": 5,
        "directions": [
            {"direction_code": "distributed", "direction_name": "分布式系统", "direction_name_en": "Distributed Systems"},
            {"direction_code": "cloud", "direction_name": "云计算", "direction_name_en": "Cloud Computing"},
            {"direction_code": "software_eng", "direction_name": "软件工程", "direction_name_en": "Software Engineering"},
        ],
        "collect_sources": [
            {"id": "OSDI", "name": "USENIX Symposium on Operating Systems Design and Implementation", "type": "conference"},
            {"id": "SOSP", "name": "ACM Symposium on Operating Systems Principles", "type": "conference"},
            {"id": "ASPLOS", "name": "International Conference on Architectural Support for Programming Languages", "type": "conference"},
            {"id": "EuroSys", "name": "European Conference on Computer Systems", "type": "conference"},
            {"id": "SoCC", "name": "ACM Symposium on Cloud Computing", "type": "conference"},
            {"id": "ICSE", "name": "International Conference on Software Engineering", "type": "conference"},
            {"id": "FSE", "name": "ACM SIGSOFT International Symposium on Foundations of Software Engineering", "type": "conference"},
            {"id": "ASE", "name": "IEEE International Conference on Automated Software Engineering", "type": "conference"},
            {"id": "TSE", "name": "IEEE Transactions on Software Engineering", "type": "journal"},
        ]
    },
    {
        "domain_code": "security",
        "domain_name": "信息安全",
        "domain_name_en": "Information Security",
        "domain_desc": "信息安全与密码学，包括密码学、隐私保护、区块链等",
        "sort_order": 6,
        "directions": [
            {"direction_code": "cryptography", "direction_name": "密码学", "direction_name_en": "Cryptography"},
            {"direction_code": "privacy", "direction_name": "隐私保护", "direction_name_en": "Privacy"},
            {"direction_code": "blockchain", "direction_name": "区块链", "direction_name_en": "Blockchain"},
        ],
        "collect_sources": [
            {"id": "CCS", "name": "ACM Conference on Computer and Communications Security", "type": "conference"},
            {"id": "USENIX Security", "name": "USENIX Security Symposium", "type": "conference"},
            {"id": "NDSS", "name": "Network and Distributed System Security Symposium", "type": "conference"},
            {"id": "S&P", "name": "IEEE Symposium on Security and Privacy", "type": "conference"},
            {"id": "CRYPTO", "name": "International Cryptology Conference", "type": "conference"},
            {"id": "EUROCRYPT", "name": "European Cryptology Conference", "type": "conference"},
            {"id": "ASIACRYPT", "name": "International Conference on the Theory and Application of Cryptology", "type": "conference"},
            {"id": "PETS", "name": "Privacy Enhancing Technologies Symposium", "type": "conference"},
            {"id": "TISSEC", "name": "ACM Transactions on Information and System Security", "type": "journal"},
        ]
    },
]


async def seed_tech_domains():
    """Seed tech domains with venue mappings."""
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Check if data already exists
        result = await session.execute(select(TechDomain).limit(1))
        if result.scalar_one_or_none():
            print("Tech domains already exist. Updating with venue mappings...")

            # Update existing domains with collect_sources
            for domain_data in TECH_DOMAINS_WITH_VENUES:
                result = await session.execute(
                    select(TechDomain).where(TechDomain.domain_code == domain_data["domain_code"])
                )
                domain = result.scalar_one_or_none()
                if domain and "collect_sources" in domain_data:
                    domain.collect_sources = domain_data["collect_sources"]
                    print(f"Updated {domain.domain_name} with {len(domain_data['collect_sources'])} venues")
        else:
            # Insert new tech domains with directions and venues
            for domain_data in TECH_DOMAINS_WITH_VENUES:
                directions_data = domain_data.pop("directions")
                collect_sources = domain_data.pop("collect_sources", None)

                domain = TechDomain(**domain_data)
                domain.collect_sources = collect_sources
                session.add(domain)
                await session.flush()  # Get the domain_id

                for dir_data in directions_data:
                    direction = TechDirection(
                        **dir_data,
                        tech_domain_id=domain.tech_domain_id
                    )
                    session.add(direction)

                print(f"Created {domain.domain_name} with {len(directions_data)} directions and {len(collect_sources) if collect_sources else 0} venues")

        await session.commit()
        print("\nSeed completed successfully!")


async def main():
    """Main entry point."""
    print("Seeding tech domains with venue mappings...")
    await seed_tech_domains()


if __name__ == "__main__":
    asyncio.run(main())
