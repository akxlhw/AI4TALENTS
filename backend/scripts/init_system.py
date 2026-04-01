"""
一键初始化系统数据脚本

功能：
1. 清空所有业务数据表
2. 重新运行数据库迁移
3. 初始化基础数据（国家、管理员、技术要素）

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
from app.models.country import Country
from app.models.iam import UserAccount, UserSchoolScope
from app.models.tech_element import TechElement, TechDirection
from app.models.statistics import OverviewStatSnapshot

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
    # 国家数据（采集入库）
    "core_country",
]

# 基础配置表（仅在 --full 时清空）
# 注意：期刊配置(config_venue, config_venue_tech_binding)永不清空，需要保留
CONFIG_TABLES = [
    "iam_user_school_scope",
    "core_tech_direction",
    "core_tech_element",
    "iam_user_account",
]

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


async def truncate_tables(full_reset: bool = False):
    """清空业务数据表

    Args:
        full_reset: 是否同时清空基础配置表（用户、国家、技术要素等）
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

        truncated_count = 0
        for table in tables:
            try:
                await session.execute(text(f"DELETE FROM {table}"))
                truncated_count += 1
                print(f"  [OK] {table}")
            except Exception as e:
                error_msg = str(e)
                if "no such table" in error_msg:
                    print(f"  [SKIP] {table} (不存在)")
                else:
                    print(f"  [WARN] {table}: {error_msg[:50]}...")
                continue

        await session.commit()
        print(f"\n已清空 {truncated_count} 个表")


