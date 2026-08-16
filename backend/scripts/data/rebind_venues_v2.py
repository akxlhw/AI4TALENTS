"""
Rebind venues to taxonomy v2 domains + add venues for empty domains.

Taxonomy v2 (migration 062): 10 domains. Existing 53 venue bindings were
migrated with legacy semantics, leaving basic_software / ai_apps / multimedia /
autonomous_driving with zero venues. This script:

1. Rebinds existing venues to the v2 domain that matches their field:
   - basic_software ← osdi/sosp/eurosys/asplos (OS/体系结构), sigmod/vldb/icde (数据库与存储)
   - ai_apps        ← cvpr/iccv/eccv/t-pami (CV应用), kdd (AI应用)
   - multimedia     ← tvcg/vis (图形图像)
2. Adds new venues (with OpenAlex source IDs) for domains that had none:
   - autonomous_driving ← t-its (T-ITS 期刊), iv (IV 年会)
   - multimedia         ← tog (SIGGRAPH/TOG), tmm (IEEE TMM), tomm (ACM TOMM)

Idempotent: re-running produces the same end state.

Usage:
    cd backend && uv run python -X utf8 scripts/data/rebind_venues_v2.py
"""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import select  # noqa: E402

import app.model_registry  # noqa: E402,F401  (registers all ORM models for relationship resolution)
from app.core.database import AsyncSessionLocal  # noqa: E402
from app.domains.academic.models.tech_domain import TechDomain  # noqa: E402
from app.domains.academic.models.venue import Venue, VenueTechBinding  # noqa: E402

logging.getLogger("sqlalchemy.engine").setLevel(logging.CRITICAL)

# venue_code → new domain_code (rebinding existing venues)
REBIND: dict[str, str] = {
    # → basic_software
    "osdi": "basic_software",
    "sosp": "basic_software",
    "eurosys": "basic_software",
    "asplos": "basic_software",
    "sigmod": "basic_software",
    "vldb": "basic_software",
    "icde": "basic_software",
    # → ai_apps
    "cvpr": "ai_apps",
    "iccv": "ai_apps",
    "eccv": "ai_apps",
    "t-pami": "ai_apps",
    "kdd": "ai_apps",
    # → multimedia
    "tvcg": "multimedia",
    "vis": "multimedia",
}

# New venues: (code, name, name_en, type, openalex_source_id, publisher, domain)
NEW_VENUES: list[dict] = [
    {
        "venue_code": "t-its",
        "venue_name": "IEEE Transactions on Intelligent Transportation Systems",
        "venue_name_en": "IEEE Transactions on Intelligent Transportation Systems",
        "venue_type": "journal",
        "openalex_source_id": "S144771191",
        "publisher": "IEEE",
        "domain": "autonomous_driving",
    },
    {
        "venue_code": "iv",
        "venue_name": "IEEE Intelligent Vehicles Symposium",
        "venue_name_en": "IEEE Intelligent Vehicles Symposium (IV)",
        "venue_type": "conference",
        "openalex_source_id": "S4210198592",
        "publisher": "IEEE",
        "domain": "autonomous_driving",
    },
    {
        "venue_code": "tog",
        "venue_name": "ACM Transactions on Graphics (SIGGRAPH)",
        "venue_name_en": "ACM Transactions on Graphics",
        "venue_type": "journal",
        "openalex_source_id": "S185367456",
        "publisher": "ACM",
        "domain": "multimedia",
    },
    {
        "venue_code": "tmm",
        "venue_name": "IEEE Transactions on Multimedia",
        "venue_name_en": "IEEE Transactions on Multimedia",
        "venue_type": "journal",
        "openalex_source_id": "S137030581",
        "publisher": "IEEE",
        "domain": "multimedia",
    },
    {
        "venue_code": "tomm",
        "venue_name": "ACM Transactions on Multimedia Computing, Communications and Applications",
        "venue_name_en": "ACM TOMM",
        "venue_type": "journal",
        "openalex_source_id": "S19610489",
        "publisher": "ACM",
        "domain": "multimedia",
    },
]


async def main() -> None:
    async with AsyncSessionLocal() as session:
        domains = {
            d.domain_code: d.tech_domain_id
            for d in (await session.execute(select(TechDomain))).scalars().all()
        }
        for v in NEW_VENUES:
            assert v["domain"] in domains, f"unknown domain {v['domain']}"
        for dom in REBIND.values():
            assert dom in domains, f"unknown domain {dom}"

        # 1. Rebind existing venues
        rebound = 0
        for venue_code, domain_code in REBIND.items():
            venue = (
                await session.execute(select(Venue).where(Venue.venue_code == venue_code))
            ).scalar_one_or_none()
            if venue is None:
                print(f"  ! venue {venue_code} not found, skip")
                continue
            binding = (
                await session.execute(
                    select(VenueTechBinding).where(VenueTechBinding.venue_id == venue.venue_id)
                )
            ).scalar_one_or_none()
            target = domains[domain_code]
            if binding is None:
                session.add(VenueTechBinding(venue_id=venue.venue_id, tech_domain_id=target))
                rebound += 1
                print(f"  + {venue_code}: (new binding) → {domain_code}")
            elif binding.tech_domain_id != target:
                print(f"  ~ {venue_code}: rebound → {domain_code}")
                binding.tech_domain_id = target
                rebound += 1

        # 2. Add new venues + bindings
        added = 0
        for spec in NEW_VENUES:
            domain_id = domains[spec.pop("domain")]
            venue = (
                await session.execute(select(Venue).where(Venue.venue_code == spec["venue_code"]))
            ).scalar_one_or_none()
            if venue is None:
                venue = Venue(
                    venue_code=spec["venue_code"],
                    venue_name=spec["venue_name"],
                    venue_name_en=spec["venue_name_en"],
                    venue_type=spec["venue_type"],
                    openalex_source_id=spec["openalex_source_id"],
                    publisher=spec["publisher"],
                )
                session.add(venue)
                await session.flush()
                added += 1
                print(f"  + new venue {spec['venue_code']} ({spec['openalex_source_id']})")
            elif not venue.openalex_source_id:
                venue.openalex_source_id = spec["openalex_source_id"]
            binding = (
                await session.execute(
                    select(VenueTechBinding).where(VenueTechBinding.venue_id == venue.venue_id)
                )
            ).scalar_one_or_none()
            if binding is None:
                session.add(VenueTechBinding(venue_id=venue.venue_id, tech_domain_id=domain_id))
            elif binding.tech_domain_id != domain_id:
                binding.tech_domain_id = domain_id

        await session.commit()
        print(f"\nrebound={rebound}, added_venues={added}")

        # 3. Print final distribution
        from sqlalchemy import func

        rows = (
            await session.execute(
                select(TechDomain.domain_code, func.count())
                .select_from(VenueTechBinding)
                .join(TechDomain, TechDomain.tech_domain_id == VenueTechBinding.tech_domain_id)
                .group_by(TechDomain.domain_code)
            )
        ).all()
        print("final distribution:", dict(rows))


if __name__ == "__main__":
    asyncio.run(main())
