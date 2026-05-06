"""
Re-sync std_author to Talent table with CS score filtering.

This script uses the ServingLayerOrchestrator for proper syncing.

Run with: python scripts/resync_talents_v2.py
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
from app.domains.academic.services.common.cs_concepts import CS_SCORE_THRESHOLD

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def resync_talents():
    """Re-sync all talents with CS score filtering using direct SQL."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///./talent.db",
        echo=False
    )

    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        # Count current state
        from sqlalchemy import func

        result = await session.execute(select(func.count(Talent.talent_id)))
        current_talents = result.scalar()

        result = await session.execute(select(func.count(StdAuthor.std_author_id)))
        total_std_authors = result.scalar()

        result = await session.execute(
            select(func.count(StdAuthor.std_author_id))
            .where(StdAuthor.cs_concepts_score >= CS_SCORE_THRESHOLD)
        )
        cs_qualified = result.scalar()

        logger.info(f"Current talents: {current_talents}")
        logger.info(f"Total std_authors: {total_std_authors}")
        logger.info(f"CS qualified (>= {CS_SCORE_THRESHOLD}): {cs_qualified}")

        # Delete all existing talents and role profiles
        logger.info("Deleting existing talent records...")
        await session.execute(delete(RoleProfile))
        await session.execute(delete(Talent))
        await session.commit()
        logger.info("Deleted all talent records")

        # Simple sync - create Talent records directly
        logger.info("Creating Talent records from qualified std_authors...")

        # Get qualified authors
        result = await session.execute(
            select(StdAuthor)
            .where(StdAuthor.cs_concepts_score >= CS_SCORE_THRESHOLD)
        )
        qualified_authors = result.scalars().all()

        logger.info(f"Processing {len(qualified_authors)} qualified authors...")

        created = 0
        errors = 0

        for author in qualified_authors:
            try:
                # Create Talent record directly
                from app.domains.shared.models.enums import VisibilityStatus
                from datetime import datetime, timezone

                talent = Talent(
                    std_author_id=author.std_author_id,
                    source_type="openalex",
                    source_record_id=author.openalex_author_id,
                    name=author.name_normalized or author.name_original,
                    name_en=author.name_original,
                    orcid=author.orcid,
                    role_type="researcher",
                    role_confidence=0.8,
                    works_count=author.works_count or 0,
                    cited_by_count=author.cited_by_count or 0,
                    h_index=author.h_index or 0,
                    openalex_topics=author.openalex_topics or [],
                    visibility_status=VisibilityStatus.ACTIVE.value,
                    is_visible=True,
                )

                session.add(talent)
                created += 1

                if created % 1000 == 0:
                    await session.commit()
                    logger.info(f"Created {created} talents...")

            except Exception as e:
                errors += 1
                if errors <= 5:
                    logger.error(f"Error creating talent for {author.openalex_author_id}: {e}")

        await session.commit()

        logger.info("=" * 50)
        logger.info("Summary:")
        logger.info(f"  Created: {created}")
        logger.info(f"  Errors: {errors}")

        # Verify final count
        result = await session.execute(select(func.count(Talent.talent_id)))
        final_talents = result.scalar()
        logger.info(f"Final talent count: {final_talents}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(resync_talents())
