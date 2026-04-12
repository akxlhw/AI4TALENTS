"""
一键初始化系统数据脚本

功能：
1. 清空所有业务数据表
2. 重新运行数据库迁移
3. 初始化基础数据（管理员、技术要素）

使用方法：
    python scripts/init_system.py              # 交互式确认
    python scripts/init_system.py --force      # 跳过确认
    python scripts/init_system.py --keep-users # 保留用户数据
"""
import asyncio
import sys
import argparse
import io
from datetime import datetime
from pathlib import Path

# 设置标准输出为UTF-8编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from app.core.database import AsyncSessionLocal
from app.core.auth import hash_password
from app.models.enums import UserRoleType, ScopeType
from app.models.iam import UserAccount, UserSchoolScope
from app.models.tech_element import TechElement
from app.models.statistics import OverviewStatSnapshot
from app.models.venue import Venue, VenueTechBinding

# 业务数据表（清空这些表）
BUSINESS_TABLES = [
    # 搜索和审计
    "search_talent_document",
    "audit_operation_log",
    # 人才相关
    "core_talent_tech_tag",
    "core_selected_work",
    "core_role_profile",
    "core_talent",
    "core_talent_embedding",  # v1.4 向量嵌入
    # 学校相关
    "core_school_alias",
    "core_school",
    # 合作网络
    "core_work_author",
    "core_collaboration",
    # 收藏和人才池
    "iam_talent_pool_member",
    "iam_favorite_talent",
    "iam_talent_pool",
    # 标准化层
    "std_school_alias",
    "std_author",
    "std_school",
    # 原始数据层
    "rel_author_tech_belong",
    "raw_work",
    "raw_author",
    "raw_institution",
    # 采集任务
    "sync_venue_sub_task",
    "sync_collect_task",
    # 统计快照
    "stat_school_snapshot",
    "stat_overview_snapshot",
    # 数据版本
    "data_quality_summary",
    "data_correction_record",
    "data_publish_record",
    "data_version",
    # JD 匹配 (v1.4)
    "jd_match_result",
    "jd_match_session",
    # 系统配置 (v1.4)
    "sys_config",
]

# 基础配置表（仅在 --full 时清空）
# 注意：期刊配置(config_venue, config_venue_tech_binding)永不清空，需要保留
CONFIG_TABLES = [
    "iam_user_school_scope",
    "core_tech_element",
    "iam_user_account",
]

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


# 已知的 OpenAlex Source ID 映射
KNOWN_OPENALEX_SOURCES = {
    # AI/ML Top Conferences
    "neurips": "S4306420609",
    "icml": "S4306419644",
    "iclr": "S4306419637",
    "cvpr": "S4363607701",
    "eccv": "S4306418318",
    "iccv": "S4363607764",
    "aaai": "S4210191458",
    "ijcai": "S4306419999",
    "acl": "S2729999759",
    "emnlp": "S4306418267",
    "naacl": "S2744807627",
    "coling": "S2766172945",
    # AI/ML Journals
    "jmlr": "S118988714",
    "t-pami": "S199944782",
    # Systems & Architecture
    "isca": "S816455",
    "micro": "S2766169462",
    "asplos": "S2764458434",
    "sosp": "S2766317723",
    "osdi": "S2765839058",
    "eurosys": "S4306418317",
    "socc": "S4306420965",
    # Data & Databases
    "sigmod": "S47508943",
    "vldb": "S4210226185",
    "icde": "S99460970",
    "sc": "S2765241720",
    "hpca": "S2765512290",
    "hotos": "S2765250776",
    # Networks
    "sigcomm": "S66039016",
    "nsdi": "S2766311384",
    "mobicom": "S99459432",
    "mobisys": "S2764955306",
    "infocom": "S4363607980",
    "ton": "S62238642",
    "sensys": "S4306419422",
    # Security
    "ccs": "S4363608815",
    "usenix-security": "S4306421123",
    "ndss": "S2765240444",
    "s&p": "S4363606603",
    "crypto": "S4387289975",
    "eurocrypt": "S2765387700",
    "asiacrypt": "S2765992576",
    "pets": "S4210183172",
    "tissec": "S2642811",
    # Graphics & Vision
    "siggraph": "S2764982680",
    "tog": "S2765307070",
    "tvcg": "S84775595",
    "vis": "S4306418842",
    # Other AI/ML
    "kdd": "S4306420424",
    "www": "S2766031128",
    "wsdm": "S2766041346",
    "recsys": "S2766042642",
    "icdm": "S4363608061",
    "sdm": "S4306420871",
    # Robotics
    "icra": "S4210217939",
    "iros": "S4363608614",
    "rss": "S2766324898",
    "hri": "S2765690096",
    "corl": "S2766256584",
    "tro": "S2765319386",
    "ijrr": "S73484101",
    # Software Engineering
    "icse": "S4306419842",
    "fse": "S4363608883",
    "ase": "S4210177399",
    "tse": "S8351582",
    # Journals
    "nature": "S181590659",
    "science": "S35014053",
    "tnnls": "S2765317550",
    "tits": "S2766194037",
    "tkde": "S2766213291",
}

