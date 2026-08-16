"""RawAuthorRepository — split from raw_data_repository.py (P2-3)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.academic.models.raw_data import RawAuthor

logger = logging.getLogger(__name__)


class RawAuthorRepository:
    """Raw author repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, author: RawAuthor) -> RawAuthor:
        """Create a raw author record"""
        self.session.add(author)
        await self.session.flush()
        await self.session.refresh(author)
        return author

    async def upsert(self, author: RawAuthor) -> RawAuthor:
        """Create or update a raw author record.

        First checks if the author exists, then updates or creates accordingly.
        This approach avoids transaction state issues with exception handling.
        """
        # Check if author already exists
        existing = await self.get_by_openalex_id(author.openalex_author_id)
        if existing:
            # Update existing record
            existing.raw_json = author.raw_json
            existing.display_name = author.display_name
            existing.orcid = author.orcid
            existing.works_count = author.works_count
            existing.cited_by_count = author.cited_by_count
            existing.h_index = author.h_index
            existing.i10_index = author.i10_index
            existing.last_known_institution_id = author.last_known_institution_id
            existing.last_known_institution_name = author.last_known_institution_name
            existing.fetched_at = datetime.now(timezone.utc).replace(tzinfo=None)
            existing.fetch_task_id = author.fetch_task_id
            await self.session.flush()
            return existing
        else:
            # Create new record
            return await self.create(author)

    async def batch_upsert(self, authors: list[RawAuthor]) -> int:
        """
        Batch create or update authors using PostgreSQL INSERT ON CONFLICT.

        This is much faster than individual upserts as it:
        1. Uses a single SQL statement
        2. Avoids N+1 queries
        3. Reduces round-trips to database

        Args:
            authors: List of RawAuthor objects to upsert

        Returns:
            Number of authors processed
        """
        if not authors:
            return 0

        # Prepare data for bulk insert
        values = []
        for author in authors:
            values.append(
                {
                    "openalex_author_id": author.openalex_author_id,
                    "raw_json": author.raw_json,
                    "display_name": author.display_name,
                    "orcid": author.orcid,
                    "works_count": author.works_count,
                    "cited_by_count": author.cited_by_count,
                    "h_index": author.h_index,
                    "i10_index": author.i10_index,
                    "last_known_institution_id": author.last_known_institution_id,
                    "last_known_institution_name": author.last_known_institution_name,
                    "primary_education_id": author.primary_education_id,
                    "primary_education_name": author.primary_education_name,
                    "primary_company_id": author.primary_company_id,
                    "primary_company_name": author.primary_company_name,
                    "fetch_task_id": author.fetch_task_id,
                    "fetched_at": datetime.now(timezone.utc).replace(tzinfo=None),
                }
            )

        # Use PostgreSQL INSERT ON CONFLICT for efficient upsert
        stmt = pg_insert(RawAuthor).values(values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["openalex_author_id"],
            set_={
                "raw_json": stmt.excluded.raw_json,
                "display_name": stmt.excluded.display_name,
                "orcid": stmt.excluded.orcid,
                "works_count": stmt.excluded.works_count,
                "cited_by_count": stmt.excluded.cited_by_count,
                "h_index": stmt.excluded.h_index,
                "i10_index": stmt.excluded.i10_index,
                "last_known_institution_id": stmt.excluded.last_known_institution_id,
                "last_known_institution_name": stmt.excluded.last_known_institution_name,
                "primary_education_id": stmt.excluded.primary_education_id,
                "primary_education_name": stmt.excluded.primary_education_name,
                "primary_company_id": stmt.excluded.primary_company_id,
                "primary_company_name": stmt.excluded.primary_company_name,
                "fetch_task_id": stmt.excluded.fetch_task_id,
                "fetched_at": stmt.excluded.fetched_at,
            },
        )

        await self.session.execute(stmt)
        return len(authors)

    async def get_by_openalex_id(self, openalex_id: str) -> RawAuthor | None:
        """Get raw author by OpenAlex ID"""
        result = await self.session.execute(
            select(RawAuthor).where(RawAuthor.openalex_author_id == openalex_id)
        )
        return result.scalar_one_or_none()

    async def get_by_openalex_ids(
        self, openalex_ids: list[str], batch_size: int = 500
    ) -> list[RawAuthor]:
        """Get raw authors by multiple OpenAlex IDs.

        Args:
            openalex_ids: List of OpenAlex author IDs
            batch_size: Number of IDs to query per batch
        """
        if not openalex_ids:
            return []

        # Batch queries to avoid large IN clauses
        results = []
        for i in range(0, len(openalex_ids), batch_size):
            batch = openalex_ids[i : i + batch_size]
            result = await self.session.execute(
                select(RawAuthor).where(RawAuthor.openalex_author_id.in_(batch))
            )
            results.extend(result.scalars().all())

        return results

    async def get_missing_author_ids(
        self, author_ids: list[str], batch_size: int = 500
    ) -> list[str]:
        """Find author IDs that are not yet in the database.

        Args:
            author_ids: List of OpenAlex author IDs to check
            batch_size: Number of IDs to query per batch
        """
        if not author_ids:
            return []

        # Batch queries to avoid large IN clauses
        existing_ids = set()
        for i in range(0, len(author_ids), batch_size):
            batch = author_ids[i : i + batch_size]
            existing = await self.session.execute(
                select(RawAuthor.openalex_author_id).where(RawAuthor.openalex_author_id.in_(batch))
            )
            existing_ids.update(row[0] for row in existing.all())

        return [aid for aid in author_ids if aid not in existing_ids]

    async def get_pending(
        self, task_id: int | None = None, limit: int | None = None
    ) -> list[RawAuthor]:
        """Get pending authors for processing.

        Args:
            task_id: Optional task ID to filter by. If provided, only returns
                     authors from the specified task.
            limit: Optional batch size limit to avoid loading all pending
                   authors into memory at once.
        """
        query = select(RawAuthor).where(RawAuthor.processed_status == "pending")
        if task_id is not None:
            query = query.where(RawAuthor.fetch_task_id == task_id)
        if limit is not None:
            query = query.limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def mark_processed(
        self, author_id: int, status: str = "processed", std_author_id: int | None = None
    ) -> None:
        """Mark author as processed"""
        values = {
            "processed_status": status,
            "processed_at": datetime.now(timezone.utc).replace(tzinfo=None),
        }
        if std_author_id:
            values["std_author_id"] = std_author_id
        await self.session.execute(
            update(RawAuthor).where(RawAuthor.raw_author_id == author_id).values(**values)
        )

    async def batch_mark_processed(
        self,
        author_ids: list[int],
        status: str = "processed",
        std_author_id_map: dict[int, int] | None = None,
    ) -> None:
        """Mark multiple authors as processed in a single UPDATE.

        Args:
            author_ids: List of RawAuthor IDs to mark.
            status: New processed_status value.
            std_author_id_map: Optional dict mapping raw_author_id -> std_author_id.
        """
        if not author_ids:
            return

        # For authors with the same std_author_id, we can use a simple UPDATE ... WHERE IN
        # For authors with different std_author_id values, we use CASE WHEN.
        if std_author_id_map and len(set(std_author_id_map.values())) > 1:
            # Multiple different std_author_ids: use CASE WHEN
            case_stmt = "CASE raw_author_id "
            for raw_id, std_id in std_author_id_map.items():
                if raw_id in author_ids:
                    case_stmt += f"WHEN {raw_id} THEN {std_id} "
            case_stmt += "END"
            await self.session.execute(
                update(RawAuthor)
                .where(RawAuthor.raw_author_id.in_(author_ids))
                .values(
                    processed_status=status,
                    processed_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    std_author_id=text(case_stmt),
                )
            )
        elif std_author_id_map and len(set(std_author_id_map.values())) == 1:
            # All same std_author_id (unlikely but optimize for it)
            std_author_id = list(std_author_id_map.values())[0]
            await self.session.execute(
                update(RawAuthor)
                .where(RawAuthor.raw_author_id.in_(author_ids))
                .values(
                    processed_status=status,
                    processed_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    std_author_id=std_author_id,
                )
            )
        else:
            await self.session.execute(
                update(RawAuthor)
                .where(RawAuthor.raw_author_id.in_(author_ids))
                .values(
                    processed_status=status,
                    processed_at=datetime.now(timezone.utc).replace(tzinfo=None),
                )
            )
