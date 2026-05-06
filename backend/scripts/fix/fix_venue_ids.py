"""
更新技术领域配置，使用正确�?OpenAlex Source ID
"""
import asyncio
import sys
sys.path.insert(0, '.')

from app.core.database import AsyncSessionLocal
from app.domains.academic.models.tech_domain import TechDomain
from sqlalchemy import select
import json


# 正确�?OpenAlex Source ID (�?OpenAlex API 搜索确认)
VENUE_MAPPINGS = {
    "ai": [
        {"id": "S4306420609", "name": "Neural Information Processing Systems (NeurIPS)", "type": "conference"},
        {"id": "S4306419644", "name": "International Conference on Machine Learning (ICML)", "type": "conference"},
        {"id": "S4306419637", "name": "International Conference on Learning Representations (ICLR)", "type": "conference"},
        {"id": "S4210191458", "name": "AAAI Conference on Artificial Intelligence", "type": "conference"},
        {"id": "S4306419999", "name": "International Joint Conference on Artificial Intelligence (IJCAI)", "type": "conference"},
        {"id": "S4363607701", "name": "IEEE/CVF Conference on Computer Vision and Pattern Recognition", "type": "conference"},
        {"id": "S4306419272", "name": "International Conference on Computer Vision (ICCV)", "type": "conference"},
        {"id": "S118988714", "name": "Journal of Machine Learning Research", "type": "journal"},
        {"id": "S199944782", "name": "IEEE Transactions on Pattern Analysis and Machine Intelligence", "type": "journal"},
    ],
    "robotics": [
        {"id": "S4207185280", "name": "International Conference on Robotics and Automation (ICRA)", "type": "conference"},
        {"id": "S10461428", "name": "International Conference on Intelligent Robots and Systems (IROS)", "type": "conference"},
        {"id": "S205968086", "name": "Robotics: Science and Systems (RSS)", "type": "conference"},
        {"id": "S14180242", "name": "IEEE Transactions on Robotics", "type": "journal"},
        {"id": "S2764899478", "name": "International Journal of Robotics Research", "type": "journal"},
    ],
    "data_science": [
        {"id": "S161814294", "name": "ACM SIGKDD Conference on Knowledge Discovery and Data Mining", "type": "conference"},
        {"id": "S205853817", "name": "ACM SIGMOD Conference", "type": "conference"},
        {"id": "S12842838", "name": "VLDB Conference", "type": "conference"},
        {"id": "S222535825", "name": "IEEE Transactions on Knowledge and Data Engineering", "type": "journal"},
    ],
    "networks": [
        {"id": "S69883565", "name": "ACM SIGCOMM Conference", "type": "conference"},
        {"id": "S11751522", "name": "ACM MobiCom", "type": "conference"},
        {"id": "S79605003", "name": "IEEE Journal on Selected Areas in Communications", "type": "journal"},
    ],
    "systems": [
        {"id": "S23662088", "name": "USENIX OSDI", "type": "conference"},
        {"id": "S16653527", "name": "ACM SOSP", "type": "conference"},
        {"id": "S2764997393", "name": "IEEE Transactions on Software Engineering", "type": "journal"},
    ],
    "security": [
        {"id": "S4363608815", "name": "ACM SIGSAC Conference on Computer and Communications Security (CCS)", "type": "conference"},
        {"id": "S4306421123", "name": "USENIX Security Symposium", "type": "conference"},
        {"id": "S4210233669", "name": "IEEE Symposium on Security and Privacy (S&P)", "type": "conference"},
        {"id": "S61310614", "name": "IEEE Transactions on Information Forensics and Security", "type": "journal"},
    ],
}


async def update_venues():
    async with AsyncSessionLocal() as session:
        for domain_code, venues in VENUE_MAPPINGS.items():
            result = await session.execute(
                select(TechDomain).where(TechDomain.domain_code == domain_code)
            )
            domain = result.scalar_one_or_none()

            if domain:
                domain.collect_sources = venues
                print(f"Updated {domain.domain_name} with {len(venues)} venues")
            else:
                print(f"Tech domain '{domain_code}' not found")

        await session.commit()
        print("\nAll venues updated!")


if __name__ == "__main__":
    asyncio.run(update_venues())