# 技术要素与顶会顶刊映射数据
VENUE_DATA = [
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


async def truncate_tables(full_reset: bool = False):
    """清空业务数据表

    Args:
        full_reset: 是否同时清空基础配置表（用户、技术要素等）
    """
    print("\n" + "="*60)
    print("Step 1: 清空数据表")
    print("="*60)

    async with AsyncSessionLocal() as session:
        # 默认只清空业务数据表
        tables = BUSINESS_TABLES.copy()

        if full_reset:
            # 全量重置，同时清空配置表
            tables.extend(CONFIG_TABLES)
            print("  [模式: 全量重置]")

        # 使用 TRUNCATE CASCADE 来强制清空，忽略外键约束
        # 需要按依赖关系逆序处理，或者一次性 TRUNCATE 所有表
        if tables:
            try:
                # 构建单个 TRUNCATE 语句，CASCADE 会自动处理外键
                table_list = ", ".join(tables)
                await session.execute(text(f"TRUNCATE TABLE {table_list} CASCADE"))
                await session.commit()
                print(f"  [OK] 已清空 {len(tables)} 个表 (CASCADE)")
            except Exception as e:
                error_msg = str(e)
                # 如果 TRUNCATE 失败，尝试逐个删除
                print(f"  [WARN] TRUNCATE 失败: {error_msg[:100]}...")
                print("  [INFO] 尝试逐个处理...")

                # 先禁用外键检查（PostgreSQL）
                await session.execute(text("SET session_replication_role = 'replica'"))

                truncated_count = 0
                for table in tables:
                    try:
                        await session.execute(text(f"DELETE FROM {table}"))
                        truncated_count += 1
                        print(f"  [OK] {table}")
                    except Exception as e2:
                        error_msg = str(e2)
                        if "does not exist" in error_msg or "不存在" in error_msg:
                            print(f"  [SKIP] {table} (不存在)")
                        else:
                            print(f"  [WARN] {table}: {error_msg[:50]}...")
                        continue

                # 重新启用外键检查
                await session.execute(text("SET session_replication_role = 'origin'"))
                await session.commit()
                print(f"\n已清空 {truncated_count} 个表")


async def clear_cache():
    """清空 Redis 缓存"""
    print("\n" + "="*60)
    print("Step 2: 清空缓存")
    print("="*60)

    try:
        from app.core.cache import get_cache_connection
        from app.services.cache_service import CacheService

        cache_conn = await get_cache_connection()
        if cache_conn.is_available:
            cache = CacheService(cache_conn)
            deleted = await cache.delete_pattern("*")
            print(f"  [OK] 已清空 {deleted} 个缓存键")
        else:
            print("  [SKIP] Redis 未启用或不可用")
    except Exception as e:
        print(f"  [WARN] 缓存清理失败: {e}")


async def seed_admin_user():
    """初始化管理员用户"""
    print("\n" + "="*60)
    print("Step 3: 初始化管理员用户")
    print("="*60)

    async with AsyncSessionLocal() as session:
        # 检查是否已存在
        from sqlalchemy import select
        result = await session.execute(
            select(UserAccount).where(UserAccount.username == "admin")
        )
        if result.scalar_one_or_none():
            print("  管理员用户已存在，跳过创建")
            return

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

        # 授予全部学校访问权限
        admin_scope = UserSchoolScope(
            user_id=admin.user_id,
            scope_type=ScopeType.ALL.value,
            scope_value="*",
            granted_by=admin.user_id,
            granted_at=datetime.now(),
            is_active=True,
        )
        session.add(admin_scope)

        # 创建演示用户
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

        await session.commit()
        print("  [OK] 管理员: admin / admin123")
        print("  [OK] 演示用户: demo / demo123")


async def seed_tech_elements():
    """初始化技术要素"""
    print("\n" + "="*60)
    print("Step 4: 初始化技术要素")
    print("="*60)

    async with AsyncSessionLocal() as session:
        from sqlalchemy import select

        # 检查是否已存在
        result = await session.execute(select(TechElement).limit(1))
        if result.scalar_one_or_none():
            print("  技术要素已存在，跳过创建")
            return

        for element_data in TECH_ELEMENTS_DATA:
            element = TechElement(**element_data)
            session.add(element)
            print(f"  [OK] {element_data['element_name']}")

        await session.commit()


async def seed_venues():
    """初始化顶刊顶会配置"""
    print("\n" + "="*60)
    print("Step 5: 初始化顶刊顶会配置")
    print("="*60)

    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        # 获取所有技术要素
        result = await session.execute(select(TechElement))
        tech_elements = {e.element_code: e for e in result.scalars().all()}

        stats = {"venues_created": 0, "bindings_created": 0}

        for element_data in VENUE_DATA:
            element_code = element_data["element_code"]
            venues_data = element_data["venues"]

            tech_element = tech_elements.get(element_code)
            if not tech_element:
                continue

            for idx, venue_info in enumerate(venues_data):
                venue_code = venue_info["id"].lower().replace(" ", "-").replace("_", "-")
                venue_name = venue_info["name"]
                venue_type = venue_info["type"]

                # 查找 OpenAlex ID
                openalex_id = KNOWN_OPENALEX_SOURCES.get(venue_code)

                # 检查 Venue 是否存在
                result = await session.execute(
                    select(Venue).where(Venue.venue_code == venue_code)
                )
                venue = result.scalar_one_or_none()

                if not venue:
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

                # 检查绑定是否存在
                result = await session.execute(
                    select(VenueTechBinding).where(
                        VenueTechBinding.venue_id == venue.venue_id,
                        VenueTechBinding.tech_element_id == tech_element.tech_element_id
                    )
                )
                binding = result.scalar_one_or_none()

                if not binding:
                    binding = VenueTechBinding(
                        venue_id=venue.venue_id,
                        tech_element_id=tech_element.tech_element_id,
                        priority=idx,
                        collect_status="pending",
                        is_enabled=True,
                    )
                    session.add(binding)
                    stats["bindings_created"] += 1

            print(f"  [OK] {tech_element.element_name}: {len(venues_data)} 个期刊")

        await session.commit()
        print(f"\n  Venue 创建: {stats['venues_created']}, 绑定创建: {stats['bindings_created']}")


async def seed_statistics_snapshot():
    """初始化统计快照"""
    print("\n" + "="*60)
    print("Step 6: 初始化统计快照")
    print("="*60)

    async with AsyncSessionLocal() as session:
        from sqlalchemy import select

        # 检查是否已存在活跃快照
        result = await session.execute(
            select(OverviewStatSnapshot).where(OverviewStatSnapshot.is_active == 1)
        )
        if result.scalar_one_or_none():
            print("  统计快照已存在，跳过创建")
            return

        version = f"v1.0_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # 获取技术要素数量
        result = await session.execute(select(TechElement))
        tech_element_count = len(result.scalars().all())

        snapshot = OverviewStatSnapshot(
            stat_version=version,
            generated_at=datetime.now().isoformat(),
            school_count=0,
            professor_count=0,
            student_count=0,
            talent_count=0,
            country_count=0,
            tech_element_count=tech_element_count,
            tech_direction_count=0,
            is_active=1,
        )
        session.add(snapshot)
        await session.commit()
        print(f"  [OK] 初始快照: {version}")
        print(f"  [OK] 技术要素数: {tech_element_count}")


async def init_system(full_reset: bool = False):
    """执行完整初始化流程

    Args:
        full_reset: 是否执行全量重置（清空用户、技术要素等基础数据）
    """
    print("\n" + "="*60)
    print("智能人才库 - 系统数据初始化")
    print("="*60)

    start_time = datetime.now()

    # 1. 清空数据表
    await truncate_tables(full_reset)

    # 2. 清空缓存
    await clear_cache()

    # 以下步骤仅在全量重置时执行
    if full_reset:
        # 3. 初始化用户
        await seed_admin_user()

        # 4. 初始化技术要素
        await seed_tech_elements()

        # 5. 初始化顶刊顶会
        await seed_venues()

    # 6. 初始化统计快照
    await seed_statistics_snapshot()

    # 完成
    elapsed = (datetime.now() - start_time).total_seconds()

    print("\n" + "="*60)
    print("初始化完成!")
    print("="*60)
    print(f"耗时: {elapsed:.2f} 秒")

    if full_reset:
        print("\n默认账号:")
        print("  管理员: admin / admin123")
        print("  演示用户: demo / demo123")
        print("\n[!] 生产环境请及时修改默认密码!")
    else:
        print("\n[提示] 已清空业务数据，用户和技术要素配置保留")
        print("[提示] 国家信息已改为常量定义，存储在 app/constants/countries.py")


def main():
    parser = argparse.ArgumentParser(
        description="一键初始化系统数据",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python scripts/init_system.py              # 交互式确认（仅清空业务数据）
    python scripts/init_system.py --force      # 跳过确认（仅清空业务数据）
    python scripts/init_system.py --full       # 全量重置（包含用户、技术要素）
    python scripts/init_system.py --full --force  # 全量重置跳过确认

注意: 国家数据已改为常量定义，存储在 app/constants/countries.py
        """
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="跳过确认提示"
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="全量重置（清空用户、技术要素等基础数据）"
    )

    args = parser.parse_args()

    # 确认提示
    if not args.force:
        if args.full:
            print("\n[!] 警告: 此操作将清空所有数据（包括用户、技术要素）!")
        else:
            print("\n[!] 警告: 此操作将清空所有业务数据!")
        confirm = input("\n确认执行? (y/N): ").strip().lower()
        if confirm != "y":
            print("已取消操作")
            return

    asyncio.run(init_system(full_reset=args.full))


if __name__ == "__main__":
    main()
