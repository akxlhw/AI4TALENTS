"""
Sync and data pipeline models.
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, JSON

from app.core.database import Base
from app.models.enums import SyncJobStatus, SourceType


class SyncBatch(Base):
    """Sync batch record for tracking data synchronization."""

    __tablename__ = "sync_batch"

    batch_id = Column(Integer, primary_key=True, index=True)
    batch_code = Column(String(50), unique=True, nullable=False, index=True)
    batch_type = Column(String(20), nullable=False)  # 'full', 'incremental'

    # Source info
    source_type = Column(String(50), default=SourceType.OPENALEX.value)

    # Status
    status = Column(String(20), default=SyncJobStatus.PENDING.value, nullable=False, index=True)

    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Counts
    total_records = Column(Integer, default=0)
    success_records = Column(Integer, default=0)
    failed_records = Column(Integer, default=0)

    # Error info
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)

    # Metadata
    created_by = Column(String(50), default="system")
    config_snapshot = Column(JSON, nullable=True)  # Store sync configuration

    def __repr__(self):
        return f"<SyncBatch(batch_id={self.batch_id}, status={self.status})>"


class RawSourceRecord(Base):
    """Raw data from external sources."""

    __tablename__ = "raw_source_record"

    record_id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, nullable=False, index=True)

    # Source info
    source_type = Column(String(50), nullable=False, index=True)  # 'institution', 'author', 'work'
    source_id = Column(String(100), nullable=False, index=True)  # OpenAlex ID

    # Raw data
    raw_data = Column(JSON, nullable=False)

    # Processing status
    processed_status = Column(String(20), default="pending", index=True)  # 'pending', 'processed', 'error'
    processed_at = Column(DateTime, nullable=True)
    error_info = Column(Text, nullable=True)

    # Timing
    fetched_at = Column(DateTime, nullable=False)

    def __repr__(self):
        return f"<RawSourceRecord(record_id={self.record_id}, source={self.source_type}:{self.source_id})>"
