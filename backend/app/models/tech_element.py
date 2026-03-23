"""
Technology Element and Direction models.
技术要素与技术方向模型
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, Float, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class TechElement(Base, TimestampMixin):
    """技术要素"""

    __tablename__ = "core_tech_element"

    tech_element_id = Column(Integer, primary_key=True, index=True)
    element_code = Column(String(50), unique=True, nullable=False)
    element_name = Column(String(100), nullable=False)
    element_name_en = Column(String(100), nullable=True)
    element_desc = Column(Text, nullable=True)
    sort_order = Column(Integer, default=0)
    is_enabled = Column(Boolean, default=True, nullable=False)

    # Relationships
    directions = relationship("TechDirection", back_populates="tech_element")

    def __repr__(self):
        return f"<TechElement(id={self.tech_element_id}, name={self.element_name})>"


class TechDirection(Base, TimestampMixin):
    """技术方向"""

    __tablename__ = "core_tech_direction"

    tech_direction_id = Column(Integer, primary_key=True, index=True)
    direction_code = Column(String(50), unique=True, nullable=False)
    direction_name = Column(String(100), nullable=False)
    direction_name_en = Column(String(100), nullable=True)
    tech_element_id = Column(Integer, ForeignKey("core_tech_element.tech_element_id"), nullable=False, index=True)
    direction_desc = Column(Text, nullable=True)
    sort_order = Column(Integer, default=0)
    is_enabled = Column(Boolean, default=True, nullable=False)

    # Relationships
    tech_element = relationship("TechElement", back_populates="directions")
    talent_tags = relationship("TalentTechTag", back_populates="tech_direction")

    def __repr__(self):
        return f"<TechDirection(id={self.tech_direction_id}, name={self.direction_name})>"


class TalentTechTag(Base, TimestampMixin):
    """人才技术标签"""

    __tablename__ = "core_talent_tech_tag"
    __table_args__ = (
        UniqueConstraint('talent_id', 'tech_direction_id', name='uq_talent_tech_direction'),
    )

    tag_id = Column(Integer, primary_key=True, index=True)
    talent_id = Column(Integer, ForeignKey("core_talent.talent_id"), nullable=False, index=True)
    tech_element_id = Column(Integer, ForeignKey("core_tech_element.tech_element_id"), nullable=False, index=True)
    tech_direction_id = Column(Integer, ForeignKey("core_tech_direction.tech_direction_id"), nullable=False, index=True)

    tag_level = Column(String(20), default="primary", nullable=False)  # primary/secondary
    tag_source = Column(String(20), default="auto_mapping", nullable=False)  # auto_mapping/manual_adjustment/imported
    confirm_status = Column(String(20), default="auto_identified", nullable=False)  # confirmed/auto_identified/pending_confirm
    confidence_score = Column(Float, default=0.8)
    is_enabled = Column(Boolean, default=True, nullable=False)

    # Relationships
    talent = relationship("Talent", back_populates="tech_tags")
    tech_element = relationship("TechElement")
    tech_direction = relationship("TechDirection", back_populates="talent_tags")

    def __repr__(self):
        return f"<TalentTechTag(talent_id={self.talent_id}, direction_id={self.tech_direction_id})>"
