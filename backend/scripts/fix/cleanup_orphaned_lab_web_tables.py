"""Cleanup orphaned lw_* tables from the deprecated lab_web_site branch.

Context: the feature/lab-web-talent-collection branch created two migrations
(050_add_lab_web_domain, 051_add_lab_web_site) that build lw_site_config and
lw_site_raw_page tables. A deployment environment that ran that branch has
alembic_version = '051_add_lab_web_site' recorded, but main no longer ships
those migration files (main's lab domain uses lab_talent via 050_add_lab_talent_table).

Result: `alembic upgrade head` fails with
"Can't locate revision identified by '051_add_lab_web_site'".

This script:
  1. Drops the orphaned lw_site_raw_page and lw_site_config tables.
  2. Resets alembic_version to '049_add_genealogy_tables' (the last revision
     shared by both branches), so a subsequent `alembic upgrade head` applies
     main's 050_add_lab_talent_table cleanly.

Idempotent: safe to re-run (skips already-dropped tables, no-ops if alembic
version is already on the main chain).

Usage:
    # Dry run (shows what would happen, makes no changes)
    uv run python scripts/fix/cleanup_orphaned_lab_web_tables.py --dry-run

    # Apply
    uv run python scripts/fix/cleanup_orphaned_lab_web_tables.py
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add backend root to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy import text

from app.core.database import AsyncSessionLocal

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("cleanup_lw_tables")

# The revision main and the deprecated branch both share.
SHARED_BASE_REVISION = "049_add_genealogy_tables"
ORPHANED_REVISION = "051_add_lab_web_site"
ORPHANED_TABLES = ["lw_site_raw_page", "lw_site_config"]


async def get_current_revision(session) -> str | None:
    result = await session.execute(text("SELECT version_num FROM alembic_version"))
    row = result.fetchone()
    return row[0] if row else None


async def table_exists(session, table_name: str) -> bool:
    result = await session.execute(
        text("SELECT to_regclass(:t)"),  # returns NULL if not exists
        {"t": f"public.{table_name}"},
    )
    return result.fetchone()[0] is not None


async def run(dry_run: bool) -> None:
    async with AsyncSessionLocal() as session:
        current = await get_current_revision(session)
        logger.info("Current alembic_version: %s", current)

        if current is None:
            logger.error("alembic_version table is empty or missing. Aborting.")
            return

        # Detect tables to drop
        existing_tables = []
        for t in ORPHANED_TABLES:
            if await table_exists(session, t):
                existing_tables.append(t)
        logger.info("Orphaned tables present: %s", existing_tables or "(none)")

        if current != ORPHANED_REVISION and not existing_tables:
            logger.info(
                "Nothing to do: alembic is at %s and no lw_* tables found. "
                "This database is not on the orphaned branch state.",
                current,
            )
            return

        if dry_run:
            logger.info("[DRY RUN] Would drop tables: %s", existing_tables)
            logger.info(
                "[DRY RUN] Would set alembic_version %s -> %s",
                current,
                SHARED_BASE_REVISION,
            )
            return

        # 1. Drop orphaned tables (raw page first, depends on site_config via FK)
        for t in reversed(ORPHANED_TABLES):
            if await table_exists(session, t):
                logger.info("Dropping table %s ...", t)
                await session.execute(text(f'DROP TABLE IF EXISTS "{t}" CASCADE'))

        # 2. Reset alembic_version to the shared base so main's 050 applies next
        logger.info("Resetting alembic_version %s -> %s", current, SHARED_BASE_REVISION)
        await session.execute(
            text("UPDATE alembic_version SET version_num = :v"),
            {"v": SHARED_BASE_REVISION},
        )

        await session.commit()
        logger.info("Done. Now run: alembic upgrade head")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without modifying the database",
    )
    args = parser.parse_args()

    if not args.dry_run:
        confirm = input(
            "This will DROP lw_* tables and reset alembic_version. Type 'yes' to proceed: "
        )
        if confirm.strip().lower() != "yes":
            logger.info("Aborted by user.")
            return 1

    asyncio.run(run(args.dry_run))
    return 0


if __name__ == "__main__":
    sys.exit(main())
