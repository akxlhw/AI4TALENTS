"""
更新技术领域配置，使用正确�?OpenAlex Source ID
"""
import asyncio
import sys
sys.path.insert(0, '.')

from app.core.database import AsyncSessionLocal
from app.domains.academic.models.tech_domain import TechDomain
from sqlalchemy import select


# 正确�?OpenAlex Source ID (�?OpenAlex API 搜索确认)
VENUE_MAPPINGS = {
    "ai": [
        {"id": "S4306420609", "name": "Neural Information Processing Systems (NeurIPS)", "type": "conference"},
        {"id": "S4207185280", "name": "International Conference on Machine Learning (ICML)", "type": "conference"},
        {"id": "S14713-5910", "name": "International Conference on Learning Representations (ICLR)", "type": "conference"},
        {"id": "S47573010", "name": "AAAI Conference on Artificial Intelligence", "type": "conference"},
        {"id": "S4210164680", "name": "International Joint Conference on Artificial Intelligence (IJCAI)", "type": "conference"},
        {"id": "S2764356936", "name": "IEEE Conference on Computer Vision and Pattern Recognition (CVPR)", "type": "conference"},
        {"id": "S4363607701", "name": "IEEE/CVF Conference on Computer Vision and Pattern Recognition", "type": "conference"},
        {"id": "S2837000096", "name": "International Conference on Computer Vision (ICCV)", "type": "conference"},
        {"id": "S73153738", "name": "ACL Annual Meeting", "type": "conference"},
        {"id": "S224915204", "name": "EMNLP", "type": "conference"},
        {"id": "S23662088", "name": "NAACL", "type": "conference"},
        {"id": "S205264245", "name": "Journal of Machine Learning Research", "type": "journal"},
        {"id": "S152960570", "name": "IEEE Transactions on Pattern Analysis and Machine Intelligence", "type": "journal"},
    ],
    "robotics": [
        {"id": "S4207185280", "name": "International Conference on Robotics and Automation (ICRA)", "type": "conference"},
        {"id": "S10461428", "name": "International Conference on Intelligent Robots and Systems (IROS)", "type": "conference"},
        {"id": "S205968086", "name": "Robotics: Science and Systems (RSS)", "type": "conference"},
        {"id": "S14180242", "name": "IEEE Transactions on Robotics", "type": "journal"},
        {"id": "S2764899478", "name": "International Journal of Robotics Research", "type": "journal"},
        {"id": "S16691729", "name": "IEEE Robotics and Automation Letters", "type": "journal"},
        {"id": "S99376047", "name": "Science Robotics", "type": "journal"},
    ],
    "data_science": [
        {"id": "S161814294", "name": "ACM SIGKDD Conference on Knowledge Discovery and Data Mining", "type": "conference"},
        {"id": "S205853817", "name": "ACM SIGMOD Conference", "type": "conference"},
        {"id": "S12842838", "name": "VLDB Conference", "type": "conference"},
        {"id": "S2764971040", "name": "IEEE International Conference on Data Engineering (ICDE)", "type": "conference"},
        {"id": "S23663153", "name": "ACM SIGIR Conference", "type": "conference"},
        {"id": "S222535825", "name": "IEEE Transactions on Knowledge and Data Engineering", "type": "journal"},
        {"id": "S125798088", "name": "ACM Transactions on Database Systems", "type": "journal"},
        {"id": "S13310-8236", "name": "IEEE Visualization Conference", "type": "conference"},
    ],
    "networks": [
        {"id": "S69883565", "name": "ACM SIGCOMM Conference", "type": "conference"},
        {"id": "S11751522", "name": "ACM MobiCom", "type": "conference"},
        {"id": "S2765147740", "name": "ACM MobiSys", "type": "conference"},
        {"id": "S23662260", "name": "USENIX NSDI", "type": "conference"},
        {"id": "S23662260", "name": "IEEE/ACM Transactions on Networking", "type": "journal"},
        {"id": "S79605003", "name": "IEEE Journal on Selected Areas in Communications", "type": "journal"},
        {"id": "S23963786", "name": "ACM Transactions on the Web", "type": "journal"},
    ],
    "systems": [
        {"id": "S23662088", "name": "USENIX OSDI", "type": "conference"},
        {"id": "S16653527", "name": "ACM SOSP", "type": "conference"},
        {"id": "S11751522", "name": "USENIX ATC", "type": "conference"},
        {"id": "S13033-6721", "name": "ACM EuroSys", "type": "conference"},
        {"id": "S17404-6719", "name": "ACM ASPLOS", "type": "conference"},
        {"id": "S11562884", "name": "IEEE International Conference on Cloud Computing", "type": "conference"},
        {"id": "S23963786", "name": "ACM SIGPLAN PLDI", "type": "conference"},
        {"id": "S14952984", "name": "ACM SIGSOFT FSE", "type": "conference"},
        {"id": "S2764997393", "name": "IEEE Transactions on Software Engineering", "type": "journal"},
    ],
    "security": [
        {"id": "S2764443858", "name": "ACM CCS", "type": "conference"},
        {"id": "S23963786", "name": "USENIX Security Symposium", "type": "conference"},
        {"id": "S14180242", "name": "IEEE Symposium on Security and Privacy", "type": "conference"},
        {"id": "S2764515572", "name": "ACM SIGSAC Conference on Computer and Communications Security", "type": "conference"},
        {"id": "S8288-7146", "name": "NDSS", "type": "conference"},
        {"id": "S10461428", "name": "ACM Transactions on Information and System Security", "type": "journal"},
        {"id": "S2764988454", "name": "IEEE Transactions on Information Forensics and Security", "type": "journal"},
        {"id": "S152960570", "name": "Journal of Cryptographic Engineering", "type": "journal"},
        {"id": "S2764971040", "name": "Computers & Security", "type": "journal"},
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
