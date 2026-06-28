"""lab_web domain ORM models.

Three tables with 'lw_' prefix, mirroring the open_source domain conventions
(os_raw_developer -> serving layer). raw layer is append-only.
"""

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.sql import func

from app.core.database import Base
from app.domains.shared.models.base import TimestampMixin


class LWLabRegistry(Base, TimestampMixin):
    """Registry of target AI labs whose People pages we scrape."""

    __tablename__ = "lw_lab_registry"

    lab_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    lab_code = Column(String(50), nullable=False, unique=True, index=True)
    lab_name = Column(String(255), nullable=False)
    lab_name_en = Column(String(255), nullable=True)
    institution = Column(String(255), nullable=False)
    country = Column(String(50), nullable=False)
    people_url = Column(String(500), nullable=False)
    collector_class = Column(String(255), nullable=True)
    fetch_mode = Column(String(20), nullable=False, default="static")
    is_active = Column(Boolean, nullable=False, default=True)
    last_collected_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<LWLabRegistry(lab_id={self.lab_id}, lab_code={self.lab_code})>"


class LWRawPerson(Base):
    """Append-only raw snapshot of a person parsed from a lab People page."""

    __tablename__ = "lw_raw_person"

    raw_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    lab_id = Column(Integer, ForeignKey("lw_lab_registry.lab_id"), nullable=False, index=True)
    source_url = Column(String(500), nullable=True)
    name_raw = Column(String(255), nullable=False)
    title_raw = Column(String(255), nullable=True)
    email_raw = Column(String(255), nullable=True)
    homepage_url = Column(String(500), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    raw_data = Column(JSON, default=dict)
    fetched_at = Column(DateTime, default=func.now(), nullable=False)
    collect_task_id = Column(Integer, nullable=True, index=True)
    # Non-unique index: same person across fetches yields the same hash, and the
    # raw layer is append-only (snapshots for change tracking). Intra-fetch
    # dedup is done in application code before insert.
    content_hash = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<LWRawPerson(raw_id={self.raw_id}, name_raw={self.name_raw})>"


class LWCollectTask(Base):
    """Collection task tracking, mirroring OSCollectTask."""

    __tablename__ = "lw_collect_task"

    task_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    task_name = Column(String(255), nullable=False)
    lab_id = Column(Integer, ForeignKey("lw_lab_registry.lab_id"), nullable=False)
    status = Column(String(20), nullable=False, default="pending", index=True)
    progress_percent = Column(Integer, default=0, nullable=False)
    current_step = Column(String(100), nullable=True)
    total_records = Column(Integer, default=0, nullable=False)
    processed_records = Column(Integer, default=0, nullable=False)
    config_json = Column(JSON, default=dict)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey("iam_user_account.user_id"), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<LWCollectTask(task_id={self.task_id}, status={self.status})>"
