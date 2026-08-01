"""
Seed tech direction data (core_tech_direction).

填充技术方向明细数据（V5.0.0 行业人才库前置依赖）。

core_tech_direction 此前只有各领域一个占位 DEFAULT 行，开源域
os_repo_config.tech_direction_id 已引用该表。本脚本手工定义技术方向清单，
按 direction_code 幂等插入（已存在的编码跳过，不修改既有行）。

用法（Windows GBK 控制台务必加 -X utf8）：
    cd backend && uv run python -X utf8 scripts/data/seed_tech_directions.py
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

# Import the full model registry so ORM relationships (e.g. VenueTechBinding)
# resolve when only the tech_domain module is used here.
import app.model_registry  # noqa: E402, F401
from app.core.config import settings  # noqa: E402
from app.domains.academic.models.tech_domain import TechDirection, TechDomain  # noqa: E402

# Silence SQLAlchemy engine echo on GBK consoles
logging.getLogger("sqlalchemy.engine").setLevel(logging.CRITICAL)

# 手工定义的技术方向清单：(domain_code, [(direction_code, 中文名, 英文名), ...])
TECH_DIRECTIONS_DATA: dict[str, list[tuple[str, str, str]]] = {
    "ai": [
        ("llm", "大模型", "Large Language Models"),
        ("llm_inference", "推理优化", "LLM Inference Optimization"),
        ("cv", "计算机视觉", "Computer Vision"),
        ("nlp", "自然语言处理", "Natural Language Processing"),
        ("speech", "语音技术", "Speech Technology"),
        ("multimodal", "多模态", "Multimodal Learning"),
        ("recsys", "推荐系统", "Recommendation Systems"),
        ("search_tech", "搜索技术", "Search Technology"),
        ("rl", "强化学习", "Reinforcement Learning"),
        ("ai_infra", "AI 基础设施", "AI Infrastructure"),
        ("mlops", "MLOps", "MLOps"),
        ("embodied_ai", "具身智能", "Embodied AI"),
        ("autonomous_driving", "自动驾驶", "Autonomous Driving"),
        ("ai_safety", "AI 安全与对齐", "AI Safety & Alignment"),
    ],
    "robotics": [
        ("robot_perception", "机器人感知", "Robot Perception"),
        ("motion_planning", "运动规划与控制", "Motion Planning & Control"),
    ],
    "data_science": [
        ("data_engineering", "数据工程", "Data Engineering"),
        ("bi_analytics", "商业智能与数据分析", "BI & Analytics"),
    ],
    "systems": [
        ("distributed_systems", "分布式系统", "Distributed Systems"),
        ("databases", "数据库", "Databases"),
    ],
    "security": [
        ("network_security", "网络安全", "Network Security"),
        ("privacy_computing", "隐私计算", "Privacy Computing"),
    ],
}


async def seed_tech_directions() -> None:
    """Insert missing tech directions idempotently (skip existing codes)."""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        domain_rows = (await session.execute(select(TechDomain))).scalars().all()
        domains = {d.domain_code: d for d in domain_rows}

        existing = (await session.execute(select(TechDirection.direction_code))).scalars().all()
        existing_codes = set(existing)

        inserted = 0
        skipped = 0
        for domain_code, directions in TECH_DIRECTIONS_DATA.items():
            domain = domains.get(domain_code)
            if domain is None:
                print(f"[warn] tech domain '{domain_code}' not found, skipped")
                continue
            for sort_order, (code, name, name_en) in enumerate(directions, start=1):
                if code in existing_codes:
                    skipped += 1
                    continue
                session.add(
                    TechDirection(
                        direction_code=code,
                        direction_name=name,
                        direction_name_en=name_en,
                        tech_domain_id=domain.tech_domain_id,
                        sort_order=sort_order,
                        is_enabled=True,
                    )
                )
                existing_codes.add(code)
                inserted += 1

        await session.commit()
        print(f"Seed tech directions done: inserted={inserted}, skipped(existing)={skipped}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_tech_directions())
