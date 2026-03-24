"""
Sync and data pipeline models.
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin
from app.models.enums import SyncJobStatus, SourceType


class SyncBatch(Base, TimestampMixin):
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


class RawSourceRecord(Base, TimestampMixin):
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


class CollectScope(Base, TimestampMixin):
    """采集范围配置"""

    __tablename__ = "sync_collect_scope"

    scope_id = Column(Integer, primary_key=True, index=True)
    scope_code = Column(String(50), unique=True, nullable=False, index=True)
    scope_name = Column(String(100), nullable=False)

    # Scope definition
    scope_type = Column(String(30), nullable=False)  # 'tech_element', 'country', 'school', 'custom'
    scope_value = Column(JSON, nullable=False)  # JSON array of IDs or codes

    # Status
    is_enabled = Column(Boolean, default=True, nullable=False)

    # Description
    description = Column(Text, nullable=True)

    # Created by
    created_by = Column(Integer, ForeignKey("iam_user_account.user_id"), nullable=True)

    def __repr__(self):
        return f"<CollectScope(scope_id={self.scope_id}, name={self.scope_name})>"


class CollectStrategy(Base, TimestampMixin):
    """采集策略配置"""

    __tablename__ = "sync_collect_strategy"

    strategy_id = Column(Integer, primary_key=True, index=True)
    strategy_code = Column(String(50), unique=True, nullable=False, index=True)
    strategy_name = Column(String(100), nullable=False)

    # Strategy type
    strategy_type = Column(String(30), default="scheduled", nullable=False)  # 'scheduled', 'manual', 'event_triggered'

    # Schedule config (for scheduled type)
    schedule_cron = Column(String(100), nullable=True)  # Cron expression

    # Scope filter
    scope_ids = Column(JSON, nullable=True)  # Array of scope_ids to apply

    # Data types to collect
    data_types = Column(JSON, nullable=False)  # ['authors', 'works', 'institutions']

    # Fetch config
    fetch_config = Column(JSON, nullable=True)  # {'max_records': 1000, 'since_date': '2024-01-01'}

    # Status
    is_enabled = Column(Boolean, default=True, nullable=False)

    # Description
    description = Column(Text, nullable=True)

    # Created by
    created_by = Column(Integer, ForeignKey("iam_user_account.user_id"), nullable=True)

    # Last run info
    last_run_at = Column(DateTime, nullable=True)
    last_run_status = Column(String(20), nullable=True)

    def __repr__(self):
        return f"<CollectStrategy(strategy_id={self.strategy_id}, name={self.strategy_name})>"


class CollectTask(Base, TimestampMixin):
    """采集任务"""

    __tablename__ = "sync_collect_task"

    task_id = Column(Integer, primary_key=True, index=True)
    task_code = Column(String(50), unique=True, nullable=False, index=True)

    # Associated strategy
    strategy_id = Column(Integer, ForeignKey("sync_collect_strategy.strategy_id"), nullable=True, index=True)

    # Task type
    task_type = Column(String(30), nullable=False)  # 'scheduled', 'manual', 'retry'

    # Trigger info
    triggered_by = Column(Integer, ForeignKey("iam_user_account.user_id"), nullable=True)  # user_id or null for system
    triggered_at = Column(DateTime, nullable=False)

    # Status
    status = Column(String(20), default="pending", nullable=False, index=True)  # pending/running/completed/failed/cancelled

    # Progress
    progress_percent = Column(Integer, default=0)
    current_step = Column(String(100), nullable=True)

    # Counts
    total_records = Column(Integer, default=0)
    processed_records = Column(Integer, default=0)
    success_records = Column(Integer, default=0)
    failed_records = Column(Integer, default=0)
    skipped_records = Column(Integer, default=0)

    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Error info
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)

    # Result summary
    result_summary = Column(JSON, nullable=True)

    def __repr__(self):
        return f"<CollectTask(task_id={self.task_id}, status={self.status})>"

