"""
Recalculate CS concepts score for all std_author records.

Run with: python scripts/recalculate_cs_scores.py [--dry-run]
"""
import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.domains.academic.models.standardized import StdAuthor
from app.domains.academic.models.raw_data import RawAuthor
from app.domains.academic.services.common.cs_concepts import CORE_CS_CONCEPTS

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def calculate_cs_score(raw_json: str) -> float:
    """Calculate CS background score from OpenAlex x_concepts."""
    if not raw_json:
        return 0.0

    try:
        data = json.loads(raw_json)
        concepts = data.get("x_concepts", [])

        cs_score = 0.0
        for concept in concepts:
            concept_id = str(concept.get("id", ""))
            if concept_id in CORE_CS_CONCEPTS:
                score = concept.get("score", 0)
                cs_score += score

        return min(cs_score, 1.0)
    except (json.JSONDecodeError, TypeError):
        return 0.0


async def recalculate_scores(dry_run: bool = False):
    """Recalculate CS scores for all std_author records."""
    # Use async engine
    engine = create_async_engine(
        "sqlite+aiosqlite:///./talent.db",
        echo=False
    )

    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    stats = {
        "total": 0,
        "updated": 0,
        "unchanged": 0,
        "no_raw_json": 0,
    }

    async with async_session() as session:
        # Get all std_authors with their raw_json
        result = await session.execute(
            select(StdAuthor, RawAuthor.raw_json)
            .join(RawAuthor, StdAuthor.openalex_author_id == RawAuthor.openalex_author_id)
        )
        rows = result.all()

        stats["total"] = len(rows)
        logger.info(f"Found {stats['total']} std_author records to process")

        if dry_run:
            logger.info("DRY RUN - showing first 10 changes:")

        for i, (std_author, raw_json) in enumerate(rows):
            if not raw_json:
                stats["no_raw_json"] += 1
                continue

            new_score = calculate_cs_score(raw_json)
            old_score = std_author.cs_concepts_score or 0.0

            if abs(new_score - old_score) < 0.001:
                stats["unchanged"] += 1
                continue

            stats["updated"] += 1

            if dry_run:
                if i < 10:
                    logger.info(
                        f"  {std_author.name_normalized}: "
                        f"{old_score:.3f} -> {new_score:.3f}"
                    )
            else:
                std_author.cs_concepts_score = new_score

        if not dry_run:
            await session.commit()
            logger.info(f"Committed {stats['updated']} updates")
        else:
            logger.info(f"Would update {stats['updated']} records")

    # Print summary
    logger.info("=" * 50)
    logger.info("Summary:")
    logger.info(f"  Total records: {stats['total']}")
    logger.info(f"  Would update:  {stats['updated']}")
    logger.info(f"  Unchanged:     {stats['unchanged']}")
    logger.info(f"  No raw_json:   {stats['no_raw_json']}")

    # Show score distribution after update
    if not dry_run:
        logger.info("=" * 50)
        logger.info("New score distribution:")
        async with async_session() as session:
            result = await session.execute(
                select(StdAuthor.cs_concepts_score)
            )
            scores = [r[0] or 0.0 for r in result.all()]

            ranges = {
                "< 0.3": 0,
                "0.3-0.5": 0,
                "0.5-0.7": 0,
                "0.7-1.0": 0,
                "1.0": 0,
            }

            for score in scores:
                if score < 0.3:
                    ranges["< 0.3"] += 1
                elif score < 0.5:
                    ranges["0.3-0.5"] += 1
                elif score < 0.7:
                    ranges["0.5-0.7"] += 1
                elif score < 1.0:
                    ranges["0.7-1.0"] += 1
                else:
                    ranges["1.0"] += 1

            for range_name, count in ranges.items():
                logger.info(f"  {range_name}: {count}")

    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Recalculate CS scores")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without applying")
    args = parser.parse_args()

    asyncio.run(recalculate_scores(dry_run=args.dry_run))
