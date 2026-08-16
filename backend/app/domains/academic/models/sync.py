"""
Sync and data pipeline models.
"""

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.domains.shared.models.base import TimestampMixin
from app.domains.shared.models.enums import SourceType, SyncJobStatus


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
    error_details = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    # Metadata
    created_by = Column(String(50), default="system")
    config_snapshot = Column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )  # Store sync configuration

    def __repr__(self) -> str:
        return f"<SyncBatch(batch_id={self.batch_id}, status={self.status})>"


class CollectScope(Base, TimestampMixin):
    """采集范围配置"""

    __tablename__ = "sync_collect_scope"

    scope_id = Column(Integer, primary_key=True, index=True)
    scope_code = Column(String(50), unique=True, nullable=False, index=True)
    scope_name = Column(String(100), nullable=False)

    # Scope definition
    scope_type = Column(String(30), nullable=False)  # 'tech_domain', 'country', 'school', 'custom'
    scope_value = Column(JSON, nullable=False)  # JSON array of IDs or codes

    # Status
    is_enabled = Column(Boolean, default=True, nullable=False)

    # Description
    description = Column(Text, nullable=True)

    # Created by
    created_by = Column(Integer, ForeignKey("iam_user_account.user_id"), nullable=True)

    def __repr__(self) -> str:
        return f"<CollectScope(scope_id={self.scope_id}, name={self.scope_name})>"


class CollectStrategy(Base, TimestampMixin):
    """采集策略配置"""

    __tablename__ = "sync_collect_strategy"

    strategy_id = Column(Integer, primary_key=True, index=True)
    strategy_code = Column(String(50), unique=True, nullable=False, index=True)
    strategy_name = Column(String(100), nullable=False)

    # Strategy type
    strategy_type = Column(
        String(30), default="scheduled", nullable=False
    )  # 'scheduled', 'manual', 'event_triggered'

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

    def __repr__(self) -> str:
        return f"<CollectStrategy(strategy_id={self.strategy_id}, name={self.strategy_name})>"


class CollectTask(Base, TimestampMixin):
    """采集任务 - 简化版，直接关联技术领域"""

    __tablename__ = "sync_collect_task"

    task_id = Column(Integer, primary_key=True, index=True)
    task_code = Column(String(50), unique=True, nullable=False, index=True)

    # 旧字段（保留以兼容现有数据库）
    strategy_id = Column(Integer, nullable=True)  # 不再使用，保留兼容
    task_type = Column(String(30), default="manual", nullable=False)  # 保留兼容

    # 关联技术领域（采集最小单位）
    tech_domain_id = Column(
        Integer, ForeignKey("core_tech_domain.tech_domain_id"), nullable=True, index=True
    )

    # 采集模式：full=全量, incremental=增量
    collect_mode = Column(String(20), default="full", nullable=False)

    # Time window for collection
    time_window_start = Column(DateTime, nullable=True)
    time_window_end = Column(DateTime, nullable=True)

    # Trigger info
    triggered_by = Column(Integer, ForeignKey("iam_user_account.user_id"), nullable=True)
    triggered_at = Column(DateTime, nullable=False)

    # Status
    status = Column(
        String(20), default="pending", nullable=False, index=True
    )  # pending/running/completed/failed/cancelled

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
    error_details = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    # Result summary
    result_summary = Column(JSON, nullable=True)

    # Execution logs - 新增字段
    execution_logs = Column(JSON, nullable=True)  # List of {timestamp, level, message}

    # Venue snapshot - 保存创建时的顶会顶刊配置
    venue_snapshot = Column(JSON, nullable=True)  # List of {id, name, type}

    # Checkpoint for resume support
    last_completed_phase = Column(String(50), nullable=True)

    # Relationships
    tech_domain = relationship("TechDomain")

    def __repr__(self) -> str:
        return f"<CollectTask(task_id={self.task_id}, status={self.status})>"


