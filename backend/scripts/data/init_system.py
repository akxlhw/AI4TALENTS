"""System data initialization script.

Functions:
  1. Clear business data tables (retains collection configs & sys_config by default)
  2. Re-run database migrations
  3. Seed base data (admin user, tech domains, open-source repo configs)

Usage:
    python scripts/init_system.py                       # Interactive confirmation
    python scripts/init_system.py --force               # Skip confirmation
    python scripts/init_system.py --domain academic     # Academic only
    python scripts/init_system.py --domain open_source  # Open source only
    python scripts/init_system.py --full                # Full reset (users + domains)
    python scripts/init_system.py --clear-collection    # Also clear collection configs
    python scripts/init_system.py --clear-config        # Also clear sys_config
"""
import asyncio
import sys

# Fix asyncpg connection issues on Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
import argparse
import io
from datetime import datetime
from pathlib import Path

# Force UTF-8 stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# Import model registry first to ensure all SQLAlchemy mappers are properly configured
from app.core.auth import hash_password
from app.core.config import settings

# Use NullPool for init script to avoid Windows asyncpg connection pool issues
_init_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
AsyncSessionLocal = async_sessionmaker(
    bind=_init_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)
from app.domains.academic.models.statistics import OverviewStatSnapshot
from app.domains.academic.models.tech_domain import TechDomain
from app.domains.academic.models.venue import Venue, VenueTechBinding
from app.domains.open_source.models.open_source import OSRepoConfig
from app.domains.shared.models.enums import ScopeType, UserRoleType
from app.domains.shared.models.iam import UserAccount, UserSchoolScope

# Academic domain business tables (cleared by default)
ACADEMIC_TABLES = [
    # Search & audit
    "search_talent_document",
    "audit_operation_log",
    # Talent-related
    "core_talent_tech_tag",
    "core_selected_work",
    "core_role_profile",
    "core_talent",
    "core_talent_embedding",
    # School-related
    "core_school_alias",
    "core_school",
    # Collaboration network
    "core_work_author",
    "core_collaboration",
    # Favorites & talent pools
    "iam_talent_pool_member",
    "iam_favorite_talent",
    "iam_talent_pool",
    # Standardized layer
    "std_school_alias",
    "std_author",
    "std_school",
    # Raw data layer
    "rel_author_tech_belong",
    "raw_work",
    "raw_author",
    "raw_institution",
    # Statistics snapshots
    "stat_school_snapshot",
    "stat_overview_snapshot",
    "stats_research_topic",
    # Data versions
    "data_quality_summary",
    "data_correction_record",
    "data_publish_record",
    "data_version",
    # JD matching
    "jd_match_result",
    "jd_match_session",
]

# Academic collection config tables (preserved by default; cleared with --clear-collection)
ACADEMIC_COLLECTION_TABLES = [
    "sync_venue_sub_task",
    "sync_collect_task",
]

# Open Source domain business tables (cleared by default)
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
]

# Open Source collection config tables (preserved by default; cleared with --clear-collection)
OPEN_SOURCE_COLLECTION_TABLES = [
    "os_collect_task",
    "os_repo_config",
]

# System config tables (retained by default; cleared with --clear-config)
CONFIG_SYSTEM_TABLES = [
    "sys_config",
]

# Base config tables (cleared only with --full)
# NOTE: venue config tables are never cleared
CONFIG_TABLES = [
    "iam_user_school_scope",
    "core_tech_domain",
    "iam_user_account",
]

# Tech domain data — single source of truth lives in
# app/domains/shared/constants/tech_taxonomy.py (taxonomy v2: 10 domains /
# 34 elements / 75 directions). Seeded here for fresh installs.
from app.domains.shared.constants.tech_taxonomy import (
    TECH_DIRECTIONS,
    TECH_DOMAINS,
    TECH_ELEMENTS,
)

TECH_DOMAINS_DATA = [
    {
        "domain_code": dom["code"],
        "domain_name": dom["name"],
        "domain_name_en": dom["name_en"],
        "domain_desc": f"{dom['name_en']} related technologies",
        "sort_order": dom["sort"],
    }
    for dom in TECH_DOMAINS
]

