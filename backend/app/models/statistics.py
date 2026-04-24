"""
Statistics snapshot models.
"""
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class OverviewStatSnapshot(Base):
    """Overview statistics snapshot for homepage."""

    __tablename__ = "stat_overview_snapshot"

    snapshot_id = Column(Integer, primary_key=True, index=True)
    stat_version = Column(String(50), nullable=False, index=True)
    generated_at = Column(String(50), nullable=False)  # ISO datetime string

    # Statistics
    school_count = Column(Integer, default=0)
    professor_count = Column(Integer, default=0)
    student_count = Column(Integer, default=0)
    talent_count = Column(Integer, default=0)
    country_count = Column(Integer, default=0)  # 覆盖国家数
    tech_domain_count = Column(Integer, default=0)  # 技术领域数
    tech_direction_count = Column(Integer, default=0)  # 技术方向数

    # Metadata
    generated_by_batch_id = Column(Integer, nullable=True)
    is_active = Column(Integer, default=1)  # 1 for active, 0 for inactive

    def __repr__(self) -> str:
        return f"<OverviewStatSnapshot(version={self.stat_version}, schools={self.school_count})>"


class SchoolStatSnapshot(Base):
    """School-level statistics snapshot."""

    __tablename__ = "stat_school_snapshot"

    snapshot_id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("core_school.school_id"), nullable=False, index=True)
    stat_version = Column(String(50), nullable=False, index=True)
    generated_at = Column(String(50), nullable=False)

    # Statistics
    professor_count = Column(Integer, default=0)
    student_count = Column(Integer, default=0)
    talent_count = Column(Integer, default=0)

    # Breakdown by role (optional)
    graduate_count = Column(Integer, default=0)
    unknown_count = Column(Integer, default=0)

    # Metadata
    generated_by_batch_id = Column(Integer, nullable=True)
    is_active = Column(Integer, default=1)

    # Relationships
    school = relationship("School")

    def __repr__(self) -> str:
        return f"<SchoolStatSnapshot(school_id={self.school_id}, version={self.stat_version})>"
