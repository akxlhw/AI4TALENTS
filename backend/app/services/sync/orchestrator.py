"""
Serving layer orchestrator for coordinating sync operations.
"""
import logging
from typing import Optional, Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.standardized import StdAuthor, StdSchool
from app.models.raw_data import AuthorTechBelong
from app.services.sync.author_sync import AuthorSyncService
from app.services.sync.school_sync import SchoolSyncService
from app.services.sync.tech_tag_sync import TechTagSyncService

logger = logging.getLogger(__name__)

# Batch size for IN queries (SQLite has variable limit)
SQLITE_BATCH_SIZE = 500


class ServingLayerOrchestrator:
    """Orchestrates synchronization from standardized layer to serving layer"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.author_sync = AuthorSyncService(session)
        self.school_sync = SchoolSyncService(session)
        self.tech_tag_sync = TechTagSyncService(session)

    async def _batch_get_std_authors(self, author_ids: List[str]) -> List[StdAuthor]:
        """Get StdAuthors by IDs in batches to avoid SQLite variable limit."""
        if not author_ids:
            return []

        results = []
        for i in range(0, len(author_ids), SQLITE_BATCH_SIZE):
            batch = author_ids[i:i + SQLITE_BATCH_SIZE]
            result = await self.session.execute(
                select(StdAuthor)
                .options(selectinload(StdAuthor.school))
                .where(StdAuthor.openalex_author_id.in_(batch))
            )
            results.extend(result.scalars().all())

        return results

    async def sync_all_for_task(
        self,
        task_id: int,
        tech_element_id: int,
        default_tech_direction_id: Optional[int] = None
    ) -> dict:
        """
        Sync all standardized data for a task to serving layer

        Args:
            task_id: Collection task ID
            tech_element_id: Tech element ID
            default_tech_direction_id: Default tech direction ID

        Returns:
            dict: Sync statistics
        """
        stats = {
            "authors_synced": 0,
            "authors_created": 0,
            "authors_updated": 0,
            "authors_filtered": 0,  # Filtered due to low CS score
            "schools_synced": 0,
            "schools_created": 0,
            "tags_created": 0,
            "new_talents_for_works": [],  # 收集新创建的学者（用于获取代表作品）
            "errors": []
        }

        # 1. First sync schools (so authors can reference them)
        await self._sync_schools(task_id, tech_element_id, stats)

        # 2. Then sync authors
        await self._sync_authors(task_id, tech_element_id, default_tech_direction_id, stats)

        await self.session.flush()

        logger.info(
            f"Sync completed: {stats['authors_synced']} authors "
            f"({stats['authors_created']} created, {stats['authors_updated']} updated), "
            f"{stats['authors_filtered']} filtered (low CS score), "
            f"{stats['schools_synced']} schools ({stats['schools_created']} created), "
            f"{stats['tags_created']} tech tags created"
        )

        return stats

    async def _sync_authors(
        self,
        task_id: int,
        tech_element_id: int,
        default_tech_direction_id: Optional[int],
        stats: dict
    ):
        """Sync all authors for a task"""
        # Get AuthorTechBelong records for this task and tech element
        belong_result = await self.session.execute(
            select(AuthorTechBelong).where(
                AuthorTechBelong.source_task_id == task_id,
                AuthorTechBelong.tech_element_id == tech_element_id
            )
        )
        belongs = belong_result.scalars().all()

        if not belongs:
            logger.info(f"No AuthorTechBelong found for task_id={task_id}, tech_element_id={tech_element_id}")
            return

        # Get unique openalex_author_ids
        author_ids = list(set(b.openalex_author_id for b in belongs))
        logger.info(f"Found {len(belongs)} tech belong records, {len(author_ids)} unique authors")

        # Get StdAuthors by openalex_author_id (batched to avoid SQLite limit)
        std_authors = await self._batch_get_std_authors(author_ids)
        logger.info(f"Found {len(std_authors)} standardized authors")

        for std_author in std_authors:
            try:
                # Sync author to Talent
                talent, is_new = await self.author_sync.sync_author_to_talent(std_author)

                # Check if author was filtered (talent is None)
                if talent is None:
                    stats["authors_filtered"] += 1
                    continue

                stats["authors_synced"] += 1
                if is_new:
                    stats["authors_created"] += 1
                    # 收集新创建的教授（用于后续获取代表作品）
                    if talent.role_type == 'professor' and talent.works_count > 5:
                        stats["new_talents_for_works"].append({
                            "talent_id": talent.talent_id,
                            "openalex_author_id": std_author.openalex_author_id,
                            "works_count": talent.works_count
                        })
                else:
                    stats["authors_updated"] += 1

                # Get author's tech belong relationships for this tech element
                author_belongs = [b for b in belongs if b.openalex_author_id == std_author.openalex_author_id]

                # Sync tech tags
                if author_belongs:
                    tag_count = await self.tech_tag_sync.sync_talent_tech_tags(
                        talent, author_belongs, default_tech_direction_id
                    )
                    stats["tags_created"] += tag_count

            except Exception as e:
                error_msg = f"Failed to sync author {std_author.openalex_author_id}: {str(e)}"
                logger.error(error_msg)
                stats["errors"].append(error_msg)

    async def _sync_schools(self, task_id: int, tech_element_id: int, stats: dict):
        """Sync all schools for a task - called BEFORE author sync"""
        # Get AuthorTechBelong records for this task and tech element
        belong_result = await self.session.execute(
            select(AuthorTechBelong).where(
                AuthorTechBelong.source_task_id == task_id,
                AuthorTechBelong.tech_element_id == tech_element_id
            )
        )
        belongs = belong_result.scalars().all()

        if not belongs:
            return

        # Get unique openalex_author_ids
        author_ids = list(set(b.openalex_author_id for b in belongs))

        # Get StdAuthors with their schools (batched to avoid SQLite limit)
        std_authors = await self._batch_get_std_authors(author_ids)

        # Collect all unique schools
        schools_to_sync = {}
        for std_author in std_authors:
            if std_author.school and std_author.school.openalex_institution_id:
                inst_id = std_author.school.openalex_institution_id
                if inst_id not in schools_to_sync:
                    schools_to_sync[inst_id] = std_author.school

        logger.info(f"Syncing {len(schools_to_sync)} schools")

        # Sync all schools
        for std_school in schools_to_sync.values():
            try:
                school, is_new = await self.school_sync.sync_school_to_school(std_school)
                stats["schools_synced"] += 1
                if is_new:
                    stats["schools_created"] += 1
            except Exception as e:
                error_msg = f"Failed to sync school {std_school.openalex_institution_id}: {str(e)}"
                logger.error(error_msg)
                stats["errors"].append(error_msg)

        await self.session.flush()