# Direction seeds derived from the shared taxonomy (element info included)
TECH_DIRECTIONS_DATA = {
    dom["code"]: [
        (code, name, name_en, TECH_ELEMENTS[element]["name"])
        for code, name, name_en, element in TECH_DIRECTIONS
        if TECH_ELEMENTS[element]["domain"] == dom["code"]
    ]
    for dom in TECH_DOMAINS
}


# Known OpenAlex Source ID mappings
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


# Default open-source repo seed configs
DEFAULT_REPO_CONFIGS = [
    # AI
    {"repo_full_name": "pytorch/pytorch", "display_name": "PyTorch", "tech_element": "training", "language": "Python", "description": "Tensors and Dynamic neural networks in Python with strong GPU acceleration"},
    {"repo_full_name": "tensorflow/tensorflow", "display_name": "TensorFlow", "tech_element": "training", "language": "Python", "description": "An Open Source Machine Learning Framework for Everyone"},
    {"repo_full_name": "huggingface/transformers", "display_name": "Hugging Face Transformers", "tech_element": "models", "language": "Python", "description": "State-of-the-art Machine Learning for JAX, PyTorch and TensorFlow"},
    {"repo_full_name": "scikit-learn/scikit-learn", "display_name": "scikit-learn", "tech_element": "models", "language": "Python", "description": "scikit-learn: machine learning in Python"},
    {"repo_full_name": "microsoft/DeepSpeed", "display_name": "DeepSpeed", "tech_element": "training", "language": "Python", "description": "Deep learning optimization library"},
    {"repo_full_name": "apache/spark", "display_name": "Apache Spark", "tech_element": "db_storage", "language": "Scala", "description": "Apache Spark - A unified analytics engine for large-scale data processing"},
    {"repo_full_name": "langchain-ai/langchain", "display_name": "LangChain", "tech_element": "agents", "language": "Python", "description": "Build context-aware reasoning applications"},
    {"repo_full_name": "langgenius/dify", "display_name": "Dify", "tech_element": "agents", "language": "TypeScript", "description": "Dify is an open-source LLM app development platform"},
    {"repo_full_name": "huggingface/trl", "display_name": "TRL", "tech_element": "training", "language": "Python", "description": "Train transformer language models with reinforcement learning"},
    {"repo_full_name": "sgl-project/sglang", "display_name": "SGLang", "tech_element": "inference", "language": "Python", "description": "SGLang is a fast serving framework for large language models"},
    {"repo_full_name": "huggingface/text-generation-inference", "display_name": "Text Generation Inference", "tech_element": "inference", "language": "Python", "description": "Large Language Model Text Generation Inference"},
    {"repo_full_name": "ray-project/ray", "display_name": "Ray", "tech_element": "training", "language": "Python", "description": "Ray is a unified framework for scaling AI and Python applications"},
    {"repo_full_name": "NVIDIA/Megatron-LM", "display_name": "Megatron-LM", "tech_element": "training", "language": "Python", "description": "Ongoing research training transformer models at scale"},
    {"repo_full_name": "google/jax", "display_name": "JAX", "tech_element": "training", "language": "Python", "description": "Composable transformations of Python+NumPy programs"},
    {"repo_full_name": "apache/tvm", "display_name": "Apache TVM", "tech_element": "inference", "language": "Python", "description": "Open deep learning compiler stack for cpu, gpu and specialized accelerators"},
    {"repo_full_name": "NVIDIA/cutlass", "display_name": "CUTLASS", "tech_element": "hpc", "language": "C++", "description": "CUDA Templates for Linear Algebra Subroutines"},
    # Robotics
    {"repo_full_name": "ros/ros", "display_name": "ROS", "tech_element": "robot_control", "language": "Python", "description": "Robot Operating System"},
    {"repo_full_name": "ros2/ros2", "display_name": "ROS2", "tech_element": "robot_control", "language": "Python", "description": "ROS 2 - Robot Operating System 2"},
    {"repo_full_name": "ArduPilot/ardupilot", "display_name": "ArduPilot", "tech_element": "robot_control", "language": "C++", "description": "ArduPilot is the most advanced, full-featured open source autopilot software"},
    {"repo_full_name": "NVIDIA-Omniverse/IsaacSim", "display_name": "NVIDIA Isaac Sim", "tech_element": "embodied", "language": "Python", "description": "NVIDIA Isaac Sim - Robotics simulation platform"},
    {"repo_full_name": "google-research/google-research", "display_name": "Google Research", "tech_element": "models", "language": "Python", "description": "Google Research repository"},
    # Data Science
    {"repo_full_name": "pandas-dev/pandas", "display_name": "pandas", "tech_element": "sci_compute", "language": "Python", "description": "Powerful data structures for data analysis"},
    {"repo_full_name": "numpy/numpy", "display_name": "NumPy", "tech_element": "sci_compute", "language": "Python", "description": "The fundamental package for scientific computing with Python"},
    {"repo_full_name": "jupyter/jupyter", "display_name": "Jupyter", "tech_element": "ai_engineering", "language": "Python", "description": "Jupyter metapackage for installation and docs"},
    {"repo_full_name": "matplotlib/matplotlib", "display_name": "Matplotlib", "tech_element": "sci_compute", "language": "Python", "description": "matplotlib: plotting with Python"},
    {"repo_full_name": "apache/arrow", "display_name": "Apache Arrow", "tech_element": "db_storage", "language": "C++", "description": "Apache Arrow is a multi-language toolbox for accelerated data interchange"},
    {"repo_full_name": "dask/dask", "display_name": "Dask", "tech_element": "hpc", "language": "Python", "description": "Parallel computing with task scheduling"},
    # Networks
    {"repo_full_name": "torvalds/linux", "display_name": "Linux Kernel", "tech_element": "os", "language": "C", "description": "Linux kernel source tree"},
    {"repo_full_name": "envoyproxy/envoy", "display_name": "Envoy", "tech_element": "protocols", "language": "C++", "description": "Cloud-native high-performance edge/middle/service proxy"},
    {"repo_full_name": "grpc/grpc", "display_name": "gRPC", "tech_element": "protocols", "language": "C++", "description": "The C based gRPC (C++, Python, Ruby, Objective-C, PHP, C#)"},
    {"repo_full_name": "openvswitch/ovs", "display_name": "Open vSwitch", "tech_element": "protocols", "language": "C", "description": "Open vSwitch is a production quality, multilayer virtual switch"},
    {"repo_full_name": "cloudflare/cloudflared", "display_name": "Cloudflared", "tech_element": "protocols", "language": "Go", "description": "Cloudflare Tunnel client"},
    {"repo_full_name": "FRRouting/frr", "display_name": "FRRouting", "tech_element": "protocols", "language": "C", "description": "FRRouting is free software that manages TCP/IP based routing protocols"},
    # Systems
    {"repo_full_name": "golang/go", "display_name": "Go", "tech_element": "languages", "language": "Go", "description": "The Go programming language"},
    {"repo_full_name": "rust-lang/rust", "display_name": "Rust", "tech_element": "languages", "language": "Rust", "description": "Empowering everyone to build reliable and efficient software"},
    {"repo_full_name": "kubernetes/kubernetes", "display_name": "Kubernetes", "tech_element": "cloud_native", "language": "Go", "description": "Production-Grade Container Scheduling and Management"},
    {"repo_full_name": "moby/moby", "display_name": "Docker", "tech_element": "cloud_native", "language": "Go", "description": "Moby Project - a collaborative project for the container ecosystem"},
    {"repo_full_name": "redis/redis", "display_name": "Redis", "tech_element": "db_storage", "language": "C", "description": "Redis is an in-memory database that persists on disk"},
    {"repo_full_name": "apache/kafka", "display_name": "Apache Kafka", "tech_element": "middleware", "language": "Java", "description": "Mirror of Apache Kafka"},
    # Security
    {"repo_full_name": "zaproxy/zaproxy", "display_name": "OWASP ZAP", "tech_element": "sys_sec", "language": "Java", "description": "The OWASP ZAP core project"},
    {"repo_full_name": "rapid7/metasploit-framework", "display_name": "Metasploit", "tech_element": "sec_ops", "language": "Ruby", "description": "Metasploit Framework"},
    {"repo_full_name": "sqlmapproject/sqlmap", "display_name": "sqlmap", "tech_element": "sec_ops", "language": "Python", "description": "Automatic SQL injection and database takeover tool"},
    {"repo_full_name": "nmap/nmap", "display_name": "Nmap", "tech_element": "sys_sec", "language": "C", "description": "Nmap - the Network Mapper"},
    {"repo_full_name": "mitmproxy/mitmproxy", "display_name": "mitmproxy", "tech_element": "sys_sec", "language": "Python", "description": "An interactive TLS-capable intercepting HTTP proxy"},
    {"repo_full_name": "wireshark/wireshark", "display_name": "Wireshark", "tech_element": "sys_sec", "language": "C", "description": "Wireshark - Network traffic analyzer"},
]


