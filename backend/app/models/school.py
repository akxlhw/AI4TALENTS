"""
School model.
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class School(Base, TimestampMixin):
    """School/university model."""

    __tablename__ = "core_school"

    school_id = Column(Integer, primary_key=True, index=True)
    school_name = Column(String(255), nullable=False, index=True)
    school_alias = Column(String(255), nullable=True)
    country_id = Column(Integer, ForeignKey("core_country.country_id"), nullable=False, index=True)
    school_intro = Column(Text, nullable=True)
    homepage_url = Column(String(500), nullable=True)

    # Cached statistics (updated from snapshots)
    professor_count = Column(Integer, default=0)
    student_count = Column(Integer, default=0)

    # Status fields
    is_visible = Column(Boolean, default=True, nullable=False)
    status = Column(String(20), default="active", nullable=False)

    # Top school flag - 管理员配置的Top院校标记
    is_top_school = Column(Boolean, default=False, nullable=False, index=True)

    # Source tracking
    source_type = Column(String(50), nullable=True)
    source_record_id = Column(String(100), nullable=True, index=True)
    last_sync_batch_id = Column(Integer, nullable=True)

    # Reserved fields for future expansion
    department_name = Column(String(255), nullable=True)
    lab_name = Column(String(255), nullable=True)

    # Relationships
    country = relationship("Country", back_populates="schools")
    talents = relationship("Talent", back_populates="school")
    aliases = relationship("SchoolAlias", back_populates="school")

    def __repr__(self):
        return f"<School(school_id={self.school_id}, name={self.school_name})>"


class SchoolAlias(Base, TimestampMixin):
    """School alias/alternative names for search and matching."""

    __tablename__ = "core_school_alias"

    alias_id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("core_school.school_id"), nullable=False, index=True)
    alias_name = Column(String(255), nullable=False, index=True)
    alias_type = Column(String(50), nullable=True)  # e.g., 'abbreviation', 'former_name', 'local_name'

    # Relationships
    school = relationship("School", back_populates="aliases")

    def __repr__(self):
        return f"<SchoolAlias(school_id={self.school_id}, alias={self.alias_name})>"
