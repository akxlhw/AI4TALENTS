"""
一键初始化系统数据脚本

功能：
1. 清空业务数据表（默认保留系统配置 sys_config）
2. 重新运行数据库迁移
3. 初始化基础数据（管理员、技术领域、开源仓库配置）

使用方法：
    python scripts/init_system.py                   # 交互式确认，默认全部清空
    python scripts/init_system.py --force           # 跳过确认
    python scripts/init_system.py --domain academic # 仅清空学术人才库
    python scripts/init_system.py --domain open_source  # 仅清空开源人才库
    python scripts/init_system.py --full            # 全量重置（含用户、技术领域）
    python scripts/init_system.py --clear-config    # 同时清空系统配置表
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
from app.models.tech_domain import TechDomain
from app.models.statistics import OverviewStatSnapshot
from app.models.venue import Venue, VenueTechBinding
from app.domains.open_source.models.open_source import OSRepoConfig

# 学术人才库业务数据表
ACADEMIC_TABLES = [
    # 搜索和审计
    "search_talent_document",
    "audit_operation_log",
    # 人才相关
    "core_talent_tech_tag",
    "core_selected_work",
    "core_role_profile",
    "core_talent",
    "core_talent_embedding",
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
    "stats_research_topic",
    # 数据版本
    "data_quality_summary",
    "data_correction_record",
    "data_publish_record",
    "data_version",
    # 岗位匹配
    "jd_match_result",
    "jd_match_session",
]

# 开源人才库业务数据表
OPEN_SOURCE_TABLES = [
    "os_embedding",
    "os_contribution",
    "os_language_skill",
    "os_repository",
    "os_favourite",
    "os_pool_member",
    "os_talent_pool",
    "os_raw_developer",
    "os_repo_mapping",
    "os_developer",
    "os_collect_task",
    "os_repo_config",
]

# 系统配置表（默认保留，仅 --clear-config 时清空）
CONFIG_SYSTEM_TABLES = [
    "sys_config",
]

# 基础配置表（仅在 --full 时清空）
# 注意：期刊配置(config_venue, config_venue_tech_binding)永不清空，需要保留
CONFIG_TABLES = [
    "iam_user_school_scope",
    "core_tech_domain",
    "iam_user_account",
]

# 初始技术领域数据（6大技术领域）
TECH_DOMAINS_DATA = [
    {
        "domain_code": "ai",
        "domain_name": "人工智能",
        "domain_name_en": "Artificial Intelligence",
        "domain_desc": "人工智能相关技术",
        "sort_order": 1,
    },
    {
        "domain_code": "robotics",
        "domain_name": "机器人",
        "domain_name_en": "Robotics",
        "domain_desc": "机器人技术相关领域",
        "sort_order": 2,
    },
    {
        "domain_code": "data_science",
        "domain_name": "数据科学",
        "domain_name_en": "Data Science",
        "domain_desc": "数据科学与分析",
        "sort_order": 3,
    },
    {
        "domain_code": "networks",
        "domain_name": "网络与通信",
        "domain_name_en": "Networks & Communications",
        "domain_desc": "计算机网络与通信技术",
        "sort_order": 4,
    },
    {
        "domain_code": "systems",
        "domain_name": "系统与软件",
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


# 默认开源仓库配置（种子数据）
# 覆盖六大技术领域，共35个仓库，便于快速体验开源人才库功能
DEFAULT_REPO_CONFIGS = [
    # AI
    {"repo_full_name": "pytorch/pytorch", "display_name": "PyTorch", "tech_element": "ai", "language": "Python", "description": "Tensors and Dynamic neural networks in Python with strong GPU acceleration"},
    {"repo_full_name": "tensorflow/tensorflow", "display_name": "TensorFlow", "tech_element": "ai", "language": "Python", "description": "An Open Source Machine Learning Framework for Everyone"},
    {"repo_full_name": "huggingface/transformers", "display_name": "Hugging Face Transformers", "tech_element": "ai", "language": "Python", "description": "State-of-the-art Machine Learning for JAX, PyTorch and TensorFlow"},
    {"repo_full_name": "scikit-learn/scikit-learn", "display_name": "scikit-learn", "tech_element": "ai", "language": "Python", "description": "scikit-learn: machine learning in Python"},
    {"repo_full_name": "microsoft/DeepSpeed", "display_name": "DeepSpeed", "tech_element": "ai", "language": "Python", "description": "Deep learning optimization library"},
    {"repo_full_name": "apache/spark", "display_name": "Apache Spark", "tech_element": "ai", "language": "Scala", "description": "Apache Spark - A unified analytics engine for large-scale data processing"},
    # Robotics
    {"repo_full_name": "ros/ros", "display_name": "ROS", "tech_element": "robotics", "language": "Python", "description": "Robot Operating System"},
    {"repo_full_name": "ros2/ros2", "display_name": "ROS2", "tech_element": "robotics", "language": "Python", "description": "ROS 2 - Robot Operating System 2"},
    {"repo_full_name": "ArduPilot/ardupilot", "display_name": "ArduPilot", "tech_element": "robotics", "language": "C++", "description": "ArduPilot is the most advanced, full-featured open source autopilot software"},
    {"repo_full_name": "NVIDIA-Omniverse/IsaacSim", "display_name": "NVIDIA Isaac Sim", "tech_element": "robotics", "language": "Python", "description": "NVIDIA Isaac Sim - Robotics simulation platform"},
    {"repo_full_name": "google-research/google-research", "display_name": "Google Research", "tech_element": "robotics", "language": "Python", "description": "Google Research repository"},
    # Data Science
    {"repo_full_name": "pandas-dev/pandas", "display_name": "pandas", "tech_element": "data_science", "language": "Python", "description": "Powerful data structures for data analysis"},
    {"repo_full_name": "numpy/numpy", "display_name": "NumPy", "tech_element": "data_science", "language": "Python", "description": "The fundamental package for scientific computing with Python"},
    {"repo_full_name": "jupyter/jupyter", "display_name": "Jupyter", "tech_element": "data_science", "language": "Python", "description": "Jupyter metapackage for installation and docs"},
    {"repo_full_name": "matplotlib/matplotlib", "display_name": "Matplotlib", "tech_element": "data_science", "language": "Python", "description": "matplotlib: plotting with Python"},
    {"repo_full_name": "apache/arrow", "display_name": "Apache Arrow", "tech_element": "data_science", "language": "C++", "description": "Apache Arrow is a multi-language toolbox for accelerated data interchange"},
    {"repo_full_name": "dask/dask", "display_name": "Dask", "tech_element": "data_science", "language": "Python", "description": "Parallel computing with task scheduling"},
    # Networks
    {"repo_full_name": "torvalds/linux", "display_name": "Linux Kernel", "tech_element": "networks", "language": "C", "description": "Linux kernel source tree"},
    {"repo_full_name": "envoyproxy/envoy", "display_name": "Envoy", "tech_element": "networks", "language": "C++", "description": "Cloud-native high-performance edge/middle/service proxy"},
    {"repo_full_name": "grpc/grpc", "display_name": "gRPC", "tech_element": "networks", "language": "C++", "description": "The C based gRPC (C++, Python, Ruby, Objective-C, PHP, C#)"},
    {"repo_full_name": "openvswitch/ovs", "display_name": "Open vSwitch", "tech_element": "networks", "language": "C", "description": "Open vSwitch is a production quality, multilayer virtual switch"},
    {"repo_full_name": "cloudflare/cloudflared", "display_name": "Cloudflared", "tech_element": "networks", "language": "Go", "description": "Cloudflare Tunnel client"},
    {"repo_full_name": "FRRouting/frr", "display_name": "FRRouting", "tech_element": "networks", "language": "C", "description": "FRRouting is free software that manages TCP/IP based routing protocols"},
    # Systems
    {"repo_full_name": "golang/go", "display_name": "Go", "tech_element": "systems", "language": "Go", "description": "The Go programming language"},
    {"repo_full_name": "rust-lang/rust", "display_name": "Rust", "tech_element": "systems", "language": "Rust", "description": "Empowering everyone to build reliable and efficient software"},
    {"repo_full_name": "kubernetes/kubernetes", "display_name": "Kubernetes", "tech_element": "systems", "language": "Go", "description": "Production-Grade Container Scheduling and Management"},
    {"repo_full_name": "moby/moby", "display_name": "Docker", "tech_element": "systems", "language": "Go", "description": "Moby Project - a collaborative project for the container ecosystem"},
    {"repo_full_name": "redis/redis", "display_name": "Redis", "tech_element": "systems", "language": "C", "description": "Redis is an in-memory database that persists on disk"},
    {"repo_full_name": "apache/kafka", "display_name": "Apache Kafka", "tech_element": "systems", "language": "Java", "description": "Mirror of Apache Kafka"},
    # Security
    {"repo_full_name": "zaproxy/zaproxy", "display_name": "OWASP ZAP", "tech_element": "security", "language": "Java", "description": "The OWASP ZAP core project"},
    {"repo_full_name": "rapid7/metasploit-framework", "display_name": "Metasploit", "tech_element": "security", "language": "Ruby", "description": "Metasploit Framework"},
    {"repo_full_name": "sqlmapproject/sqlmap", "display_name": "sqlmap", "tech_element": "security", "language": "Python", "description": "Automatic SQL injection and database takeover tool"},
    {"repo_full_name": "nmap/nmap", "display_name": "Nmap", "tech_element": "security", "language": "C", "description": "Nmap - the Network Mapper"},
    {"repo_full_name": "mitmproxy/mitmproxy", "display_name": "mitmproxy", "tech_element": "security", "language": "Python", "description": "An interactive TLS-capable intercepting HTTP proxy"},
    {"repo_full_name": "wireshark/wireshark", "display_name": "Wireshark", "tech_element": "security", "language": "C", "description": "Wireshark - Network traffic analyzer"},
]


# 技术领域与顶会顶刊映射数据
VENUE_DATA = [
    {
        "domain_code": "ai",
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
        "domain_code": "robotics",
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
        "domain_code": "data_science",
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
        "domain_code": "networks",
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
        "domain_code": "systems",
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
        "domain_code": "security",
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


async def truncate_tables(
    full_reset: bool = False,
    clear_config: bool = False,
    domain: str = "all",
):
    """清空业务数据表

    Args:
        full_reset: 是否同时清空基础配置表（用户、技术领域等）
        clear_config: 是否清空系统配置表（sys_config 等）
        domain: 清空范围，可选 academic / open_source / all（默认 all）
    """
    print("\n" + "="*60)
    print("Step 1: 清空数据表")
    print("="*60)

    async with AsyncSessionLocal() as session:
        # 根据 domain 选择要清空的表
        tables: list[str] = []
        if domain in ("all", "academic"):
            tables.extend(ACADEMIC_TABLES)
            print("  [范围: 学术人才库]")
        if domain in ("all", "open_source"):
            tables.extend(OPEN_SOURCE_TABLES)
            print("  [范围: 开源人才库]")

        if clear_config:
            tables.extend(CONFIG_SYSTEM_TABLES)
            print("  [模式: 包含系统配置表]")

        if full_reset:
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
        from app.domains.shared.services.cache_service import CacheService

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


async def seed_tech_domains():
    """初始化技术领域"""
    print("\n" + "="*60)
    print("Step 4: 初始化技术领域")
    print("="*60)

    async with AsyncSessionLocal() as session:
        from sqlalchemy import select

        # 检查是否已存在
        result = await session.execute(select(TechDomain).limit(1))
        if result.scalar_one_or_none():
            print("  技术领域已存在，跳过创建")
            return

        for domain_data in TECH_DOMAINS_DATA:
            domain = TechDomain(**domain_data)
            session.add(domain)
            print(f"  [OK] {domain_data['domain_name']}")

        await session.commit()


async def seed_venues():
    """初始化顶刊顶会配置"""
    print("\n" + "="*60)
    print("Step 5: 初始化顶刊顶会配置")
    print("="*60)

    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        # 获取所有技术领域
        result = await session.execute(select(TechDomain))
        tech_domains = {d.domain_code: d for d in result.scalars().all()}

        stats = {"venues_created": 0, "bindings_created": 0}

        for domain_data in VENUE_DATA:
            domain_code = domain_data["domain_code"]
            venues_data = domain_data["venues"]

            tech_domain = tech_domains.get(domain_code)
            if not tech_domain:
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
                        VenueTechBinding.tech_domain_id == tech_domain.tech_domain_id
                    )
                )
                binding = result.scalar_one_or_none()

                if not binding:
                    binding = VenueTechBinding(
                        venue_id=venue.venue_id,
                        tech_domain_id=tech_domain.tech_domain_id,
                        priority=idx,
                        collect_status="pending",
                        is_enabled=True,
                    )
                    session.add(binding)
                    stats["bindings_created"] += 1

            print(f"  [OK] {tech_domain.domain_name}: {len(venues_data)} 个期刊")

        await session.commit()
        print(f"\n  Venue 创建: {stats['venues_created']}, 绑定创建: {stats['bindings_created']}")


async def seed_open_source_repo_configs():
    """初始化默认开源仓库配置"""
    print("\n" + "="*60)
    print("Step 5.5: 初始化默认开源仓库配置")
    print("="*60)

    async with AsyncSessionLocal() as session:
        from sqlalchemy import select

        for config_data in DEFAULT_REPO_CONFIGS:
            existing = await session.scalar(
                select(OSRepoConfig).where(
                    OSRepoConfig.repo_full_name == config_data["repo_full_name"]
                )
            )
            if existing:
                print(f"  [SKIP] {config_data['repo_full_name']} 已存在")
                continue

            config = OSRepoConfig(
                repo_full_name=config_data["repo_full_name"],
                display_name=config_data["display_name"],
                tech_element=config_data["tech_element"],
                language=config_data.get("language"),
                description=config_data.get("description"),
                is_active=True,
                collect_enabled=True,
            )
            session.add(config)
            print(f"  [OK] {config_data['display_name']} ({config_data['tech_element']})")

        await session.commit()


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

        # 获取技术领域数量
        result = await session.execute(select(TechDomain))
        tech_domain_count = len(result.scalars().all())

        snapshot = OverviewStatSnapshot(
            stat_version=version,
            generated_at=datetime.now().isoformat(),
            school_count=0,
            professor_count=0,
            student_count=0,
            talent_count=0,
            country_count=0,
            tech_domain_count=tech_domain_count,
            tech_direction_count=0,
            is_active=1,
        )
        session.add(snapshot)
        await session.commit()
        print(f"  [OK] 初始快照: {version}")
        print(f"  [OK] 技术领域数: {tech_domain_count}")


async def init_system(
    full_reset: bool = False,
    clear_config: bool = False,
    domain: str = "all",
):
    """执行完整初始化流程

    Args:
        full_reset: 是否执行全量重置（清空用户、技术领域等基础数据）
        clear_config: 是否清空系统配置表（sys_config 等）
        domain: 初始化范围，可选 academic / open_source / all（默认 all）
    """
    print("\n" + "="*60)
    print("智能人才库 - 系统数据初始化")
    print("="*60)

    start_time = datetime.now()

    # 1. 清空数据表
    await truncate_tables(full_reset, clear_config, domain)

    # 2. 清空缓存
    await clear_cache()

    # 以下步骤仅在全量重置时执行
    if full_reset:
        # 3. 初始化用户
        await seed_admin_user()

        # 4. 初始化技术领域
        await seed_tech_domains()

        # 5. 初始化顶刊顶会
        await seed_venues()

    # 5.5 初始化开源仓库配置（幂等：已存在则跳过）
    if domain in ("all", "open_source"):
        await seed_open_source_repo_configs()

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
        print("\n[提示] 已清空业务数据，用户和技术领域配置保留")
        if not clear_config:
            print("[提示] 系统配置表(sys_config)已保留，如需清除请使用 --clear-config")
        print("[提示] 国家信息已改为常量定义，存储在 app/constants/countries.py")


def main():
    parser = argparse.ArgumentParser(
        description="一键初始化系统数据",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python scripts/init_system.py                       # 交互式确认，默认清空全部
    python scripts/init_system.py --force               # 跳过确认，默认清空全部
    python scripts/init_system.py --domain academic     # 仅清空学术人才库
    python scripts/init_system.py --domain open_source  # 仅清空开源人才库
    python scripts/init_system.py --full                # 全量重置（含用户、技术领域）
    python scripts/init_system.py --clear-config        # 同时清空系统配置表
    python scripts/init_system.py --full --force        # 全量重置跳过确认

注意: 默认清空全部业务数据（学术+开源），如需指定领域请使用 --domain
       默认保留系统配置表(sys_config)，如需清除请使用 --clear-config
       国家数据已改为常量定义，存储在 app/constants/countries.py
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
        help="全量重置（清空用户、技术领域等基础数据）"
    )
    parser.add_argument(
        "--clear-config",
        action="store_true",
        help="同时清空系统配置表(sys_config)"
    )
    parser.add_argument(
        "--domain",
        choices=["academic", "open_source", "all"],
        default="all",
        help="指定要清空的人才库领域（默认 all）"
    )

    args = parser.parse_args()

    # 确认提示
    if not args.force:
        domain_label = {"academic": "学术人才库", "open_source": "开源人才库", "all": "全部业务数据"}
        print(f"\n[!] 警告: 此操作将清空 {domain_label[args.domain]}!")
        if args.full:
            print("[!] 注意: 全量重置模式，用户和技术领域等基础数据也将被清空!")
        if args.clear_config:
            print("[!] 注意: 系统配置表(sys_config)也将被清空!")
        confirm = input("\n确认执行? (y/N): ").strip().lower()
        if confirm != "y":
            print("已取消操作")
            return

    asyncio.run(init_system(full_reset=args.full, clear_config=args.clear_config, domain=args.domain))


if __name__ == "__main__":
    main()
