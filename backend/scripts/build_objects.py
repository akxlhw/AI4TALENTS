"""
Domain objects building script.
Transforms raw data from OpenAlex into domain objects.

Usage:
    python scripts/build_objects.py [options]

Options:
    --batch-id N       Specific batch ID to process
    --full             Run full build (default)
    --schools-only     Build only schools
    --stats-only       Build only statistics
    --search-only      Build only search documents

NOTE: Talent building is now handled by ServingLayerSync during data collection.
"""
import asyncio
import argparse
import json
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import AsyncSessionLocal
from app.repositories.sync_repository import SyncBatchRepository
from app.builders.orchestrator import BuildOrchestrator
from app.models.enums import SyncJobStatus


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def get_latest_successful_batch_id() -> Optional[int]:
    """Get the latest successful sync batch ID."""
    async with AsyncSessionLocal() as session:
        repo = SyncBatchRepository(session)
        batches = await repo.get_recent_batches(limit=10)

        for batch in batches:
            if batch.status in [SyncJobStatus.SUCCESS.value, SyncJobStatus.PARTIAL.value]:
                return batch.batch_id

        return None


async def run_build(
    batch_id: Optional[int] = None,
    build_type: str = "full",
) -> dict:
    """
    Run the object build process.

    Args:
        batch_id: Specific batch ID (None for latest successful)
        build_type: 'full', 'schools', 'stats', or 'search'

    Returns:
        Build summary dictionary
    """
    # Get batch ID if not specified
    if not batch_id:
        batch_id = await get_latest_successful_batch_id()
        if not batch_id:
            return {
                "success": False,
                "error": "No successful sync batch found",
            }

    print(f"\nBuilding objects for batch: {batch_id}")
    print(f"Build type: {build_type}")
    print("="*60)

    async with AsyncSessionLocal() as session:
        orchestrator = BuildOrchestrator(session, batch_id)

        if build_type == "full":
            result = await orchestrator.run_full_build()
        elif build_type == "schools":
            build_result = await orchestrator.build_schools_only()
            result = {
                "batch_id": batch_id,
                "success": build_result.success,
                "schools": {
                    "created": build_result.records_created,
                    "updated": build_result.records_updated,
                    "failed": build_result.records_failed,
                },
            }
        elif build_type == "stats":
            build_result = await orchestrator.build_stats_only()
            result = {
                "batch_id": batch_id,
                "success": build_result.success,
                "statistics": {"created": build_result.records_created},
            }
        elif build_type == "search":
            build_result = await orchestrator.build_search_only()
            result = {
                "batch_id": batch_id,
                "success": build_result.success,
                "search": {
                    "created": build_result.records_created,
                    "failed": build_result.records_failed,
                },
            }
        else:
            result = {
                "success": False,
                "error": f"Unknown build type: {build_type}",
            }

        return result


def print_summary(result: dict):
    """Print build summary."""
    print("\n" + "="*60)
    print("Build Summary")
    print("="*60)

    if result.get("error"):
        print(f"Error: {result['error']}")
        return

    print(f"Batch ID: {result.get('batch_id')}")
    print(f"Version: {result.get('version', 'N/A')}")

    if "schools" in result:
        schools = result["schools"]
        print(f"\nSchools:")
        print(f"  Created: {schools.get('created', 0)}")
        print(f"  Updated: {schools.get('updated', 0)}")
        print(f"  Failed: {schools.get('failed', 0)}")

    if "statistics" in result:
        stats = result["statistics"]
        print(f"\nStatistics:")
        print(f"  Snapshots created: {stats.get('created', 0)}")

    if "search" in result:
        search = result["search"]
        print(f"\nSearch Documents:")
        print(f"  Created: {search.get('created', 0)}")
        print(f"  Failed: {search.get('failed', 0)}")

    if "duration_seconds" in result:
        print(f"\nDuration: {result['duration_seconds']:.2f} seconds")

    print(f"\nOverall Success: {result.get('success', False)}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Build domain objects from raw data",
    )

    parser.add_argument(
        "--batch-id",
        type=int,
        help="Specific batch ID to process",
    )

    parser.add_argument(
        "--full",
        action="store_true",
        help="Run full build (default)",
    )

    parser.add_argument(
        "--schools-only",
        action="store_true",
        help="Build only schools",
    )

    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Build only statistics",
    )

    parser.add_argument(
        "--search-only",
        action="store_true",
        help="Build only search documents",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )

    args = parser.parse_args()

    # Determine build type
    build_type = "full"
    if args.schools_only:
        build_type = "schools"
    elif args.stats_only:
        build_type = "stats"
    elif args.search_only:
        build_type = "search"

    # Run build
    result = asyncio.run(run_build(
        batch_id=args.batch_id,
        build_type=build_type,
    ))

    # Output result
    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print_summary(result)

    # Exit with appropriate code
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
