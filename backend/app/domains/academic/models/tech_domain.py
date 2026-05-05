"""
Technology Domain and Direction models.
技术领域与技术方向模型
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.domains.shared.models.base import TimestampMixin


class TechDomain(Base, TimestampMixin):
    """技术领域"""

    __tablename__ = "core_tech_domain"

    tech_domain_id = Column(Integer, primary_key=True, index=True)
    domain_code = Column(String(50), unique=True, nullable=False)
    domain_name = Column(String(100), nullable=False)
    domain_name_en = Column(String(100), nullable=True)
    domain_desc = Column(Text, nullable=True)
    sort_order = Column(Integer, default=0)
    is_enabled = Column(Boolean, default=True, nullable=False)

    # 最后采集时间
    last_collect_at = Column(DateTime, nullable=True)

    # Relationships
    directions = relationship("TechDirection", back_populates="tech_domain")
    venue_bindings = relationship("VenueTechBinding", back_populates="tech_domain")

    def __repr__(self) -> str:
        return f"<TechDomain(id={self.tech_domain_id}, name={self.domain_name})>"


class TechDirection(Base, TimestampMixin):
    """技术方向"""

    __tablename__ = "core_tech_direction"

    tech_direction_id = Column(Integer, primary_key=True, index=True)
    direction_code = Column(String(50), unique=True, nullable=False)
    direction_name = Column(String(100), nullable=False)
    direction_name_en = Column(String(100), nullable=True)
    tech_domain_id = Column(
        Integer, ForeignKey("core_tech_domain.tech_domain_id"), nullable=False, index=True
    )
    direction_desc = Column(Text, nullable=True)
    sort_order = Column(Integer, default=0)
    is_enabled = Column(Boolean, default=True, nullable=False)

    # Relationships
    tech_domain = relationship("TechDomain", back_populates="directions")
    talent_tags = relationship("TalentTechTag", back_populates="tech_direction")

    def __repr__(self) -> str:
        return f"<TechDirection(id={self.tech_direction_id}, name={self.direction_name})>"


class TalentTechTag(Base, TimestampMixin):
    """人才技术标签"""

    __tablename__ = "core_talent_tech_tag"
    __table_args__ = (
        UniqueConstraint("talent_id", "tech_direction_id", name="uq_talent_tech_direction"),
    )

    tag_id = Column(Integer, primary_key=True, index=True)
    talent_id = Column(Integer, ForeignKey("core_talent.talent_id"), nullable=False, index=True)
    tech_domain_id = Column(
        Integer, ForeignKey("core_tech_domain.tech_domain_id"), nullable=False, index=True
    )
    tech_direction_id = Column(
        Integer, ForeignKey("core_tech_direction.tech_direction_id"), nullable=False, index=True
    )

    tag_level = Column(String(20), default="primary", nullable=False)  # primary/secondary
    tag_source = Column(
        String(20), default="auto_mapping", nullable=False
    )  # auto_mapping/manual_adjustment/imported
    confirm_status = Column(
        String(20), default="auto_identified", nullable=False
    )  # confirmed/auto_identified/pending_confirm
    confidence_score = Column(Float, default=0.8)
    is_enabled = Column(Boolean, default=True, nullable=False)

    # Relationships
    talent = relationship("Talent", back_populates="tech_tags")
    tech_domain = relationship("TechDomain")
    tech_direction = relationship("TechDirection", back_populates="talent_tags")

    def __repr__(self) -> str:
        return f"<TalentTechTag(talent_id={self.talent_id}, direction_id={self.tech_direction_id})>"
