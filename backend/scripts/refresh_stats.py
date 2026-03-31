"""
Refresh all statistics after data updates.

This script updates:
1. School professor_count and student_count
2. Homepage statistics snapshots
3. Tech element talent counts (via TechTag)

Usage:
    python scripts/refresh_stats.py
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, func, case, update, text
from app.core.database import AsyncSessionLocal
from app.models.school import School
from app.models.talent import Talent
from app.models.tech_element import TechElement, TalentTechTag

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def update_school_statistics(session):
    """Update school professor_count and student_count."""
    logger.info("Updating school statistics...")

    # Reset all school counts
    await session.execute(
        School.__table__.update().values(professor_count=0, student_count=0)
    )

    # Calculate and update counts
    result = await session.execute(
        select(
            Talent.school_id,
            func.count(case((Talent.role_type == 'professor', 1))).label('professor_count'),
            func.count(case((Talent.role_type.in_(['student', 'graduate']), 1))).label('student_count')
        ).where(
            Talent.school_id.isnot(None),
            Talent.is_visible == True
        ).group_by(Talent.school_id)
    )

    updated_schools = 0
    for row in result:
        school_id, prof_count, stu_count = row
        if school_id:
            await session.execute(
                School.__table__.update()
                .where(School.school_id == school_id)
                .values(professor_count=prof_count, student_count=stu_count)
            )
            updated_schools += 1

    await session.flush()
    logger.info(f"  Updated {updated_schools} schools")
    return updated_schools


async def update_tech_element_counts(session):
    """Update tech element talent counts from TechTag."""
    logger.info("Updating tech element talent counts...")

    # Count talents per tech element
    result = await session.execute(
        select(
            TalentTechTag.tech_element_id,
            func.count(TalentTechTag.talent_id.distinct()).label('talent_count')
        ).group_by(TalentTechTag.tech_element_id)
    )

    updated_elements = 0
    for row in result:
        tech_element_id, talent_count = row
        # Update the tech element (if it has a talent_count field)
        # Note: core_tech_element doesn't have talent_count, but we can log for reference
        updated_elements += 1
        logger.info(f"  Tech element {tech_element_id}: {talent_count} talents")

    logger.info(f"  {updated_elements} tech elements have talents")
    return updated_elements


async def build_homepage_statistics(session):
    """Build statistics snapshots for homepage."""
    from app.builders.stat_builder import StatBuilder

    logger.info("Building homepage statistics...")

    try:
        builder = StatBuilder(session, batch_id=0, version="manual-refresh")
        result = await builder.build()

        if result.success:
            logger.info(f"  Homepage stats built: {result.records_created} records created")
        else:
            logger.warning(f"  Homepage stats build failed: {result.errors}")

        return result.success
    except Exception as e:
        logger.error(f"  Homepage stats build error: {e}")
        return False


async def rebuild_search_index(session):
    """Rebuild search index for all talents."""
    from app.builders.search_builder import SearchBuilder
    from sqlalchemy import text

    logger.info("Rebuilding search index...")

    # Clear existing search documents
    await session.execute(text("DELETE FROM search_talent_document"))
    await session.commit()
    logger.info("  Cleared existing search documents")

    try:
        builder = SearchBuilder(session, batch_id=0)
        result = await builder.build()

        if result.success:
            logger.info(f"  Search index rebuilt: {result.records_created} documents")
        else:
            logger.warning(f"  Search index build failed: {result.errors}")

        return result.success
    except Exception as e:
        logger.error(f"  Search index build error: {e}")
        return False


async def refresh_all_stats():
    """Refresh all statistics."""
    async with AsyncSessionLocal() as session:
        # 1. Update school statistics
        await update_school_statistics(session)
        await session.commit()

        # 2. Update tech element counts
        await update_tech_element_counts(session)

        # 3. Build homepage statistics
        await build_homepage_statistics(session)
        await session.commit()

        # 4. Rebuild search index
        await rebuild_search_index(session)

        # 5. Print summary
        logger.info("\n=== Summary ===")
        result = await session.execute(text("SELECT COUNT(*) FROM core_talent"))
        logger.info(f"Total talents: {result.scalar()}")

        result = await session.execute(text("SELECT COUNT(*) FROM core_school WHERE professor_count > 0"))
        logger.info(f"Schools with professors: {result.scalar()}")

        result = await session.execute(text("SELECT COUNT(*) FROM stat_overview_snapshot"))
        logger.info(f"Stat snapshots: {result.scalar()}")

        result = await session.execute(text("SELECT COUNT(*) FROM search_talent_document"))
        logger.info(f"Search documents: {result.scalar()}")

        logger.info("\nStatistics refresh complete!")


if __name__ == "__main__":
    asyncio.run(refresh_all_stats())
