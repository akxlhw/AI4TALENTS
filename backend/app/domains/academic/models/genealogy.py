"""Genealogy models for academic talent influence and advisor-student relationships."""

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)

from app.core.database import Base
from app.domains.shared.models.base import TimestampMixin


class GenealogyEdge(Base, TimestampMixin):
    """Academic genealogy edge: inferred advisor-student / mentor-mentee / senior-junior relationships."""

    __tablename__ = "genealogy_edge"

    edge_id = Column(Integer, primary_key=True, autoincrement=True)
    from_talent_id = Column(
        Integer, ForeignKey("core_talent.talent_id"), nullable=False, index=True
    )
    to_talent_id = Column(Integer, ForeignKey("core_talent.talent_id"), nullable=False, index=True)
    relationship_type = Column(String(20), nullable=False, index=True)
    # advisor_student / mentor_mentee / senior_junior
    confidence_score = Column(Float, nullable=False, default=0.0)
    evidence_count = Column(Integer, nullable=False, default=0)
    shared_institution = Column(Boolean, nullable=False, default=False)
    first_year = Column(Integer, nullable=True)
    last_year = Column(Integer, nullable=True)
    source_work_ids = Column(JSON, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "from_talent_id", "to_talent_id", "relationship_type", name="uq_genealogy_pair"
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<GenealogyEdge({self.from_talent_id} -> {self.to_talent_id}, "
            f"type={self.relationship_type}, conf={self.confidence_score:.2f})>"
        )


class TalentInfluenceScore(Base, TimestampMixin):
    """Influence score for academic talents (composite + per-dimension)."""

    __tablename__ = "talent_influence_score"

    talent_id = Column(Integer, ForeignKey("core_talent.talent_id"), primary_key=True)
    h_index_score = Column(Float, nullable=False, default=0.0)
    citation_score = Column(Float, nullable=False, default=0.0)
    works_score = Column(Float, nullable=False, default=0.0)
    collaboration_score = Column(Float, nullable=False, default=0.0)
    bridge_score = Column(Float, nullable=False, default=0.0)
    composite_score = Column(Float, nullable=False, default=0.0)
    tier = Column(String(10), nullable=False, default="tier4")
    is_root = Column(Boolean, nullable=False, default=False)
    computed_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<TalentInfluenceScore(talent={self.talent_id}, score={self.composite_score:.1f}, tier={self.tier})>"
