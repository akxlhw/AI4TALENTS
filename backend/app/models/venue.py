"""
Venue and VenueTechBinding models.
顶会顶刊配置与技术领域绑定模型
"""
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class Venue(Base, TimestampMixin):
    """顶会顶刊配置表 - 独立管理采集边界"""

    __tablename__ = "config_venue"

    venue_id = Column(Integer, primary_key=True, index=True)
    venue_code = Column(String(50), unique=True, nullable=False, index=True)
    venue_name = Column(String(255), nullable=False)
    venue_name_en = Column(String(255), nullable=True)

    # OpenAlex source ID (e.g., "S137534324" for NeurIPS)
    openalex_source_id = Column(String(50), unique=True, nullable=True, index=True)

    # Venue type: conference/journal/workshop
    venue_type = Column(String(30), default="conference", nullable=False)

    # Country/region (for conferences)
    country_code = Column(String(10), nullable=True)

    # Publisher info
    publisher = Column(String(100), nullable=True)

    # Metrics (cached from OpenAlex)
    h_index = Column(Integer, default=0)
    works_count = Column(Integer, default=0)
    cited_by_count = Column(Integer, default=0)

    # Status
    is_enabled = Column(Boolean, default=True, nullable=False)

    # Last collection time for this venue
    last_collect_at = Column(DateTime, nullable=True)

    # Description
    description = Column(Text, nullable=True)

    # Relationships
    tech_bindings = relationship("VenueTechBinding", back_populates="venue")

    def __repr__(self):
        return f"<Venue(venue_id={self.venue_id}, name={self.venue_name}, type={self.venue_type})>"


class VenueTechBinding(Base, TimestampMixin):
    """Venue-技术领域绑定关系表"""

    __tablename__ = "config_venue_tech_binding"
    __table_args__ = (
        UniqueConstraint('venue_id', 'tech_domain_id', name='uq_venue_tech_domain'),
    )

    binding_id = Column(Integer, primary_key=True, index=True)

    # Foreign keys
    venue_id = Column(Integer, ForeignKey("config_venue.venue_id"), nullable=False, index=True)
    tech_domain_id = Column(Integer, ForeignKey("core_tech_domain.tech_domain_id"), nullable=False, index=True)

    # Priority within this tech domain (for display order)
    priority = Column(Integer, default=0)

    # Collection status for this venue-tech_domain pair
    collect_status = Column(String(20), default="pending", nullable=False)  # pending/collecting/completed/failed

    # Last collection time for this binding
    last_collect_at = Column(DateTime, nullable=True)

    # Collection statistics
    author_count = Column(Integer, default=0)  # Number of authors collected
    work_count = Column(Integer, default=0)    # Number of works collected

    # Status
    is_enabled = Column(Boolean, default=True, nullable=False)

    # Relationships
    venue = relationship("Venue", back_populates="tech_bindings")
    tech_domain = relationship("TechDomain", back_populates="venue_bindings")

    def __repr__(self):
        return f"<VenueTechBinding(venue_id={self.venue_id}, tech_domain_id={self.tech_domain_id})>"


class VenueSubTask(Base, TimestampMixin):
    """Venue级别子任务表 - 支持细粒度采集追踪"""

    __tablename__ = "sync_venue_sub_task"

    sub_task_id = Column(Integer, primary_key=True, index=True)

    # Parent task
    task_id = Column(Integer, ForeignKey("sync_collect_task.task_id"), nullable=False, index=True)

    # Venue for this sub-task
    venue_id = Column(Integer, ForeignKey("config_venue.venue_id"), nullable=False, index=True)

    # Status
    status = Column(String(20), default="pending", nullable=False, index=True)  # pending/running/completed/failed/skipped

    # Time window for this sub-task
    time_window_start = Column(DateTime, nullable=True)
    time_window_end = Column(DateTime, nullable=True)

    # Counts
    estimated_works = Column(Integer, default=0)  # 预估论文数（采集前获取）
    works_fetched = Column(Integer, default=0)
    authors_fetched = Column(Integer, default=0)
    new_authors = Column(Integer, default=0)
    updated_authors = Column(Integer, default=0)

    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Error info
    error_message = Column(Text, nullable=True)

    # Relationships
    task = relationship("CollectTask")
    venue = relationship("Venue")

    def __repr__(self):
        return f"<VenueSubTask(sub_task_id={self.sub_task_id}, venue_id={self.venue_id}, status={self.status})>"
