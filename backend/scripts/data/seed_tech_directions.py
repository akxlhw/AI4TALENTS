"""Seed tech directions from the shared taxonomy (v2).

Inserts missing directions idempotently (skip existing codes, never modify).
Direction data — including the element layer (element_code/element_name) —
comes from app/domains/shared/constants/tech_taxonomy.py, the single source
of truth for the 10-domain / 34-element / 75-direction taxonomy.

Run: cd backend && uv run python scripts/data/seed_tech_directions.py
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.domains.academic.models.tech_domain import TechDirection, TechDomain
from app.domains.shared.constants.tech_taxonomy import (
    TECH_DIRECTIONS,
    TECH_DOMAINS,
    TECH_ELEMENTS,
)


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
        for sort_order, (code, name, name_en, element) in enumerate(TECH_DIRECTIONS, start=1):
            if code in existing_codes:
                skipped += 1
                continue
            el = TECH_ELEMENTS[element]
            domain = domains.get(el["domain"])
            if domain is None:
                print(f"[warn] tech domain '{el['domain']}' not found, skipped {code}")
                continue
            session.add(
                TechDirection(
                    direction_code=code,
                    direction_name=name,
                    direction_name_en=name_en,
                    element_code=element,
                    element_name=el["name"],
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
