"""
Standardized data layer models.
标准化层模型 - 经过清洗和归一的数据
"""

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class StdAuthor(Base, TimestampMixin):
    """标准化作者表 - 清洗后的作者数据"""

    __tablename__ = "std_author"

    std_author_id = Column(Integer, primary_key=True, index=True)

    # Link to raw data
    openalex_author_id = Column(String(50), nullable=False, unique=True, index=True)

    # Normalized fields
    name_normalized = Column(String(255), nullable=False, index=True)  # 清洗后的姓名
    name_original = Column(String(255), nullable=True)  # 原始姓名
    orcid = Column(String(50), nullable=True, index=True)

    # Academic metrics (from Authors API)
    works_count = Column(Integer, default=0)
    cited_by_count = Column(Integer, default=0)
    h_index = Column(Integer, default=0)
    i10_index = Column(Integer, default=0)

    # Institution reference (after normalization) - legacy field
    std_school_id = Column(
        Integer, ForeignKey("std_school.std_school_id"), nullable=True, index=True
    )

    # Raw institution info for matching (legacy field)
    raw_institution_name = Column(String(255), nullable=True)
    raw_institution_id = Column(String(50), nullable=True)

    # Primary institutions (extracted from affiliations by publication count)
    primary_education_id = Column(String(50), nullable=True)
    primary_education_name = Column(String(255), nullable=True)
    primary_company_id = Column(String(50), nullable=True)
    primary_company_name = Column(String(255), nullable=True)

    # Status
    confirm_status = Column(String(20), default="auto_identified", nullable=False, index=True)
    # auto_identified: 自动识别
    # confirmed: 已确认
    # pending_confirm: 待确认
    # pending_school: 学校待确认

    # Confidence score
    confidence_score = Column(Float, default=0.8)

    # Research topics from OpenAlex (topics field)
    openalex_topics = Column(JSON, default=[])

    # CS background score (0.0-1.0), calculated from OpenAlex x_concepts
    # Used to filter non-CS/AI background authors
    cs_concepts_score = Column(Float, default=0.0)

    # Processing metadata
    source_task_id = Column(Integer, ForeignKey("sync_collect_task.task_id"), nullable=True)
    normalized_at = Column(DateTime, nullable=True)

    # Relationships
    school = relationship("StdSchool", back_populates="authors")
    talent = relationship("Talent", back_populates="std_author", uselist=False)

    def __repr__(self) -> str:
        return f"<StdAuthor(id={self.std_author_id}, name={self.name_normalized})>"


class StdSchool(Base, TimestampMixin):
    """标准化学校表 - 归一后的学校数据"""

    __tablename__ = "std_school"

    std_school_id = Column(Integer, primary_key=True, index=True)

    # OpenAlex ID for matching
    openalex_institution_id = Column(String(50), nullable=True, unique=True, index=True)

    # Normalized name
    name_normalized = Column(String(255), nullable=False, index=True)

    # Alternative names/aliases (JSON array)
    name_aliases = Column(Text, nullable=True)

    # Country (country_id removed - use country_code directly)
    country_code = Column(String(10), nullable=True, index=True)
    country_name = Column(String(100), nullable=True)

    # ROR ID for additional matching
    ror = Column(String(50), nullable=True, index=True)

    # Institution type
    inst_type = Column(String(50), nullable=True)  # education, company, government, etc.

    # Homepage
    homepage_url = Column(String(500), nullable=True)

    # Status
    confirm_status = Column(String(20), default="auto_identified", nullable=False, index=True)
    # auto_identified: 自动识别
    # confirmed: 已确认
    # pending_confirm: 待确认
    # pending_merge: 待合并

    # Link to serving layer school
    school_id = Column(Integer, ForeignKey("core_school.school_id"), nullable=True, index=True)

    # Processing metadata
    source_task_id = Column(Integer, ForeignKey("sync_collect_task.task_id"), nullable=True)
    normalized_at = Column(DateTime, nullable=True)

    # Relationships
    authors = relationship("StdAuthor", back_populates="school")

    def __repr__(self) -> str:
        return f"<StdSchool(id={self.std_school_id}, name={self.name_normalized})>"


class SchoolNameAlias(Base, TimestampMixin):
    """学校名称别名表 - 用于学校归一匹配"""

    __tablename__ = "std_school_alias"
    __table_args__ = (Index("ix_school_alias_name", "alias_name"),)

    alias_id = Column(Integer, primary_key=True, index=True)
    std_school_id = Column(
        Integer, ForeignKey("std_school.std_school_id"), nullable=False, index=True
    )

    alias_name = Column(String(255), nullable=False, index=True)
    alias_type = Column(
        String(30), nullable=True
    )  # abbreviation, former_name, local_name, translation

    # Source of this alias
    source = Column(String(50), nullable=True)  # openalex, manual, wikipedia

    def __repr__(self) -> str:
        return f"<SchoolNameAlias(school_id={self.std_school_id}, alias={self.alias_name})>"
