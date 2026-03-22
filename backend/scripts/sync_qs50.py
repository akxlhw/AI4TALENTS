"""
Sync QS Top 50 universities data from OpenAlex.

This script fetches data for QS World University Rankings Top 50 institutions.

Usage:
    python scripts/sync_qs50.py [--max-authors N]
"""
import asyncio
import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.services.sync_service import SyncService
from app.services.openalex_client import OpenAlexClient
from app.repositories.sync_repository import SyncBatchRepository

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# QS Top 50 Universities 2024 (simplified names for matching)
# Format: (display_name, country_code)
QS_TOP_50 = [
    # Top 10
    ("Massachusetts Institute of Technology", "US"),
    ("University of Cambridge", "GB"),
    ("University of Oxford", "GB"),
    ("Harvard University", "US"),
    ("Stanford University", "US"),
    ("Imperial College London", "GB"),
    ("ETH Zurich", "CH"),
    ("National University of Singapore", "SG"),
    ("UCL", "GB"),
    ("California Institute of Technology", "US"),
    # 11-20
    ("University of Pennsylvania", "US"),
    ("University of California Berkeley", "US"),
    ("University of Melbourne", "AU"),
    ("Peking University", "CN"),
    ("Tsinghua University", "CN"),
    ("University of Sydney", "AU"),
    ("University of New South Wales", "AU"),
    ("University of Toronto", "CA"),
    ("University of Edinburgh", "GB"),
    ("Princeton University", "US"),
    # 21-30
    ("Yale University", "US"),
    ("Nanyang Technological University", "SG"),
    ("Columbia University", "US"),
    ("University of Hong Kong", "HK"),
    ("University of Tokyo", "JP"),
    ("University of Michigan", "US"),
    ("Johns Hopkins University", "US"),
    ("University of California Los Angeles", "US"),
    ("McGill University", "CA"),
    ("Australian National University", "AU"),
    # 31-40
    ("University of Manchester", "GB"),
    ("Northwestern University", "US"),
    ("Fudan University", "CN"),
    ("University of California San Diego", "US"),
    ("King's College London", "GB"),
    ("Chinese University of Hong Kong", "HK"),
    ("KAIST", "KR"),
    ("London School of Economics", "GB"),
    ("University of Waterloo", "CA"),
    ("University of British Columbia", "CA"),
    # 41-50
    ("Duke University", "US"),
    ("City University of Hong Kong", "HK"),
    ("University of Queensland", "AU"),
    ("Shanghai Jiao Tong University", "CN"),
    ("University of Chicago", "US"),
    ("Cornell University", "US"),
    ("Seoul National University", "KR"),
    ("University of New South Wales", "AU"),
    ("Technical University of Munich", "DE"),
    ("University of Glasgow", "GB"),
]


async def search_institution(
    client: OpenAlexClient,
    name: str,
    country_code: str,
) -> Optional[Dict]:
    """
    Search for an institution in OpenAlex by name and country.

    Args:
        client: OpenAlex client
        name: Institution name
        country_code: Country code

    Returns:
        Institution data or None
    """
    try:
        # Try to search by display_name
        results = await client.get_institutions(
            country_code=country_code,
            institution_type="education",
            per_page=10,
        )

        institutions = results.get("results", [])

        # Try exact match first
        for inst in institutions:
            display_name = inst.get("display_name", "").lower()
            if name.lower() in display_name or display_name in name.lower():
                return inst

        # Try partial match
        name_parts = name.lower().split()
        for inst in institutions:
            display_name = inst.get("display_name", "").lower()
            matches = sum(1 for part in name_parts if part in display_name)
            if matches >= len(name_parts) * 0.5:  # At least 50% match
                return inst

        return None

    except Exception as e:
        logger.warning(f"Failed to search for {name}: {e}")
        return None