# Tech domain -> venue mapping data
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
    clear_collection: bool = False,
    domain: str = "all",
):
    """Truncate business data tables.
    Args:
        full_reset: Also clear base config tables (users, tech domains)
        clear_config: Also clear system config tables (sys_config)
        clear_collection: Also clear collection config tables (tasks, repo configs)
        domain: Domain to clear (academic / open_source / all, default all)
    """
    print("\n" + "="*60)
    print("Step 1: Clear data tables")
    print("="*60)

    async with AsyncSessionLocal() as session:
        # Select tables to clear by domain
        tables: list[str] = []
        if domain in ("all", "academic"):
            tables.extend(ACADEMIC_TABLES)
            print("  [Scope: Academic]")
        if domain in ("all", "open_source"):
            tables.extend(OPEN_SOURCE_TABLES)
            print("  [Scope: Open Source]")

        if clear_collection:
            if domain in ("all", "academic"):
                tables.extend(ACADEMIC_COLLECTION_TABLES)
                print("  [Mode: include academic collection configs]")
            if domain in ("all", "open_source"):
                tables.extend(OPEN_SOURCE_COLLECTION_TABLES)
                print("  [Mode: include open-source collection configs]")

        if clear_config:
            tables.extend(CONFIG_SYSTEM_TABLES)
            print("  [Mode: include system config tables]")

        if full_reset:
            tables.extend(CONFIG_TABLES)
            print("  [Mode: full reset]")

        # Use TRUNCATE CASCADE to force-clear, ignoring FK constraints
        # Process in reverse dependency order, or TRUNCATE all at once
        if tables:
            try:
                # Build single TRUNCATE statement; CASCADE handles FKs
                table_list = ", ".join(tables)
                await session.execute(text(f"TRUNCATE TABLE {table_list} CASCADE"))
                await session.commit()
                print(f"  [OK] Cleared{len(tables)} tables (CASCADE)")
            except Exception as e:
                error_msg = str(e)
                # If TRUNCATE fails, try DELETE row-by-row
                print(f"  [WARN] TRUNCATE failed: {error_msg[:100]}...")
                print("  [INFO] Trying row-by-row...")

                # Disable FK checks (PostgreSQL)
                await session.execute(text("SET session_replication_role = 'replica'"))

                truncated_count = 0
                for table in tables:
                    try:
                        await session.execute(text(f"DELETE FROM {table}"))
                        truncated_count += 1
                        print(f"  [OK] {table}")
                    except Exception as e2:
                        error_msg = str(e2)
                        if "does not exist" in error_msg or "does not exist" in error_msg:
                            print(f"  [SKIP] {table} (does not exist)")
                        else:
                            print(f"  [WARN] {table}: {error_msg[:50]}...")
                        continue

                # Re-enable FK checks
                await session.execute(text("SET session_replication_role = 'origin'"))
                await session.commit()
                print(f"\nCleared{truncated_count} tables")


