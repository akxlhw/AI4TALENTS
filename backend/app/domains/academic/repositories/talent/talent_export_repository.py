"""Talent export repository with batch and bulk data operations."""

from __future__ import annotations

import logging

from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.domains.academic.models.raw_data import RawWork
from app.domains.academic.models.standardized import StdAuthor
from app.domains.academic.models.talent import Talent

from .base_talent_repository import BaseTalentRepository

logger = logging.getLogger(__name__)


class TalentExportRepository(BaseTalentRepository):
    """Repository for batch and export-oriented talent operations."""

    async def get_by_ids(
        self,
        talent_ids: list[int],
        include_relations: bool = True,
        batch_size: int = 5000,
    ) -> list[Talent]:
        """
        Get multiple talents by IDs with batch processing.

        Uses batch processing to avoid PostgreSQL parameter limit (32767).

        Args:
            talent_ids: List of talent IDs to fetch
            include_relations: If True, load school relationship
            batch_size: Number of IDs per batch (default 5000)

        Returns:
            List of Talent instances
        """
        if not talent_ids:
            return []

        all_talents = []

        for i in range(0, len(talent_ids), batch_size):
            batch_ids = talent_ids[i : i + batch_size]
            query = select(Talent).where(Talent.talent_id.in_(batch_ids))

            if include_relations:
                query = query.options(
                    selectinload(Talent.school),
                    selectinload(Talent.education_school),
                    selectinload(Talent.company_school),
                )

            result = await self.session.execute(query)
            all_talents.extend(result.scalars().all())

        return all_talents

    async def get_paper_titles_for_talents(
        self,
        talent_ids: list[int],
        limit_per_talent: int = 20,
    ) -> dict[int, list[str]]:
        """
        Batch get paper titles for multiple talents.

        Fixes N+1 query problem by using a single query instead of
        one query per talent.

        Data path: Talent.std_author_id → StdAuthor.openalex_author_id → RawWork.author_ids

        Args:
            talent_ids: List of talent IDs
            limit_per_talent: Maximum papers per talent

        Returns:
            Dict mapping talent_id to list of paper titles
        """
        if not talent_ids:
            return {}

        # Batch size for PostgreSQL parameter limit
        BATCH_SIZE = 5000
        result: dict[int, list[str]] = {tid: [] for tid in talent_ids}

        for i in range(0, len(talent_ids), BATCH_SIZE):
            batch_ids = talent_ids[i : i + BATCH_SIZE]

            # Step 1: Get std_author_id → openalex_author_id mapping
            author_query = (
                select(Talent.talent_id, StdAuthor.openalex_author_id)
                .join(StdAuthor, Talent.std_author_id == StdAuthor.std_author_id)
                .where(Talent.talent_id.in_(batch_ids))
                .where(StdAuthor.openalex_author_id.isnot(None))
            )
            author_result = await self.session.execute(author_query)
            talent_to_openalex = {
                row.talent_id: row.openalex_author_id for row in author_result.all()
            }

            if not talent_to_openalex:
                continue

            # Step 2: Batch query paper titles
            openalex_ids = list(talent_to_openalex.values())

            # Build OR conditions for author_ids search
            # author_ids is stored as JSON text, use LIKE pattern matching
            conditions = []
            for oid in openalex_ids:
                conditions.append(RawWork.author_ids.ilike(f'%"{oid}"%'))

            paper_query = (
                select(RawWork.author_ids, RawWork.title)
                .where(or_(*conditions))
                .limit(len(openalex_ids) * limit_per_talent)
            )
            paper_result = await self.session.execute(paper_query)

            # Step 3: Map papers back to talents
            for row in paper_result.all():
                if not row.title:
                    continue
                # Find which talent this paper belongs to
                for talent_id, openalex_id in talent_to_openalex.items():
                    if openalex_id and f'"{openalex_id}"' in (row.author_ids or ""):
                        if len(result[talent_id]) < limit_per_talent:
                            result[talent_id].append(row.title)
                        break  # Each paper maps to one talent in our query

        return result
