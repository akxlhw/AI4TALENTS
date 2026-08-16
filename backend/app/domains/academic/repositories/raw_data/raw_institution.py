"""RawInstitutionRepository — split from raw_data_repository.py (P2-3)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.academic.models.raw_data import RawInstitution

logger = logging.getLogger(__name__)


class RawInstitutionRepository:
    """Raw institution repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, institution: RawInstitution) -> RawInstitution:
        """Create a raw institution record"""
        self.session.add(institution)
        await self.session.flush()
        await self.session.refresh(institution)
        return institution

    async def upsert(self, institution: RawInstitution) -> RawInstitution:
        """Create or update a raw institution record.

        First checks if the institution exists, then updates or creates accordingly.
        This approach avoids transaction state issues with exception handling.
        """
        # Check if institution already exists
        existing = await self.get_by_openalex_id(institution.openalex_institution_id)
        if existing:
            # Update existing record
            existing.raw_json = institution.raw_json
            existing.display_name = institution.display_name
            existing.country_code = institution.country_code
            existing.country_name = institution.country_name
            existing.ror = institution.ror
            existing.type = institution.type
            existing.fetched_at = datetime.now(timezone.utc).replace(tzinfo=None)
            existing.fetch_task_id = institution.fetch_task_id
            await self.session.flush()
            return existing
        else:
            # Create new record
            return await self.create(institution)

    async def get_by_openalex_id(self, openalex_id: str) -> RawInstitution | None:
        """Get raw institution by OpenAlex ID"""
        result = await self.session.execute(
            select(RawInstitution).where(RawInstitution.openalex_institution_id == openalex_id)
        )
        return result.scalar_one_or_none()

    async def get_by_openalex_ids(
        self, openalex_ids: list[str], batch_size: int = 500
    ) -> list[RawInstitution]:
        """Get raw institutions by multiple OpenAlex IDs.

        Args:
            openalex_ids: List of OpenAlex institution IDs
            batch_size: Number of IDs to query per batch
        """
        if not openalex_ids:
            return []

        # Batch queries to avoid large IN clauses
        results = []
        for i in range(0, len(openalex_ids), batch_size):
            batch = openalex_ids[i : i + batch_size]
            result = await self.session.execute(
                select(RawInstitution).where(RawInstitution.openalex_institution_id.in_(batch))
            )
            results.extend(result.scalars().all())

        return results

    async def get_missing_ids(self, institution_ids: list[str], batch_size: int = 500) -> list[str]:
        """Find institution IDs that are not yet in the database.

        Args:
            institution_ids: List of OpenAlex institution IDs to check
            batch_size: Number of IDs to query per batch
        """
        if not institution_ids:
            return []

        # Batch queries to avoid large IN clauses
        existing_ids = set()
        for i in range(0, len(institution_ids), batch_size):
            batch = institution_ids[i : i + batch_size]
            existing = await self.session.execute(
                select(RawInstitution.openalex_institution_id).where(
                    RawInstitution.openalex_institution_id.in_(batch)
                )
            )
            existing_ids.update(row[0] for row in existing.all())

        return [iid for iid in institution_ids if iid not in existing_ids]

    async def get_pending(self, task_id: int | None = None) -> list[RawInstitution]:
        """Get pending institutions for processing.

        Args:
            task_id: Optional task ID to filter by. If provided, only returns
                     institutions from the specified task.
        """
        query = select(RawInstitution).where(RawInstitution.processed_status == "pending")
        if task_id is not None:
            query = query.where(RawInstitution.fetch_task_id == task_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def mark_processed(
        self, inst_id: int, status: str = "processed", std_school_id: int | None = None
    ) -> None:
        """Mark institution as processed"""
        values = {
            "processed_status": status,
            "processed_at": datetime.now(timezone.utc).replace(tzinfo=None),
        }
        if std_school_id:
            values["std_school_id"] = std_school_id
        await self.session.execute(
            update(RawInstitution)
            .where(RawInstitution.raw_institution_id == inst_id)
            .values(**values)
        )

    async def batch_upsert(self, institutions: list[RawInstitution]) -> int:
        """Batch create or update institutions using PostgreSQL INSERT ON CONFLICT.

        This eliminates N+1 queries from individual upserts.
        """
        if not institutions:
            return 0

        values = []
        for inst in institutions:
            values.append(
                {
                    "openalex_institution_id": inst.openalex_institution_id,
                    "raw_json": inst.raw_json,
                    "display_name": inst.display_name,
                    "country_code": inst.country_code,
                    "country_name": inst.country_name,
                    "ror": inst.ror,
                    "type": inst.type,
                    "fetch_task_id": inst.fetch_task_id,
                    "fetched_at": inst.fetched_at,
                }
            )

        stmt = pg_insert(RawInstitution).values(values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["openalex_institution_id"],
            set_={
                "raw_json": stmt.excluded.raw_json,
                "display_name": stmt.excluded.display_name,
                "country_code": stmt.excluded.country_code,
                "country_name": stmt.excluded.country_name,
                "ror": stmt.excluded.ror,
                "type": stmt.excluded.type,
                "fetch_task_id": stmt.excluded.fetch_task_id,
                "fetched_at": stmt.excluded.fetched_at,
            },
        )
        await self.session.execute(stmt)
        return len(institutions)