async def clear_cache():
    """Clear Redis cache"""
    print("\n" + "="*60)
    print("Step 2: Clear cache")
    print("="*60)

    try:
        from app.core.cache import get_cache_connection
        from app.domains.shared.services.cache_service import CacheService

        cache_conn = await get_cache_connection()
        if cache_conn.is_available:
            cache = CacheService(cache_conn)
            deleted = await cache.delete_pattern("*")
            print(f"  [OK] Cleared{deleted} cache keys")
        else:
            print("  [SKIP] Redis not enabled or unavailable")
    except Exception as e:
        print(f"  [WARN] Cache clear failed: {e}")


async def seed_admin_user():
    """Seed admin user"""
    print("\n" + "="*60)
    print("Step 3: Seed admin user")
    print("="*60)

    async with AsyncSessionLocal() as session:
        # Check if already exists
        from sqlalchemy import select
        result = await session.execute(
            select(UserAccount).where(UserAccount.username == "admin")
        )
        if result.scalar_one_or_none():
            print("  Admin user exists, skipping")
            return

        admin_password = hash_password("admin123")
        admin = UserAccount(
            username="admin",
            email="admin@talent.local",
            password_hash=admin_password,
            role_type=UserRoleType.SUPER_ADMIN.value,
            is_active=True,
            status="active",
            display_name="System Admin",
        )
        session.add(admin)
        await session.flush()

        # Grant all-school access scope
        admin_scope = UserSchoolScope(
            user_id=admin.user_id,
            scope_type=ScopeType.ALL.value,
            scope_value="*",
            granted_by=admin.user_id,
            granted_at=datetime.now(),
            is_active=True,
        )
        session.add(admin_scope)

        # Create demo user
        demo_password = hash_password("demo123")
        demo = UserAccount(
            username="demo",
            email="demo@talent.local",
            password_hash=demo_password,
            role_type=UserRoleType.USER.value,
            is_active=True,
            status="active",
            display_name="Demo User",
        )
        session.add(demo)

        await session.commit()
        print("  [OK] Admin: admin / admin123")
        print("  [OK] Demo User: demo / demo123")