async def seed_countries():
    """初始化国家数据"""
    print("\n" + "="*60)
    print("Step 2: 初始化国家数据")
    print("="*60)

    # 完整的国家代码列表（ISO 3166-1 alpha-2）
    # 包含主要学术强国和常见国家
    countries_data = [
        # 主要国家（按学术活跃度排序）
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
        # 其他重要国家
        ("IN", "印度", "India", 16),
        ("RU", "俄罗斯", "Russia", 17),
        ("BR", "巴西", "Brazil", 18),
        ("HK", "香港", "Hong Kong", 19),
        ("PL", "波兰", "Poland", 21),
        ("VN", "越南", "Vietnam", 22),
        ("FI", "芬兰", "Finland", 23),
        ("NO", "挪威", "Norway", 24),
        ("DK", "丹麦", "Denmark", 25),
        ("AT", "奥地利", "Austria", 26),
        ("BE", "比利时", "Belgium", 27),
        ("IL", "以色列", "Israel", 28),
        ("NZ", "新西兰", "New Zealand", 29),
        ("IE", "爱尔兰", "Ireland", 30),
        ("PT", "葡萄牙", "Portugal", 31),
        ("CZ", "捷克", "Czech Republic", 32),
        ("GR", "希腊", "Greece", 33),
        ("MY", "马来西亚", "Malaysia", 34),
        ("TH", "泰国", "Thailand", 35),
        ("ZA", "南非", "South Africa", 36),
        ("MX", "墨西哥", "Mexico", 37),
        ("AE", "阿联酋", "United Arab Emirates", 38),
        ("SA", "沙特阿拉伯", "Saudi Arabia", 39),
        ("TR", "土耳其", "Turkey", 40),
        ("ID", "印度尼西亚", "Indonesia", 41),
        ("PH", "菲律宾", "Philippines", 42),
        ("AR", "阿根廷", "Argentina", 43),
        ("CL", "智利", "Chile", 44),
        ("CO", "哥伦比亚", "Colombia", 45),
        ("EG", "埃及", "Egypt", 46),
        ("NG", "尼日利亚", "Nigeria", 47),
        ("PK", "巴基斯坦", "Pakistan", 48),
        ("BD", "孟加拉国", "Bangladesh", 49),
        ("HU", "匈牙利", "Hungary", 50),
        ("RO", "罗马尼亚", "Romania", 51),
        ("UA", "乌克兰", "Ukraine", 52),
        ("RS", "塞尔维亚", "Serbia", 53),
        ("SI", "斯洛文尼亚", "Slovenia", 54),
        ("SK", "斯洛伐克", "Slovakia", 55),
        ("BG", "保加利亚", "Bulgaria", 56),
        ("HR", "克罗地亚", "Croatia", 57),
        ("LT", "立陶宛", "Lithuania", 58),
        ("LV", "拉脱维亚", "Latvia", 59),
        ("EE", "爱沙尼亚", "Estonia", 60),
        ("IS", "冰岛", "Iceland", 61),
        ("LU", "卢森堡", "Luxembourg", 62),
        ("MT", "马耳他", "Malta", 63),
        ("CY", "塞浦路斯", "Cyprus", 64),
        # 中东和北非
        ("IQ", "伊拉克", "Iraq", 65),
        ("IR", "伊朗", "Iran", 66),
        ("MM", "缅甸", "Myanmar", 67),
        ("MN", "蒙古", "Mongolia", 68),
        ("KP", "朝鲜", "North Korea", 69),
        ("LK", "斯里兰卡", "Sri Lanka", 70),
        ("NP", "尼泊尔", "Nepal", 71),
        ("JO", "约旦", "Jordan", 72),
        ("LB", "黎巴嫩", "Lebanon", 73),
        ("MA", "摩洛哥", "Morocco", 74),
        ("TN", "突尼斯", "Tunisia", 75),
        ("DZ", "阿尔及利亚", "Algeria", 76),
        # 非洲
        ("KE", "肯尼亚", "Kenya", 77),
        ("GH", "加纳", "Ghana", 78),
        ("ET", "埃塞俄比亚", "Ethiopia", 79),
        ("UG", "乌干达", "Uganda", 80),
        ("TZ", "坦桑尼亚", "Tanzania", 81),
        ("CM", "喀麦隆", "Cameroon", 82),
        # 南美洲
        ("PE", "秘鲁", "Peru", 83),
        ("VE", "委内瑞拉", "Venezuela", 84),
        ("UY", "乌拉圭", "Uruguay", 85),
        ("PY", "巴拉圭", "Paraguay", 86),
        ("BO", "玻利维亚", "Bolivia", 87),
        ("EC", "厄瓜多尔", "Ecuador", 88),
        # 中美洲和加勒比
        ("CU", "古巴", "Cuba", 89),
        ("JM", "牙买加", "Jamaica", 90),
        ("CR", "哥斯达黎加", "Costa Rica", 91),
        ("PA", "巴拿马", "Panama", 92),
        ("DO", "多米尼加", "Dominican Republic", 93),
        ("GT", "危地马拉", "Guatemala", 94),
        # 未知/其他
        ("XX", "未知", "Unknown", 999),
    ]

    async with AsyncSessionLocal() as session:
        for code, name_cn, name_en, sort_order in countries_data:
            country = Country(
                country_code=code,
                country_name_cn=name_cn,
                country_name_en=name_en,
                sort_order=sort_order,
                is_active=True,
            )
            session.add(country)

        await session.commit()
        print(f"  [OK] 已创建 {len(countries_data)} 个国家")


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
            directions_data = element_data.copy().pop("directions")
            element = TechElement(**{k: v for k, v in element_data.items() if k != "directions"})
            session.add(element)
            await session.flush()

            for dir_data in directions_data:
                direction = TechDirection(
                    **dir_data,
                    tech_element_id=element.tech_element_id
                )
                session.add(direction)

            print(f"  [OK] {element_data['element_name']} ({len(directions_data)} 个方向)")

        await session.commit()


async def seed_statistics_snapshot():
    """初始化统计快照"""
    print("\n" + "="*60)
    print("Step 5: 初始化统计快照")
    print("="*60)

    async with AsyncSessionLocal() as session:
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
        await session.commit()
        print(f"  [OK] 初始快照: {version}")


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

    # 以下步骤仅在全量重置时执行
    if full_reset:
        # 2. 初始化用户
        await seed_admin_user()

        # 3. 初始化技术要素
        await seed_tech_elements()

    # 4. 初始化统计快照
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


def main():
    parser = argparse.ArgumentParser(
        description="一键初始化系统数据",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python scripts/init_system.py              # 交互式确认（仅清空业务数据）
    python scripts/init_system.py --force      # 跳过确认（仅清空业务数据）
    python scripts/init_system.py --full       # 全量重置（包含用户、国家、技术要素）
    python scripts/init_system.py --full --force  # 全量重置跳过确认
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
        help="全量重置（清空用户、国家、技术要素等基础数据）"
    )

    args = parser.parse_args()

    # 确认提示
    if not args.force:
        if args.full:
            print("\n[!] 警告: 此操作将清空所有数据（包括用户、国家、技术要素）!")
        else:
            print("\n[!] 警告: 此操作将清空所有业务数据!")
        confirm = input("\n确认执行? (y/N): ").strip().lower()
        if confirm != "y":
            print("已取消操作")
            return

    asyncio.run(init_system(full_reset=args.full))


if __name__ == "__main__":
    main()
