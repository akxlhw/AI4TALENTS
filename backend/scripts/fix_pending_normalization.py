"""
Fix pending normalization for a specific task.
Processes pending RawAuthor and RawInstitution records for a given task_id.

Usage:
    python scripts/fix_pending_normalization.py --task-id 2 [--sync]

Options:
    --task-id   Task ID to process (required)
    --sync      Also run sync to serving layer (create Talent records)
"""
import asyncio
import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.domains.academic.services.normalizers import AuthorNormalizer, SchoolNormalizer
from app.domains.academic.services.sync import ServingLayerOrchestrator
from app.domains.academic.repositories.raw_data_repository import RawAuthorRepository, RawInstitutionRepository
from app.domains.academic.models.sync import CollectTask

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def fix_pending_normalization(task_id: int, run_sync: bool = False):
    """Process pending normalization for a specific task."""
    async with AsyncSessionLocal() as session:
        # Check pending counts
        raw_author_repo = RawAuthorRepository(session)
        raw_inst_repo = RawInstitutionRepository(session)

        pending_authors = await raw_author_repo.get_pending(task_id)
        pending_institutions = await raw_inst_repo.get_pending(task_id)

        logger.info(f"Task {task_id} pending status:")
        logger.info(f"  - Authors: {len(pending_authors)}")
        logger.info(f"  - Institutions: {len(pending_institutions)}")

        # Step 1: Normalize institutions
        if pending_institutions:
            logger.info("Step 1: Normalizing institutions...")
            school_normalizer = SchoolNormalizer(session)
            result = await school_normalizer.normalize_all_institutions(task_id=task_id)
            logger.info(f"  Institutions processed: {result.processed}, failed: {result.failed}")
            await session.commit()

        # Step 2: Normalize authors (depends on institutions for school linkage)
        if pending_authors:
            logger.info("Step 2: Normalizing authors...")
            author_normalizer = AuthorNormalizer(session)
            result = await author_normalizer.normalize_all_authors(task_id=task_id)
            logger.info(f"  Authors processed: {result.processed}, failed: {result.failed}")
            await session.commit()

        # Step 3: Sync to serving layer (optional)
        if run_sync:
            logger.info("Step 3: Syncing to serving layer...")

            # Get tech_domain_id from task
            task_result = await session.execute(
                select(CollectTask).where(CollectTask.task_id == task_id)
            )
            task = task_result.scalar_one_or_none()
            if not task:
                logger.error(f"Task {task_id} not found!")
                return

            sync = ServingLayerOrchestrator(session)
            stats = await sync.sync_all_for_task(
                task_id=task_id,
                tech_domain_id=task.tech_domain_id,
                default_tech_direction_id=await get_default_tech_direction(session, task.tech_domain_id)
            )
            logger.info(f"  Sync stats: {stats}")
            await session.commit()

        # Verify results
        remaining_authors = await raw_author_repo.get_pending(task_id)
        remaining_institutions = await raw_inst_repo.get_pending(task_id)

        logger.info(f"Remaining pending:")
        logger.info(f"  - Authors: {len(remaining_authors)}")
        logger.info(f"  - Institutions: {len(remaining_institutions)}")

        logger.info("Normalization fix complete!")


async def get_default_tech_direction(session, tech_domain_id: int) -> int:
    """Get or create default tech direction for a tech domain."""
    from app.domains.academic.models.tech_domain import TechDirection
    from sqlalchemy import func

    # Try to get the first available direction
    result = await session.execute(
        select(TechDirection.tech_direction_id).limit(1)
    )
    direction = result.scalar_one_or_none()
    if direction:
        return direction

    # Create a default direction if none exists
    direction = TechDirection(
        direction_name="Default Direction",
        direction_code="DEFAULT"
    )
    session.add(direction)
    await session.flush()
    return direction.tech_direction_id


def main():
    parser = argparse.ArgumentParser(description="Fix pending normalization for a task")
    parser.add_argument("--task-id", type=int, required=True, help="Task ID to process")
    parser.add_argument("--sync", action="store_true", help="Also sync to serving layer")
    args = parser.parse_args()

    asyncio.run(fix_pending_normalization(args.task_id, args.sync))


if __name__ == "__main__":
    main()