class DataVersion(Base, TimestampMixin):
    """数据版本"""

    __tablename__ = "data_version"

    version_id = Column(Integer, primary_key=True, index=True)
    version_code = Column(String(50), unique=True, nullable=False, index=True)
    version_name = Column(String(100), nullable=False)

    # Version info
    version_type = Column(String(20), default="snapshot", nullable=False)  # 'snapshot', 'release'
    base_version_id = Column(Integer, ForeignKey("data_version.version_id"), nullable=True)

    # Source task
    source_task_id = Column(Integer, ForeignKey("sync_collect_task.task_id"), nullable=True)

    # Statistics
    total_talents = Column(Integer, default=0)
    total_schools = Column(Integer, default=0)
    total_works = Column(Integer, default=0)

    # Status
    is_active = Column(
        Boolean, default=False, nullable=False, index=True
    )  # Currently active version
    is_published = Column(Boolean, default=False, nullable=False)

    # Publish info
    published_at = Column(DateTime, nullable=True)
    published_by = Column(Integer, ForeignKey("iam_user_account.user_id"), nullable=True)

    # Description
    description = Column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<DataVersion(version_id={self.version_id}, code={self.version_code})>"


class DataPublishRecord(Base, TimestampMixin):
    """数据发布记录"""

    __tablename__ = "data_publish_record"

    publish_id = Column(Integer, primary_key=True, index=True)
    version_id = Column(Integer, ForeignKey("data_version.version_id"), nullable=False, index=True)

    # Action type
    action = Column(String(20), nullable=False)  # 'publish', 'rollback', 'activate', 'deactivate'

    # Previous state
    previous_version_id = Column(Integer, ForeignKey("data_version.version_id"), nullable=True)

    # Operator
    operated_by = Column(Integer, ForeignKey("iam_user_account.user_id"), nullable=False)
    operated_at = Column(DateTime, nullable=False)

    # Notes
    notes = Column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<DataPublishRecord(publish_id={self.publish_id}, action={self.action})>"


class DataCorrectionRecord(Base, TimestampMixin):
    """数据纠偏记录"""

    __tablename__ = "data_correction_record"

    correction_id = Column(Integer, primary_key=True, index=True)

    # Target info
    target_type = Column(String(30), nullable=False, index=True)  # 'talent', 'school', 'tech_tag'
    target_id = Column(Integer, nullable=False, index=True)

    # Field info
    field_name = Column(String(50), nullable=False)
    original_value = Column(Text, nullable=True)
    corrected_value = Column(Text, nullable=True)

    # Correction type
    correction_type = Column(String(20), nullable=False)  # 'manual', 'system', 'import'

    # Reason
    reason = Column(Text, nullable=True)

    # Source
    source = Column(String(100), nullable=True)  # Where correction came from

    # Operator
    corrected_by = Column(Integer, ForeignKey("iam_user_account.user_id"), nullable=False)

    # Status
    status = Column(
        String(20), default="applied", nullable=False
    )  # 'pending', 'applied', 'reverted'

    def __repr__(self) -> str:
        return (
            f"<DataCorrectionRecord("
            f"correction_id={self.correction_id}, "
            f"target={self.target_type}:{self.target_id})>"
        )


class DataQualitySummary(Base, TimestampMixin):
    """数据质量摘要"""

    __tablename__ = "data_quality_summary"

    summary_id = Column(Integer, primary_key=True, index=True)
    version_id = Column(Integer, ForeignKey("data_version.version_id"), nullable=False, index=True)

    # Summary date
    summary_date = Column(DateTime, nullable=False, index=True)

    # Talent quality metrics
    talent_total = Column(Integer, default=0)
    talent_with_orcid = Column(Integer, default=0)
    talent_with_affiliation = Column(Integer, default=0)
    talent_with_works = Column(Integer, default=0)
    talent_completeness_avg = Column(Integer, default=0)  # Percentage average

    # School quality metrics
    school_total = Column(Integer, default=0)
    school_with_ror = Column(Integer, default=0)
    school_with_country = Column(Integer, default=0)

    # Work quality metrics
    work_total = Column(Integer, default=0)
    work_with_doi = Column(Integer, default=0)

    # Tech tag metrics
    tech_tag_total = Column(Integer, default=0)
    tech_tag_confirmed = Column(Integer, default=0)
    tech_tag_auto_identified = Column(Integer, default=0)
    tech_tag_pending_confirm = Column(Integer, default=0)

    # Issues count
    issues_critical = Column(Integer, default=0)
    issues_warning = Column(Integer, default=0)
    issues_info = Column(Integer, default=0)

    # Additional details
    details = Column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<DataQualitySummary(summary_id={self.summary_id}, version_id={self.version_id})>"
