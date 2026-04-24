"""
Serving layer orchestrator for coordinating sync operations.
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.raw_data import AuthorTechBelong
from app.models.standardized import StdAuthor, StdSchool
from app.models.talent import Talent
from app.services.common.batch_utils import batch_in_query_flat, batch_in_query_map
from app.services.sync.author_sync import AuthorSyncService
from app.services.sync.school_sync import SchoolSyncService
from app.services.sync.tech_tag_sync import TechTagSyncService

logger = logging.getLogger(__name__)

# Log module load to verify code version
logger.info("[SYNC_ORCHESTRATOR] Module loaded with CS score filtering enabled")


class ServingLayerOrchestrator:
    """Orchestrates synchronization from standardized layer to serving layer"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.author_sync = AuthorSyncService(session)
        self.school_sync = SchoolSyncService(session)
        self.tech_tag_sync = TechTagSyncService(session)

    async def _batch_get_std_authors(self, author_ids: list[str]) -> list[StdAuthor]:
        """Get StdAuthors by IDs in batches."""
        return await batch_in_query_flat(
            self.session,
            lambda batch: select(StdAuthor)
                .options(selectinload(StdAuthor.school))
                .where(StdAuthor.openalex_author_id.in_(batch)),
            author_ids
        )

    async def sync_all_for_task(
        self,
        task_id: int,
        tech_domain_id: int,
        default_tech_direction_id: int | None = None
    ) -> dict:
        """
        Sync all standardized data for a task to serving layer

        Args:
            task_id: Collection task ID
            tech_domain_id: Tech domain ID
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

        # Use bulk sync for PostgreSQL
        return await self._bulk_sync_all(task_id, tech_domain_id, default_tech_direction_id, stats)

    async def _bulk_sync_all(
        self,
        task_id: int,
        tech_domain_id: int,
        default_tech_direction_id: int | None,
        stats: dict
    ) -> dict:
        """
        PostgreSQL-optimized bulk sync using ON CONFLICT.

        This method uses bulk operations for maximum performance.
        """
        from app.services.common.cs_concepts import CS_SCORE_THRESHOLD

        # Get AuthorTechBelong records for this task and tech domain
        belong_result = await self.session.execute(
            select(AuthorTechBelong).where(
                AuthorTechBelong.source_task_id == task_id,
                AuthorTechBelong.tech_domain_id == tech_domain_id
            )
        )
        belongs = belong_result.scalars().all()

        if not belongs:
            logger.warning(f"[BULK_SYNC] No AuthorTechBelong found for task_id={task_id}")
            return stats

        # Get unique openalex_author_ids
        author_ids = list({b.openalex_author_id for b in belongs})
        logger.info(f"[BULK_SYNC] Found {len(belongs)} tech belong records, {len(author_ids)} unique authors")

        # Get StdAuthors with their schools (batched)
        std_authors = await self._batch_get_std_authors(author_ids)
        logger.info(f"[BULK_SYNC] Found {len(std_authors)} standardized authors")

        # Log CS score distribution
        cs_scores = [sa.cs_concepts_score for sa in std_authors if sa.cs_concepts_score is not None]
        if cs_scores:
            above_threshold = sum(1 for s in cs_scores if s >= CS_SCORE_THRESHOLD)
            logger.info(f"[BULK_SYNC] CS score distribution: {len(cs_scores)} authors, {above_threshold} >= {CS_SCORE_THRESHOLD}")

        # 1. Bulk sync schools first
        schools_to_sync = await self._collect_schools_to_sync(std_authors)

        if schools_to_sync:
            school_result = await self.school_sync.bulk_sync_schools(list(schools_to_sync.values()))
            stats["schools_synced"] = school_result["synced"]
            stats["schools_created"] = school_result["created"]
            school_id_map = school_result["school_id_map"]
        else:
            school_id_map = {}

        # 2. Bulk sync authors
        author_result = await self.author_sync.bulk_sync_authors(std_authors, school_id_map)
        stats["authors_synced"] = author_result["synced"]
        stats["authors_created"] = author_result["created"]
        stats["authors_updated"] = author_result["updated"]
        stats["authors_filtered"] = author_result["filtered"]
        stats["new_talents_for_works"] = author_result.get("new_talents", [])

        # Track affected school IDs for incremental statistics update
        affected_school_ids = set(school_id_map.values())
        stats["affected_school_ids"] = affected_school_ids

        # 3. Sync tech tags
        synced_author_ids = [
            a.openalex_author_id for a in std_authors
            if (a.cs_concepts_score or 0.0) >= CS_SCORE_THRESHOLD
        ]

        if synced_author_ids:
            # Batch query talent IDs (batched)
            talent_map = await batch_in_query_map(
                self.session,
                lambda batch: select(Talent.talent_id, Talent.source_record_id)
                    .where(Talent.source_record_id.in_(batch)),
                synced_author_ids,
                key_func=lambda row: row.source_record_id,
                value_func=lambda row: row.talent_id
            )

            # Build belongs map by author
            belongs_by_author = {}
            for b in belongs:
                if b.openalex_author_id not in belongs_by_author:
                    belongs_by_author[b.openalex_author_id] = []
                belongs_by_author[b.openalex_author_id].append(b)

            # Batch sync tech tags
            for openalex_id, talent_id in talent_map.items():
                author_belongs = belongs_by_author.get(openalex_id, [])
                if author_belongs:
                    # Create minimal talent object for tech_tag_sync
                    talent = Talent(talent_id=talent_id)
                    tag_count = await self.tech_tag_sync.sync_talent_tech_tags(
                        talent, author_belongs, default_tech_direction_id
                    )
                    stats["tags_created"] += tag_count

        await self.session.flush()

        logger.info(
            f"[BULK_SYNC] Completed: {stats['authors_synced']} authors "
            f"({stats['authors_created']} created, {stats['authors_updated']} updated), "
            f"{stats['authors_filtered']} filtered, "
            f"{stats['schools_synced']} schools, {stats['tags_created']} tags"
        )

        return stats

    async def _collect_schools_to_sync(self, std_authors: list[StdAuthor]) -> dict:
        """Collect all schools to sync from std_authors.

        Returns:
            dict: Map of openalex_institution_id -> StdSchool
        """
        schools_to_sync = {}
        openalex_inst_ids_to_lookup = set()

        # Legacy: schools via FK relationship
        for std_author in std_authors:
            if std_author.school and std_author.school.openalex_institution_id:
                inst_id = std_author.school.openalex_institution_id
                if inst_id not in schools_to_sync:
                    schools_to_sync[inst_id] = std_author.school

            # Collect primary education/company OpenAlex IDs for lookup
            if std_author.primary_education_id:
                openalex_inst_ids_to_lookup.add(std_author.primary_education_id)
            if std_author.primary_company_id:
                openalex_inst_ids_to_lookup.add(std_author.primary_company_id)

        # Lookup StdSchool by OpenAlex institution ID for primary education/company
        if openalex_inst_ids_to_lookup:
            # Remove IDs already in schools_to_sync
            openalex_inst_ids_to_lookup -= set(schools_to_sync.keys())

            if openalex_inst_ids_to_lookup:
                # Batch query StdSchools (batched)
                std_schools = await batch_in_query_flat(
                    self.session,
                    lambda batch: select(StdSchool).where(
                        StdSchool.openalex_institution_id.in_(batch)
                    ),
                    list(openalex_inst_ids_to_lookup)
                )
                for std_school in std_schools:
                    if std_school.openalex_institution_id:
                        schools_to_sync[std_school.openalex_institution_id] = std_school

        return schools_to_sync
