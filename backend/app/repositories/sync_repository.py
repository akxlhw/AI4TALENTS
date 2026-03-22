"""
Repository for sync batch operations.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sync import SyncBatch, RawSourceRecord
from app.models.enums import SyncJobStatus, SourceType


class SyncBatchRepository:
    """Repository for SyncBatch operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_batch(
        self,
        batch_type: str,
        source_type: str = SourceType.OPENALEX.value,
        config_snapshot: Optional[Dict] = None,
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
        error_message: Optional[str] = None,
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

    async def get_batch(self, batch_id: int) -> Optional[SyncBatch]:
        """Get batch by ID."""
        result = await self.session.execute(
            select(SyncBatch).where(SyncBatch.batch_id == batch_id)
        )
        return result.scalar_one_or_none()

    async def get_batch_by_code(self, batch_code: str) -> Optional[SyncBatch]:
        """Get batch by code."""
        result = await self.session.execute(
            select(SyncBatch).where(SyncBatch.batch_code == batch_code)
        )
        return result.scalar_one_or_none()

    async def get_recent_batches(
        self,
        limit: int = 10,
        source_type: Optional[str] = None,
    ) -> List[SyncBatch]:
        """Get recent batches."""
        query = select(SyncBatch).order_by(SyncBatch.batch_id.desc()).limit(limit)

        if source_type:
            query = query.where(SyncBatch.source_type == source_type)

        result = await self.session.execute(query)
        return list(result.scalars().all())


class RawSourceRecordRepository:
    """Repository for RawSourceRecord operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_record(
        self,
        batch_id: int,
        source_type: str,
        source_id: str,
        raw_data: Dict[str, Any],
    ) -> RawSourceRecord:
        """
        Save a raw source record.

        Args:
            batch_id: Associated batch ID
            source_type: 'institution', 'author', or 'work'
            source_id: OpenAlex ID
            raw_data: Raw JSON data

        Returns:
            Created RawSourceRecord
        """
        record = RawSourceRecord(
            batch_id=batch_id,
            source_type=source_type,
            source_id=source_id,
            raw_data=raw_data,
            processed_status="pending",
            fetched_at=datetime.now(),
        )

        self.session.add(record)
        await self.session.flush()

        return record

    async def save_records_batch(
        self,
        batch_id: int,
        source_type: str,
        records: List[Dict[str, Any]],
        id_field: str = "id",
    ) -> int:
        """
        Save multiple raw records in batch.

        Args:
            batch_id: Associated batch ID
            source_type: 'institution', 'author', or 'work'
            records: List of raw records
            id_field: Field name for the ID in the record

        Returns:
            Number of records saved
        """
        count = 0
        for record_data in records:
            source_id = record_data.get(id_field, "")
            if source_id:
                # Extract ID from URL if needed
                if isinstance(source_id, str) and source_id.startswith("https://"):
                    source_id = source_id.rstrip("/").split("/")[-1]

                await self.save_record(
                    batch_id=batch_id,
                    source_type=source_type,
                    source_id=source_id,
                    raw_data=record_data,
                )
                count += 1

        return count

    async def mark_processed(
        self,
        record_id: int,
        status: str = "processed",
        error_info: Optional[str] = None,
    ) -> None:
        """Mark a record as processed."""
        await self.session.execute(
            update(RawSourceRecord)
            .where(RawSourceRecord.record_id == record_id)
            .values(
                processed_status=status,
                processed_at=datetime.now(),
                error_info=error_info,
            )
        )

    async def get_pending_records(
        self,
        batch_id: int,
        limit: int = 1000,
    ) -> List[RawSourceRecord]:
        """Get pending records for a batch."""
        result = await self.session.execute(
            select(RawSourceRecord)
            .where(
                RawSourceRecord.batch_id == batch_id,
                RawSourceRecord.processed_status == "pending",
            )
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_stats(self, batch_id: int) -> Dict[str, int]:
        """Get processing statistics for a batch."""
        from sqlalchemy import func

        result = await self.session.execute(
            select(
                RawSourceRecord.processed_status,
                func.count(RawSourceRecord.record_id),
            )
            .where(RawSourceRecord.batch_id == batch_id)
            .group_by(RawSourceRecord.processed_status)
        )

        stats = {"pending": 0, "processed": 0, "error": 0}
        for status, count in result:
            stats[status] = count

        return stats
