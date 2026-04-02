"""
Raw data layer models for OpenAlex entities.
原始数据层模型 - 支持数据回溯、重试和审计
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class RawWork(Base, TimestampMixin):
    """原始论文数据 - 从 OpenAlex Works API 采集"""

    __tablename__ = "raw_work"

    raw_work_id = Column(Integer, primary_key=True, index=True)

    # OpenAlex ID
    openalex_work_id = Column(String(50), nullable=False, unique=True, index=True)

    # Original JSON data
    raw_json = Column(Text, nullable=False)

    # Extracted key fields for quick access
    title = Column(Text, nullable=True)
    doi = Column(String(200), nullable=True, index=True)
    publication_year = Column(Integer, nullable=True, index=True)
    publication_date = Column(String(20), nullable=True)

    # Source venue
    source_id = Column(String(50), nullable=True, index=True)
    source_name = Column(String(255), nullable=True)

    # Author count and IDs
    author_count = Column(Integer, default=0)
    author_ids = Column(Text, nullable=True)  # JSON array of author IDs

    # Processing status
    processed_status = Column(String(20), default="pending", index=True)  # pending/processed/error
    processed_at = Column(DateTime, nullable=True)
    error_info = Column(Text, nullable=True)

    # Collection metadata
    fetched_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    fetch_task_id = Column(Integer, ForeignKey("sync_collect_task.task_id"), nullable=True)

    # Sub-task reference
    sub_task_id = Column(Integer, ForeignKey("sync_venue_sub_task.sub_task_id"), nullable=True)

    def __repr__(self):
        return f"<RawWork(id={self.openalex_work_id}, year={self.publication_year})>"


class RawAuthor(Base, TimestampMixin):
    """原始作者数据 - 从 OpenAlex Authors API 采集"""

    __tablename__ = "raw_author"

    raw_author_id = Column(Integer, primary_key=True, index=True)

    # OpenAlex ID (short format: A123456789)
    openalex_author_id = Column(String(50), nullable=False, unique=True, index=True)

    # Original JSON data
    raw_json = Column(Text, nullable=False)

    # Extracted key fields for quick access
    display_name = Column(String(255), nullable=True, index=True)
    orcid = Column(String(50), nullable=True, index=True)

    # Works and citations
    works_count = Column(Integer, default=0)
    cited_by_count = Column(Integer, default=0)
    h_index = Column(Integer, default=0)
    i10_index = Column(Integer, default=0)

    # Institution
    last_known_institution_id = Column(String(50), nullable=True, index=True)
    last_known_institution_name = Column(String(255), nullable=True)

    # Processing status
    processed_status = Column(String(20), default="pending", index=True)  # pending/processed/error
    processed_at = Column(DateTime, nullable=True)
    error_info = Column(Text, nullable=True)

    # Collection metadata
    fetched_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    fetch_task_id = Column(Integer, ForeignKey("sync_collect_task.task_id"), nullable=True)

    # Normalized reference (after standardization)
    std_author_id = Column(Integer, nullable=True, index=True)

    def __repr__(self):
        return f"<RawAuthor(id={self.openalex_author_id}, name={self.display_name})>"


class RawInstitution(Base, TimestampMixin):
    """原始机构数据 - 从 OpenAlex Institutions API 采集"""

    __tablename__ = "raw_institution"

    raw_institution_id = Column(Integer, primary_key=True, index=True)

    # OpenAlex ID (short format: I123456789)
    openalex_institution_id = Column(String(50), nullable=False, unique=True, index=True)

    # Original JSON data
    raw_json = Column(Text, nullable=False)

    # Extracted key fields
    display_name = Column(String(255), nullable=True, index=True)
    country_code = Column(String(10), nullable=True, index=True)
    country_name = Column(String(100), nullable=True)
    ror = Column(String(50), nullable=True)
    type = Column(String(50), nullable=True)

    # Processing status
    processed_status = Column(String(20), default="pending", index=True)  # pending/processed/error
    processed_at = Column(DateTime, nullable=True)
    error_info = Column(Text, nullable=True)

    # Collection metadata
    fetched_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    fetch_task_id = Column(Integer, ForeignKey("sync_collect_task.task_id"), nullable=True)

    # Normalized reference
    std_school_id = Column(Integer, nullable=True, index=True)

    def __repr__(self):
        return f"<RawInstitution(id={self.openalex_institution_id}, name={self.display_name})>"


class AuthorTechBelong(Base, TimestampMixin):
    """作者-技术要素归属关系表"""

    __tablename__ = "rel_author_tech_belong"
    __table_args__ = (
        Index('ix_author_tech_author_tech', 'openalex_author_id', 'tech_element_id', unique=True),
    )

    belong_id = Column(Integer, primary_key=True, index=True)

    # Author reference (using OpenAlex ID for raw layer linking)
    openalex_author_id = Column(String(50), nullable=False, index=True)

    # After normalization, link to std_author
    std_author_id = Column(Integer, nullable=True, index=True)

    # Tech element reference
    tech_element_id = Column(Integer, ForeignKey("core_tech_element.tech_element_id"), nullable=False, index=True)

    # Source venue where this relationship was established
    source_venue_id = Column(Integer, ForeignKey("config_venue.venue_id"), nullable=True)

    # Work statistics from this venue
    work_count_in_venue = Column(Integer, default=0)
    first_work_year = Column(Integer, nullable=True)
    last_work_year = Column(Integer, nullable=True)

    # Collection metadata
    source_task_id = Column(Integer, ForeignKey("sync_collect_task.task_id"), nullable=True)

    # Relationships
    tech_element = relationship("TechElement")
    venue = relationship("Venue")

    def __repr__(self):
        return f"<AuthorTechBelong(author={self.openalex_author_id}, tech={self.tech_element_id})>"
