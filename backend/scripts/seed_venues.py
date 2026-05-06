"""
Seed venues from TechDomain collect_sources.
从技术领域的采集源初始化 Venue 表和 VenueTechBinding �?
用法:
    python -m backend.scripts.seed_venues
"""
import asyncio
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.domains.academic.models.tech_domain import TechDomain
from app.domains.academic.models.venue import Venue, VenueTechBinding
from app.domains.academic.repositories.venue_repository import VenueRepository, VenueTechBindingRepository


# 已知�?OpenAlex Source ID 映射
# 格式: venue_code -> openalex_source_id
KNOWN_OPENALEX_SOURCES = {
    # AI/ML Top Conferences
    "neurips": "S137534324",
    "icml": "S216152413",
    "iclr": "S2764757099",
    "cvpr": "S11712273",
    "eccv": "S2736275573",
    "iccv": "S99458316",
    "aaai": "S1474501",
    "ijcai": "S1474504",
    "acl": "S816424",
    "emnlp": "S99460462",
    "naacl": "S2744807627",
    "coling": "S2766172945",

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
    "ccs": "S2764979084",
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
    "kdd": "S816468",
    "www": "S2766031128",
    "wsdm": "S2766041346",
    "recsys": "S2766042642",
    "icdm": "S99460372",
    "sdm": "S2765931314",
}


async def seed_venues(
    session: AsyncSession,
    dry_run: bool = False,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    �?TechDomain.collect_sources 初始�?Venue �?VenueTechBinding

    Args:
        session: 数据库会�?        dry_run: 是否只预览不执行
        verbose: 是否打印详细信息

    Returns:
        dict: 执行统计
    """
    stats = {
        "tech_domains_processed": 0,
        "venues_created": 0,
        "venues_updated": 0,
        "bindings_created": 0,
        "bindings_updated": 0,
        "errors": []
    }

    venue_repo = VenueRepository(session)
    binding_repo = VenueTechBindingRepository(session)

    # 获取所有技术领�?    result = await session.execute(
        select(TechDomain).where(TechDomain.is_enabled == True)
    )
    tech_domains = result.scalars().all()

    if verbose:
        print(f"\n{'='*60}")
        print(f"Venue Seeding Script")
        print(f"{'='*60}")
        print(f"Found {len(tech_domains)} enabled tech domains")
        print(f"Dry run: {dry_run}")
        print(f"{'='*60}\n")

    for tech_domain in tech_domains:
        stats["tech_domains_processed"] += 1

        if not tech_domain.collect_sources:
            if verbose:
                print(f"[{tech_domain.domain_code}] No collect sources, skipping")
            continue

        sources = tech_domain.collect_sources
        if verbose:
            print(f"\n[{tech_domain.domain_code}] Processing {len(sources)} sources...")

        for idx, source in enumerate(sources):
            source_id = source.get("id", "")
            source_name = source.get("name", source_id)
            source_type = source.get("type", "conference")

            if not source_id:
                stats["errors"].append(f"Missing source ID in {tech_domain.domain_code}")
                continue

            # 生成 venue_code
            venue_code = source_id.lower().replace(" ", "-").replace("_", "-")

            # 查找 OpenAlex Source ID
            openalex_id = KNOWN_OPENALEX_SOURCES.get(venue_code)
            if not openalex_id:
                # 尝试直接使用 source_id 作为 OpenAlex ID
                if source_id.startswith("S"):
                    openalex_id = source_id

            try:
                # 检�?Venue 是否存在
                existing_venue = await venue_repo.get_by_code(venue_code)

                if existing_venue:
                    # 更新现有 Venue
                    existing_venue.venue_name = source_name
                    existing_venue.venue_type = source_type
                    if openalex_id:
                        existing_venue.openalex_source_id = openalex_id
                    stats["venues_updated"] += 1
                    venue = existing_venue
                    if verbose:
                        print(f"  [UPDATE] {venue_code}: {source_name} ({source_type})")
                else:
                    # 创建�?Venue
                    venue = Venue(
                        venue_code=venue_code,
                        venue_name=source_name,
                        venue_type=source_type,
                        openalex_source_id=openalex_id,
                        is_enabled=True,
                    )
                    venue = await venue_repo.create(venue)
                    stats["venues_created"] += 1
                    if verbose:
                        print(f"  [CREATE] {venue_code}: {source_name} ({source_type})" +
                              (f" -> OpenAlex: {openalex_id}" if openalex_id else ""))

                # 检查绑定是否已存在
                existing_binding = await binding_repo.get_by_venue_and_tech(
                    venue.venue_id, tech_domain.tech_domain_id
                )

                if existing_binding:
                    existing_binding.priority = idx
                    existing_binding.is_enabled = True
                    stats["bindings_updated"] += 1
                else:
                    # 创建新绑�?                    binding = VenueTechBinding(
                        venue_id=venue.venue_id,
                        tech_domain_id=tech_domain.tech_domain_id,
                        priority=idx,
                        collect_status="pending",
                        is_enabled=True,
                    )
                    await binding_repo.create(binding)
                    stats["bindings_created"] += 1

            except Exception as e:
                error_msg = f"Error processing {venue_code}: {str(e)}"
                stats["errors"].append(error_msg)
                if verbose:
                    print(f"  [ERROR] {error_msg}")

    if not dry_run:
        await session.commit()
        if verbose:
            print(f"\n{'='*60}")
            print(f"Changes committed to database")
    else:
        if verbose:
            print(f"\n{'='*60}")
            print(f"Dry run - no changes made")

    if verbose:
        print(f"\n{'='*60}")
        print(f"Summary:")
        print(f"  Tech domains processed: {stats['tech_domains_processed']}")
        print(f"  Venues created: {stats['venues_created']}")
        print(f"  Venues updated: {stats['venues_updated']}")
        print(f"  Bindings created: {stats['bindings_created']}")
        print(f"  Bindings updated: {stats['bindings_updated']}")
        print(f"  Errors: {len(stats['errors'])}")
        print(f"{'='*60}\n")

    return stats


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Seed venues from TechDomain collect_sources")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without committing")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress detailed output")
    args = parser.parse_args()

    async with AsyncSessionLocal() as session:
        await seed_venues(
            session=session,
            dry_run=args.dry_run,
            verbose=not args.quiet
        )


if __name__ == "__main__":
    asyncio.run(main())
