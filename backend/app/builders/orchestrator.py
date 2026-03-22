"""
Object build orchestrator.
Coordinates the complete build process from raw data to domain objects.
"""
from datetime import datetime
from typing import Dict, Any, Optional
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.builders.base import BuildResult
from app.builders.school_builder import SchoolBuilder
from app.builders.talent_builder import TalentBuilder
from app.builders.stat_builder import StatBuilder
from app.builders.search_builder import SearchBuilder


logger = logging.getLogger(__name__)


class BuildOrchestrator:
    """
    Orchestrates the complete build process.

    Build order:
    1. Build schools from institutions
    2. Build talents from authors
    3. Build statistics
    4. Build search documents
    """

    def __init__(self, session: AsyncSession, batch_id: int):
        self.session = session
        self.batch_id = batch_id
        self.version = f"v{datetime.now().strftime('%Y%m%d%H%M%S')}"

    async def run_full_build(self) -> Dict[str, Any]:
        """
        Run the complete build process.

        Returns:
            Summary of all build results
        """
        start_time = datetime.now()
        results = {}

        logger.info(f"Starting full build for batch {self.batch_id}")
        logger.info(f"Build version: {self.version}")

        # Step 1: Build schools
        logger.info("\n" + "="*50)
        logger.info("Step 1: Building schools")
        logger.info("="*50)

        school_builder = SchoolBuilder(self.session, self.batch_id)
        results["schools"] = await school_builder.build()

        logger.info(
            f"Schools: {results['schools'].records_created} created, "
            f"{results['schools'].records_updated} updated, "
            f"{results['schools'].records_failed} failed"
        )

        # Step 2: Build talents
        logger.info("\n" + "="*50)
        logger.info("Step 2: Building talents")
        logger.info("="*50)

        talent_builder = TalentBuilder(self.session, self.batch_id)
        results["talents"] = await talent_builder.build()

        logger.info(
            f"Talents: {results['talents'].records_created} created, "
            f"{results['talents'].records_updated} updated, "
            f"{results['talents'].records_failed} failed"
        )

        # Step 3: Build statistics
        logger.info("\n" + "="*50)
        logger.info("Step 3: Building statistics")
        logger.info("="*50)

        stat_builder = StatBuilder(self.session, self.batch_id, self.version)
        results["statistics"] = await stat_builder.build()

        logger.info(
            f"Statistics: {results['statistics'].records_created} snapshots created"
        )

        # Step 4: Build search documents
        logger.info("\n" + "="*50)
        logger.info("Step 4: Building search documents")
        logger.info("="*50)

        search_builder = SearchBuilder(self.session, self.batch_id)
        results["search"] = await search_builder.build()

        logger.info(
            f"Search: {results['search'].records_created} documents created, "
            f"{results['search'].records_failed} failed"
        )

        # Summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        summary = {
            "batch_id": self.batch_id,
            "version": self.version,
            "started_at": start_time.isoformat(),
            "completed_at": end_time.isoformat(),
            "duration_seconds": duration,
            "schools": {
                "created": results["schools"].records_created,
                "updated": results["schools"].records_updated,
                "failed": results["schools"].records_failed,
            },
            "talents": {
                "created": results["talents"].records_created,
                "updated": results["talents"].records_updated,
                "failed": results["talents"].records_failed,
            },
            "statistics": {
                "created": results["statistics"].records_created,
            },
            "search": {
                "created": results["search"].records_created,
                "failed": results["search"].records_failed,
            },
            "success": all(
                r.success for r in results.values() if isinstance(r, BuildResult)
            ),
        }

        logger.info("\n" + "="*50)
        logger.info("Build Complete")
        logger.info("="*50)
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info(f"Success: {summary['success']}")

        return summary

    async def build_schools_only(self) -> BuildResult:
        """Build only schools."""
        builder = SchoolBuilder(self.session, self.batch_id)
        return await builder.build()

    async def build_talents_only(self) -> BuildResult:
        """Build only talents."""
        builder = TalentBuilder(self.session, self.batch_id)
        return await builder.build()

    async def build_stats_only(self) -> BuildResult:
        """Build only statistics."""
        builder = StatBuilder(self.session, self.batch_id, self.version)
        return await builder.build()

    async def build_search_only(self) -> BuildResult:
        """Build only search documents."""
        builder = SearchBuilder(self.session, self.batch_id)
        return await builder.build()
