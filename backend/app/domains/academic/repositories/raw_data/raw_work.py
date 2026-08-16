"""RawWorkRepository — split from raw_data_repository.py (P2-3)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.academic.models.raw_data import RawWork

logger = logging.getLogger(__name__)


class RawWorkRepository:
    """Raw work repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, work: RawWork) -> RawWork:
        """Create a raw work record"""
        self.session.add(work)
        await self.session.flush()
        await self.session.refresh(work)
        return work

    async def upsert(self, work: RawWork) -> RawWork:
        """Create or update a raw work record.

        First checks if the work exists, then updates or creates accordingly.
        This approach avoids transaction state issues with exception handling.
        """
        # Check if work already exists
        existing = await self.get_by_openalex_id(work.openalex_work_id)
        if existing:
            # Update existing record
            existing.raw_json = work.raw_json
            existing.title = work.title
            existing.doi = work.doi
            existing.publication_year = work.publication_year
            existing.source_id = work.source_id
            existing.source_name = work.source_name
            existing.author_count = work.author_count
            existing.author_ids = work.author_ids
            existing.fetched_at = datetime.now(timezone.utc).replace(tzinfo=None)
            existing.fetch_task_id = work.fetch_task_id
            existing.sub_task_id = work.sub_task_id
            await self.session.flush()
            return existing
        else:
            # Create new record
            return await self.create(work)

    async def get_by_openalex_id(self, openalex_id: str) -> RawWork | None:
        """Get raw work by OpenAlex ID"""
        result = await self.session.execute(
            select(RawWork).where(RawWork.openalex_work_id == openalex_id)
        )
        return result.scalar_one_or_none()

    async def get_by_source(
        self,
        source_id: str,
        year_from: int | None = None,
        year_to: int | None = None,
        limit: int = 10000,
    ) -> list[RawWork]:
        """Get works by source (venue) ID"""
        query = select(RawWork).where(RawWork.source_id == source_id)
        if year_from:
            query = query.where(RawWork.publication_year >= year_from)
        if year_to:
            query = query.where(RawWork.publication_year <= year_to)
        query = query.order_by(RawWork.publication_year.desc()).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_author_ids_by_task(self, task_id: int) -> set[str]:
        """Extract unique author IDs from works collected in a specific task.

        Args:
            task_id: The fetch task ID to filter by

        Returns:
            Set of unique OpenAlex author IDs
        """
        result = await self.session.execute(
            select(RawWork.author_ids).where(RawWork.fetch_task_id == task_id)
        )
        author_ids = set()
        for row in result.fetchall():
            if row[0]:
                try:
                    ids = json.loads(row[0])
                    author_ids.update(ids)
                except (json.JSONDecodeError, TypeError):
                    pass
        return author_ids

    async def get_pending(self, limit: int = 100) -> list[RawWork]:
        """Get pending works for processing"""
        result = await self.session.execute(
            select(RawWork).where(RawWork.processed_status == "pending").limit(limit)
        )
        return list(result.scalars().all())

    async def mark_processed(
        self, work_id: int, status: str = "processed", error: str | None = None
    ) -> None:
        """Mark work as processed"""
        values = {
            "processed_status": status,
            "processed_at": datetime.now(timezone.utc).replace(tzinfo=None),
        }
        if error:
            values["error_info"] = error
        await self.session.execute(
            update(RawWork).where(RawWork.raw_work_id == work_id).values(**values)
        )

    async def batch_upsert(self, works: list[RawWork]) -> int:
        """Batch create or update works using PostgreSQL INSERT ON CONFLICT.

        This eliminates N+1 queries from individual upserts.
        """
        if not works:
            return 0

        values = []
        for work in works:
            values.append(
                {
                    "openalex_work_id": work.openalex_work_id,
                    "raw_json": work.raw_json,
                    "title": work.title,
                    "doi": work.doi,
                    "publication_year": work.publication_year,
                    "publication_date": work.publication_date,
                    "source_id": work.source_id,
                    "source_name": work.source_name,
                    "author_count": work.author_count,
                    "author_ids": work.author_ids,
                    "fetch_task_id": work.fetch_task_id,
                    "sub_task_id": work.sub_task_id,
                    "fetched_at": work.fetched_at,
                }
            )

        stmt = pg_insert(RawWork).values(values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["openalex_work_id"],
            set_={
                "raw_json": stmt.excluded.raw_json,
                "title": stmt.excluded.title,
                "doi": stmt.excluded.doi,
                "publication_year": stmt.excluded.publication_year,
                "publication_date": stmt.excluded.publication_date,
                "source_id": stmt.excluded.source_id,
                "source_name": stmt.excluded.source_name,
                "author_count": stmt.excluded.author_count,
                "author_ids": stmt.excluded.author_ids,
                "fetched_at": stmt.excluded.fetched_at,
                "fetch_task_id": stmt.excluded.fetch_task_id,
                "sub_task_id": stmt.excluded.sub_task_id,
            },
        )
        await self.session.execute(stmt)
        return len(works)