async def sync_qs50(
    max_authors_per_institution: Optional[int] = None,
    institution_limit: Optional[int] = None,
) -> Dict:
    """
    Sync QS Top 50 universities and their authors.

    Args:
        max_authors_per_institution: Max authors to sync per institution
        institution_limit: Limit number of institutions (for testing)

    Returns:
        Sync summary
    """
    start_time = datetime.now()
    print("\n" + "=" * 60)
    print("QS Top 50 Universities - OpenAlex Data Sync")
    print("=" * 60)
    print(f"Start time: {start_time}")
    print(f"Max authors per institution: {max_authors_per_institution or 'Unlimited'}")

    client = OpenAlexClient(
        email=settings.OPENALEX_EMAIL,
        rate_limit=settings.OPENALEX_RATE_LIMIT,
    )

    # Step 1: Find OpenAlex IDs for QS Top 50
    print("\n" + "-" * 60)
    print("Step 1: Finding OpenAlex IDs for QS Top 50 universities")
    print("-" * 60)

    found_institutions = []
    institutions_to_process = QS_TOP_50[:institution_limit] if institution_limit else QS_TOP_50

    for name, country in institutions_to_process:
        print(f"  Searching: {name} ({country})...", end=" ")
        inst = await search_institution(client, name, country)

        if inst:
            openalex_id = inst.get("id", "").split("/")[-1]
            display_name = inst.get("display_name", "Unknown")
            works_count = inst.get("works_count", 0)
            print(f"Found! ID: {openalex_id}, Works: {works_count:,}")
            found_institutions.append({
                "id": openalex_id,
                "name": display_name,
                "country": country,
                "works_count": works_count,
            })
        else:
            print("Not found")

    print(f"\nFound {len(found_institutions)} / {len(institutions_to_process)} institutions")

    if not found_institutions:
        print("No institutions found. Aborting.")
        return {"success": False, "error": "No institutions found"}

    # Step 2: Sync institutions to database
    print("\n" + "-" * 60)
    print("Step 2: Syncing institution data")
    print("-" * 60)

    async with AsyncSessionLocal() as session:
        service = SyncService(session)

        # Sync institutions
        inst_ids = [inst["id"] for inst in found_institutions]
        inst_progress = await service.sync_institutions_by_ids(
            institution_ids=inst_ids,
        )

        print(f"  Institutions synced: {inst_progress.processed_records}")

        # Step 3: Sync authors for each institution
        print("\n" + "-" * 60)
        print("Step 3: Syncing author data")
        print("-" * 60)

        total_authors = 0
        for i, inst in enumerate(found_institutions, 1):
            print(f"  [{i}/{len(found_institutions)}] {inst['name']}...", end=" ")

            author_progress = await service.sync_authors_for_institutions(
                institution_ids=[inst["id"]],
                max_authors_per_institution=max_authors_per_institution,
            )

            authors_synced = author_progress.processed_records
            total_authors += authors_synced
            print(f"{authors_synced} authors")

        await session.commit()

    # Summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print("\n" + "=" * 60)
    print("Sync Complete")
    print("=" * 60)
    print(f"Duration: {duration:.1f} seconds")
    print(f"Institutions found: {len(found_institutions)}")
    print(f"Institutions synced: {inst_progress.processed_records}")
    print(f"Total authors: {total_authors}")

    return {
        "success": True,
        "duration_seconds": duration,
        "institutions_found": len(found_institutions),
        "institutions_synced": inst_progress.processed_records,
        "total_authors": total_authors,
    }


async def build_objects_after_sync():
    """Build domain objects after sync."""
    print("\n" + "-" * 60)
    print("Step 4: Building domain objects")
    print("-" * 60)

    from app.builders.orchestrator import BuildOrchestrator
    from app.repositories.sync_repository import SyncBatchRepository

    async with AsyncSessionLocal() as session:
        # Get latest batch
        repo = SyncBatchRepository(session)
        batches = await repo.get_recent_batches(limit=1)
        if not batches:
            print("No batch found")
            return

        batch_id = batches[0].batch_id
        print(f"Building objects for batch {batch_id}...")

        orchestrator = BuildOrchestrator(session, batch_id)
        result = await orchestrator.run_full_build()

        print(f"\nBuild Results:")
        print(f"  Schools: {result['schools']['created']} created")
        print(f"  Talents: {result['talents']['created']} created")
        print(f"  Statistics: {result['statistics']['created']} snapshots")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Sync QS Top 50 universities data from OpenAlex",
    )

    parser.add_argument(
        "--max-authors",
        type=int,
        default=100,
        help="Max authors per institution (default: 100)",
    )

    parser.add_argument(
        "--institution-limit",
        type=int,
        help="Limit number of institutions (for testing)",
    )

    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip building domain objects",
    )

    args = parser.parse_args()

    # Run sync
    result = asyncio.run(sync_qs50(
        max_authors_per_institution=args.max_authors,
        institution_limit=args.institution_limit,
    ))

    # Build objects
    if result.get("success") and not args.skip_build:
        asyncio.run(build_objects_after_sync())

    print("\nDone!")


if __name__ == "__main__":
    main()
