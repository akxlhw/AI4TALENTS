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
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from sqlalchemy import case, func, select, text

from app.core.database import AsyncSessionLocal
from app.domains.academic.models.school import School
from app.domains.academic.models.talent import Talent
from app.domains.academic.models.tech_domain import TalentTechTag

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


async def update_tech_domain_counts(session):
    """Update tech domain talent counts from TechTag."""
    logger.info("Updating tech domain talent counts...")

    # Count talents per tech domain
    result = await session.execute(
        select(
            TalentTechTag.tech_domain_id,
            func.count(TalentTechTag.talent_id.distinct()).label('talent_count')
        ).group_by(TalentTechTag.tech_domain_id)
    )

    updated_domains = 0
    for row in result:
        tech_domain_id, talent_count = row
        # Update the tech domain (if it has a talent_count field)
        # Note: core_tech_domain doesn't have talent_count, but we can log for reference
        updated_domains += 1
        logger.info(f"  Tech domain {tech_domain_id}: {talent_count} talents")

    logger.info(f"  {updated_domains} tech domains have talents")
    return updated_domains


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


async def refresh_research_topic_stats(session):
    """Refresh research topic statistics from openalex_topics.

    Used for:
    1. Initializing historical data (already collected but not yet counted)
    2. Manual full refresh to fix data inconsistency
    3. Scheduled task fallback
    """
    from app.builders.stat_builder import StatBuilder

    logger.info("Refreshing research topic statistics...")

    try:
        builder = StatBuilder(session, batch_id=0, version="manual-refresh")
        result = await builder._build_research_topic_stats()
        await session.flush()
        logger.info(f"  Research topic stats refreshed: {result['topics_processed']} topics")
        return result["topics_processed"]
    except Exception as e:
        logger.error(f"  Research topic stats refresh error: {e}")
        return 0


async def rebuild_search_index(session):
    """Rebuild search index for all talents."""
    from sqlalchemy import text

    from app.builders.search_builder import SearchBuilder

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

        # 2. Update tech domain counts
        await update_tech_domain_counts(session)

        # 3. Build homepage statistics
        await build_homepage_statistics(session)
        await session.commit()

        # 4. Rebuild search index
        await rebuild_search_index(session)

        # 5. Refresh research topic statistics (handles historical data initialization)
        await refresh_research_topic_stats(session)
        await session.commit()

        # 6. Print summary
        logger.info("\n=== Summary ===")
        result = await session.execute(text("SELECT COUNT(*) FROM core_talent"))
        logger.info(f"Total talents: {result.scalar()}")

        result = await session.execute(text("SELECT COUNT(*) FROM core_school WHERE professor_count > 0"))
        logger.info(f"Schools with professors: {result.scalar()}")

        result = await session.execute(text("SELECT COUNT(*) FROM stat_overview_snapshot"))
        logger.info(f"Stat snapshots: {result.scalar()}")

        result = await session.execute(text("SELECT COUNT(*) FROM search_talent_document"))
        logger.info(f"Search documents: {result.scalar()}")

        result = await session.execute(text("SELECT COUNT(*) FROM stats_research_topic"))
        logger.info(f"Research topic stats: {result.scalar()}")

        logger.info("\nStatistics refresh complete!")


if __name__ == "__main__":
    asyncio.run(refresh_all_stats())
