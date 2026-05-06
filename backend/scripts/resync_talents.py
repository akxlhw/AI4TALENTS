"""
Re-sync std_author to Talent table with CS score filtering.

This script will:
1. Delete all existing Talent records
2. Re-sync from std_author with proper CS score filtering

Run with: python scripts/resync_talents.py [--dry-run]
"""
import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.domains.academic.models.talent import Talent, RoleProfile
from app.domains.academic.models.standardized import StdAuthor
from app.domains.academic.models.school import School
from app.domains.academic.services.sync.author_sync import AuthorSyncService
from app.domains.academic.services.common.cs_concepts import CS_SCORE_THRESHOLD

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def resync_talents(dry_run: bool = False):
    """Re-sync all talents with CS score filtering."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///./talent.db",
        echo=False
    )

    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        # Count current state
        result = await session.execute(select(Talent))
        current_talents = len(result.all())

        result = await session.execute(select(StdAuthor))
        total_std_authors = len(result.all())

        result = await session.execute(
            select(StdAuthor).where(StdAuthor.cs_concepts_score >= CS_SCORE_THRESHOLD)
        )
        cs_qualified = len(result.all())

        logger.info(f"Current talents: {current_talents}")
        logger.info(f"Total std_authors: {total_std_authors}")
        logger.info(f"CS qualified (>= {CS_SCORE_THRESHOLD}): {cs_qualified}")

        if dry_run:
            logger.info("DRY RUN - no changes will be made")
            await engine.dispose()
            return

        # Delete all existing talents and role profiles
        logger.info("Deleting existing talent records...")
        await session.execute(delete(RoleProfile))
        await session.execute(delete(Talent))
        await session.commit()
        logger.info("Deleted all talent records")

        # Re-sync with CS score filtering
        logger.info("Re-syncing talents with CS score filtering...")
        sync_service = AuthorSyncService(session)

        result = await session.execute(
            select(StdAuthor).where(StdAuthor.cs_concepts_score >= CS_SCORE_THRESHOLD)
        )
        qualified_authors = result.scalars().all()

        stats = {
            "synced": 0,
            "created": 0,
            "updated": 0,
            "filtered": 0,
            "errors": 0,
        }

        for i, std_author in enumerate(qualified_authors):
            try:
                talent, is_new = await sync_service.sync_author_to_talent(std_author)
                if talent:
                    stats["synced"] += 1
                    if is_new:
                        stats["created"] += 1
                    else:
                        stats["updated"] += 1
                else:
                    stats["filtered"] += 1

                if (i + 1) % 1000 == 0:
                    logger.info(f"Processed {i + 1}/{len(qualified_authors)}...")
                    await session.commit()

            except Exception as e:
                stats["errors"] += 1
                if stats["errors"] <= 5:
                    logger.error(f"Error syncing {std_author.openalex_author_id}: {e}")

        await session.commit()

        logger.info("=" * 50)
        logger.info("Summary:")
        logger.info(f"  Synced: {stats['synced']}")
        logger.info(f"  Created: {stats['created']}")
        logger.info(f"  Updated: {stats['updated']}")
        logger.info(f"  Filtered: {stats['filtered']}")
        logger.info(f"  Errors: {stats['errors']}")

        # Verify final count
        result = await session.execute(select(Talent))
        final_talents = len(result.all())
        logger.info(f"Final talent count: {final_talents}")

    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Re-sync talents with CS filtering")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without applying")
    args = parser.parse_args()

    asyncio.run(resync_talents(dry_run=args.dry_run))
