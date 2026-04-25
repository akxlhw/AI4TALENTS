"""
Repository for sync batch operations.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import SourceType, SyncJobStatus
from app.models.sync import SyncBatch


class SyncBatchRepository:
    """Repository for SyncBatch operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_batch(
        self,
        batch_type: str,
        source_type: str = SourceType.OPENALEX.value,
        config_snapshot: dict | None = None,
        created_by: str = "system",
    ) -> SyncBatch:
        """
        Create a new sync batch.

        Args:
            batch_type: 'full' or 'incremental'
            source_type: Data source type
            config_snapshot: Sync configuration
            created_by: Who initiated the sync

        Returns:
            Created SyncBatch instance
        """
        # Generate batch code
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_code = f"sync_{source_type}_{timestamp}"

        batch = SyncBatch(
            batch_code=batch_code,
            batch_type=batch_type,
            source_type=source_type,
            status=SyncJobStatus.PENDING.value,
            config_snapshot=config_snapshot,
            created_by=created_by,
        )

        self.session.add(batch)
        await self.session.flush()
        await self.session.refresh(batch)

        return batch

    async def start_batch(self, batch_id: int) -> None:
        """Mark batch as running."""
        await self.session.execute(
            update(SyncBatch)
            .where(SyncBatch.batch_id == batch_id)
            .values(
                status=SyncJobStatus.RUNNING.value,
                started_at=datetime.now(),
            )
        )

    async def complete_batch(
        self,
        batch_id: int,
        total_records: int,
        success_records: int,
        failed_records: int,
        error_message: str | None = None,
    ) -> None:
        """Mark batch as completed."""
        status = SyncJobStatus.SUCCESS.value
        if failed_records > 0 and success_records == 0:
            status = SyncJobStatus.FAILED.value
        elif failed_records > 0:
            status = SyncJobStatus.PARTIAL.value

        await self.session.execute(
            update(SyncBatch)
            .where(SyncBatch.batch_id == batch_id)
            .values(
                status=status,
                completed_at=datetime.now(),
                total_records=total_records,
                success_records=success_records,
                failed_records=failed_records,
                error_message=error_message,
            )
        )

    async def fail_batch(self, batch_id: int, error_message: str) -> None:
        """Mark batch as failed."""
        await self.session.execute(
            update(SyncBatch)
            .where(SyncBatch.batch_id == batch_id)
            .values(
                status=SyncJobStatus.FAILED.value,
                completed_at=datetime.now(),
                error_message=error_message,
            )
        )

    async def get_batch(self, batch_id: int) -> SyncBatch | None:
        """Get batch by ID."""
        result = await self.session.execute(select(SyncBatch).where(SyncBatch.batch_id == batch_id))
        return result.scalar_one_or_none()

    async def get_batch_by_code(self, batch_code: str) -> SyncBatch | None:
        """Get batch by code."""
        result = await self.session.execute(
            select(SyncBatch).where(SyncBatch.batch_code == batch_code)
        )
        return result.scalar_one_or_none()

    async def get_recent_batches(
        self,
        limit: int = 10,
        source_type: str | None = None,
    ) -> list[SyncBatch]:
        """Get recent batches."""
        query = select(SyncBatch).order_by(SyncBatch.batch_id.desc()).limit(limit)

        if source_type:
            query = query.where(SyncBatch.source_type == source_type)

        result = await self.session.execute(query)
        return list(result.scalars().all())