async def seed_tech_domains():
    """Seed tech domains"""
    print("\n" + "="*60)
    print("Step 4: Seed tech domains")
    print("="*60)

    async with AsyncSessionLocal() as session:
        from sqlalchemy import select

        # Check if already exists
        result = await session.execute(select(TechDomain).limit(1))
        if result.scalar_one_or_none():
            print("  Tech domains exist, skipping")
            return

        for domain_data in TECH_DOMAINS_DATA:
            domain = TechDomain(**domain_data)
            session.add(domain)
            print(f"  [OK] {domain_data['domain_name']}")

        await session.commit()


async def seed_venues():
    """Seed venue configs"""
    print("\n" + "="*60)
    print("Step 5: Seed venue configs")
    print("="*60)

    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        # Get all tech domains
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

                # Lookup OpenAlex ID
                openalex_id = KNOWN_OPENALEX_SOURCES.get(venue_code)

                # Check if Venue exists
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

                # Check binding exists
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

            print(f"  [OK] {tech_domain.domain_name}: {len(venues_data)} venues")

        await session.commit()
        print(f"\n  Venues created: {stats['venues_created']}, Bindings created: {stats['bindings_created']}")


async def seed_open_source_repo_configs():
    """Seed open-source repo configs"""
    print("\n" + "="*60)
    print("Step 5.5: Seed open-source repo configs")
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
                print(f"  [SKIP] {config_data['repo_full_name']} already exists")
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
    """Seed statistics snapshot"""
    print("\n" + "="*60)
    print("Step 6: Seed statistics snapshot")
    print("="*60)

    async with AsyncSessionLocal() as session:
        from sqlalchemy import select

        # Check if active snapshot exists
        result = await session.execute(
            select(OverviewStatSnapshot).where(OverviewStatSnapshot.is_active == 1)
        )
        if result.scalar_one_or_none():
            print("  Snapshot exists, skipping")
            return

        version = f"v1.0_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Get tech domain count
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
        print(f"  [OK] Initial snapshot: {version}")
        print(f"  [OK] Tech domain count: {tech_domain_count}")


