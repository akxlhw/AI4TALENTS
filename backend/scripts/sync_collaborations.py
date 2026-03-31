"""
Standalone script for syncing collaboration data.

Usage:
    # Sync all talents
    python -m scripts.sync_collaborations

    # Sync specific talent
    python -m scripts.sync_collaborations --talent-id 123

    # With custom batch size
    python -m scripts.sync_collaborations --batch-size 50 --works-per-author 100
"""
import asyncio
import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import async_session_maker
from app.services.collaboration_service import CollaborationService
from app.services.talent_service import TalentService


async def main():
    parser = argparse.ArgumentParser(description="Sync collaboration data")
    parser.add_argument("--talent-id", type=int, help="Specific talent ID to sync")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size for processing")
    parser.add_argument("--works-per-author", type=int, default=50, help="Max works to fetch per author")
    args = parser.parse_args()

    print("=" * 60)
    print("Collaboration Data Sync Script")
    print("=" * 60)

    async with async_session_maker() as session:
        service = CollaborationService(session)
        talent_service = TalentService(session)

        try:
            if args.talent_id:
                # Sync single talent
                print(f"\nSyncing collaborations for talent {args.talent_id}...")
                talent = await talent_service.get_talent_by_id(args.talent_id)
                if not talent:
                    print(f"Error: Talent {args.talent_id} not found")
                    return

                count = await service.sync_collaborations_for_talent(
                    talent,
                    limit=args.works_per_author
                )
                print(f"Created/updated {count} collaborations")
            else:
                # Sync all talents
                print("\nSyncing collaborations for all talents...")
                print(f"Batch size: {args.batch_size}")
                print(f"Works per author: {args.works_per_author}")
                print()

                def progress_callback(processed, total, collaborations):
                    print(f"\rProgress: {processed}/{total} talents, {collaborations} collaborations", end="", flush=True)

                result = await service.sync_all_collaborations(
                    batch_size=args.batch_size,
                    works_per_author=args.works_per_author,
                    progress_callback=progress_callback
                )

                print(f"\n\nSync completed!")
                print(f"Total talents: {result['total_talents']}")
                print(f"Processed: {result['processed']}")
                print(f"Collaborations created: {result['collaborations_created']}")

        except Exception as e:
            print(f"\nError: {e}")
            raise
        finally:
            await service.close()

    print("\n" + "=" * 60)
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
