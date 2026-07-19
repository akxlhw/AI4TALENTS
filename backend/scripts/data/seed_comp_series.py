"""Seed comp_series rows from the competition domain registry.

Idempotent: existing series (matched by code) are left untouched.

Usage:
    cd backend && uv run python scripts/data/seed_comp_series.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.domains.competition.constants.series import SERIES
from app.domains.competition.models.competition import CompSeries


async def main() -> None:
    async with AsyncSessionLocal() as session:
        inserted = 0
        for item in SERIES:
            exists = await session.scalar(
                select(CompSeries.series_id).where(CompSeries.code == item["code"])
            )
            if exists:
                continue
            session.add(
                CompSeries(
                    code=item["code"],
                    name=item["name"],
                    name_en=item.get("name_en"),
                    homepage=item.get("homepage"),
                    description=item.get("description"),
                    is_enabled=item.get("is_enabled", True),
                )
            )
            inserted += 1
        await session.commit()
        print(f"Seed complete: {inserted} series inserted, {len(SERIES) - inserted} already existed.")


if __name__ == "__main__":
    asyncio.run(main())