async def init_system(
    full_reset: bool = False,
    clear_config: bool = False,
    clear_collection: bool = False,
    domain: str = "all",
):
    """Run full initialization flow.
    Args:
        full_reset: Full reset (also clears users, tech domains)
        clear_config: Also clear system config tables (sys_config)
        clear_collection: Also clear collection config tables (tasks, repo configs)
        domain: Domain to init (academic / open_source / all, default all)
    """
    print("\n" + "="*60)
    print("AI Talent Platform - System Data Initialization")
    print("="*60)

    start_time = datetime.now()

    # 1. Clear data tables
    await truncate_tables(full_reset, clear_config, clear_collection, domain)

    # 2. Clear cache
    await clear_cache()

    # Only run on full reset
    if full_reset:
        # 3. Seed admin user
        await seed_admin_user()

        # 4. Seed tech domains
        await seed_tech_domains()

        # 5. Seed venues
        await seed_venues()

    # 5.5 Seed open-source repo configs (idempotent)
    if domain in ("all", "open_source"):
        await seed_open_source_repo_configs()

    # 6. Seed statistics snapshot
    await seed_statistics_snapshot()

    # Done
    elapsed = (datetime.now() - start_time).total_seconds()

    print("\n" + "="*60)
    print("Initialization complete")
    print("="*60)
    print(f"Elapsed: {elapsed:.2f}s")

    if full_reset:
        print("\nDefault accounts:")
        print("  Admin: admin / admin123")
        print("  Demo: demo / demo123")
        print("\n[!] Change default password in production")
    else:
        print("[TIP] Business data cleared, user and tech domain configs retained")
        if not clear_collection:
            print("[TIP] Collection configs (tasks, repo configs) retained; use --clear-collection to remove")
        if not clear_config:
            print("[TIP] System config (sys_config) retained; use --clear-config to remove")
        print("[TIP] Country data lives in app/constants/countries.py")


def main():
    parser = argparse.ArgumentParser(
        description="System data initialization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/init_system.py                       # Interactive confirm
    python scripts/init_system.py --force               # Skip confirmation
    python scripts/init_system.py --domain academic     # Academic only
    python scripts/init_system.py --domain open_source  # Open source only
    python scripts/init_system.py --full                # Full reset
    python scripts/init_system.py --clear-collection    # Also clear collection configs
    python scripts/init_system.py --clear-config        # Also clear sys_config
    python scripts/init_system.py --full --force        # Full reset, no confirm

Notes:
  - Default clears business data; use --domain to restrict
  - Default retains collection configs; use --clear-collection to remove
  - Default retains sys_config; use --clear-config to remove
  - Country data lives in app/constants/countries.py
        """
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Skip confirmation prompt"
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Full reset (also clears users, tech domains, etc.)"
    )
    parser.add_argument(
        "--clear-collection",
        action="store_true",
        help="Also clear collection config tables (tasks, repo configs)"
    )
    parser.add_argument(
        "--clear-config",
        action="store_true",
        help="Also clear system config tables (sys_config)"
    )
    parser.add_argument(
        "--domain",
        choices=["academic", "open_source", "all"],
        default="all",
        help="Domain to clear (default: all)"
    )

    args = parser.parse_args()

    # Confirmation prompt
    if not args.force:
        domain_label = {"academic": "Academic", "open_source": "Open Source", "all": "All business data"}
        print(f"\n[!] WARNING: This will clear {domain_label[args.domain]}!")
        if args.full:
            print("[!] NOTE: Full reset will also clear users and tech domains")
        if args.clear_collection:
            print("[!] NOTE: Collection configs (tasks, repo configs) will also be cleared")
        if args.clear_config:
            print("[!] NOTE: System config (sys_config) will also be cleared")
        confirm = input("\nConfirm? (y/N): ").strip().lower()
        if confirm != "y":
            print("Cancelled")
            return

    asyncio.run(init_system(full_reset=args.full, clear_config=args.clear_config, clear_collection=args.clear_collection, domain=args.domain))


if __name__ == "__main__":
    main()
