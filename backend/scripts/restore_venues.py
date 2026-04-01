"""
恢复期刊配置数据脚本
从技术要素配置中恢复 Venue 和 VenueTechBinding 表

用法:
    python scripts/restore_venues.py
"""
import asyncio
import sys
import io
from pathlib import Path

# 设置UTF-8编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.tech_element import TechElement
from app.models.venue import Venue, VenueTechBinding


# 已知的 OpenAlex Source ID 映射
# 注意：这些 ID 来自 OpenAlex API，格式为 S + 数字
# 可通过 https://api.openalex.org/sources?search=CONFERENCE_NAME 验证
KNOWN_OPENALEX_SOURCES = {
    # AI/ML Top Conferences
    "neurips": "S4306420609",      # Neural Information Processing Systems
    "icml": "S4306419644",         # International Conference on Machine Learning
    "iclr": "S4306419637",         # International Conference on Learning Representations
    "cvpr": "S4363607701",         # Conference on Computer Vision and Pattern Recognition
    "eccv": "S4306418318",         # European Conference on Computer Vision
    "iccv": "S4363607764",         # International Conference on Computer Vision
    "aaai": "S4210191458",         # AAAI Conference on Artificial Intelligence
    "ijcai": "S4306419999",        # International Joint Conference on Artificial Intelligence
    "acl": "S2729999759",          # Association for Computational Linguistics
    "emnlp": "S4306418267",        # Empirical Methods in Natural Language Processing
    "naacl": "S2744807627",        # North American Chapter of the ACL
    "coling": "S2766172945",       # International Conference on Computational Linguistics

    # Systems & Architecture
    "isca": "S816455",
    "micro": "S2766169462",
    "asplos": "S2764458434",
    "sosp": "S2766317723",
    "osdi": "S2765839058",
    "sigmod": "S2748722670",
    "vldb": "S137512363",
    "icde": "S99460970",
    "sc": "S2765241720",
    "hpca": "S2765512290",
    "hotos": "S2765250776",

    # Networks & Security
    "sigcomm": "S2749120424",
    "nsdi": "S2766311384",
    "mobicom": "S99459432",
    "mobisys": "S2764955306",
    "infocom": "S2764626538",
    "ccs": "S4363608815",          # ACM Conference on Computer and Communications Security
    "usenix-sec": "S2764980276",
    "ndss": "S2765240444",
    "sp": "S27472868",

    # Graphics & Vision
    "siggraph": "S2764982680",
    "tog": "S2765307070",
    "tpami": "S2765312534",
    "tvcg": "S2765553156",

    # Journals
    "nature": "S181590659",
    "science": "S35014053",
    "tnnls": "S2765317550",
    "tits": "S2766194037",
    "tkde": "S2766213291",

    # Other AI/ML
    "kdd": "S4306420424",          # Knowledge Discovery and Data Mining
    "www": "S2766031128",
    "wsdm": "S2766041346",
    "recsys": "S2766042642",
    "icdm": "S99460372",
    "sdm": "S2765931314",

    # Robotics
    "icra": "S4210217939",         # International Conference on Robotics and Automation
    "iros": "S4363608614",         # International Conference on Intelligent Robots and Systems
    "rss": "S2766324898",
    "hri": "S2765690096",
    "corl": "S2766256584",
    "tro": "S2765319386",
    "ijrr": "S137482568",

    # Security
    "crypto": "S2764763556",
    "eurocrypt": "S2765387700",
    "asiacrypt": "S2765992576",
    "pets": "S2766102452",
    "tissec": "S2766246720",

    # Software Engineering
    "icse": "S4306419842",         # International Conference on Software Engineering
    "fse": "S99459168",
    "ase": "S99459666",
    "tse": "S2765320310",
}


# 技术要素与顶会顶刊映射数据
TECH_ELEMENTS_WITH_VENUES = [
    {
        "element_code": "ai",
        "venues": [
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
        "element_code": "robotics",
        "venues": [
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
        "element_code": "data_science",
        "venues": [
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
        "element_code": "networks",
        "venues": [
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
        "element_code": "systems",
        "venues": [
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
        "element_code": "security",
        "venues": [
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


async def restore_venues():
    """恢复期刊配置数据"""
    print("\n" + "="*60)
    print("恢复期刊配置数据")
    print("="*60)

    async with AsyncSessionLocal() as session:
        # 获取所有技术要素
        result = await session.execute(select(TechElement))
        tech_elements = {e.element_code: e for e in result.scalars().all()}

        stats = {
            "venues_created": 0,
            "bindings_created": 0,
            "errors": []
        }

        for element_data in TECH_ELEMENTS_WITH_VENUES:
            element_code = element_data["element_code"]
            venues_data = element_data["venues"]

            tech_element = tech_elements.get(element_code)
            if not tech_element:
                print(f"[WARN] 技术要素 {element_code} 不存在，跳过")
                continue

            print(f"\n[{tech_element.element_name}] 处理 {len(venues_data)} 个期刊...")

            for idx, venue_info in enumerate(venues_data):
                venue_code = venue_info["id"].lower().replace(" ", "-").replace("_", "-")
                venue_name = venue_info["name"]
                venue_type = venue_info["type"]

                # 查找 OpenAlex ID
                openalex_id = KNOWN_OPENALEX_SOURCES.get(venue_code)

                try:
                    # 检查 Venue 是否存在
                    result = await session.execute(
                        select(Venue).where(Venue.venue_code == venue_code)
                    )
                    venue = result.scalar_one_or_none()

                    if not venue:
                        # 创建新 Venue
                        venue = Venue(
                            venue_code=venue_code,
                            venue_name=venue_name,
                            venue_type=venue_type,
                            openalex_source_id=openalex_id,
                            is_enabled=True,
                        )
                        session.add(venue)
                        await session.flush()
                        stats["venues_created"] += 1
                        print(f"  [CREATE] {venue_code}: {venue_name}")
                    else:
                        print(f"  [EXISTS] {venue_code}: {venue_name}")

                    # 检查绑定是否存在
                    result = await session.execute(
                        select(VenueTechBinding).where(
                            VenueTechBinding.venue_id == venue.venue_id,
                            VenueTechBinding.tech_element_id == tech_element.tech_element_id
                        )
                    )
                    binding = result.scalar_one_or_none()

                    if not binding:
                        # 创建绑定
                        binding = VenueTechBinding(
                            venue_id=venue.venue_id,
                            tech_element_id=tech_element.tech_element_id,
                            priority=idx,
                            collect_status="pending",
                            is_enabled=True,
                        )
                        session.add(binding)
                        stats["bindings_created"] += 1

                except Exception as e:
                    stats["errors"].append(f"{venue_code}: {str(e)}")
                    print(f"  [ERROR] {venue_code}: {e}")

        await session.commit()

        print("\n" + "="*60)
        print("恢复完成!")
        print("="*60)
        print(f"  Venue 创建: {stats['venues_created']}")
        print(f"  绑定创建: {stats['bindings_created']}")
        print(f"  错误: {len(stats['errors'])}")


if __name__ == "__main__":
    asyncio.run(restore_venues())
