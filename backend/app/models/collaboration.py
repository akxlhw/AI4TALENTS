"""
Collaboration model for co-author relationships.
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class Collaboration(Base, TimestampMixin):
    """Co-author collaboration relationship between two talents."""

    __tablename__ = "core_collaboration"
    __table_args__ = (
        UniqueConstraint('talent_id_1', 'talent_id_2', name='uq_collaboration_pair'),
    )

    collaboration_id = Column(Integer, primary_key=True, index=True)

    # Two talents in the collaboration (ordered by talent_id)
    talent_id_1 = Column(Integer, ForeignKey("core_talent.talent_id"), nullable=False, index=True)
    talent_id_2 = Column(Integer, ForeignKey("core_talent.talent_id"), nullable=False, index=True)

    # Collaboration statistics
    collaboration_count = Column(Integer, default=1, nullable=False)  # Number of papers together
    first_collaboration_year = Column(Integer, nullable=True)
    last_collaboration_year = Column(Integer, nullable=True)

    # Source tracking
    source_batch_id = Column(Integer, nullable=True)

    def __repr__(self):
        return f"<Collaboration({self.talent_id_1} <-> {self.talent_id_2}, count={self.collaboration_count})>"


class WorkAuthor(Base, TimestampMixin):
    """Authors of a work, for collaboration extraction."""

    __tablename__ = "core_work_author"

    work_author_id = Column(Integer, primary_key=True, index=True)

    # Work reference (use OpenAlex work ID as string)
    source_work_id = Column(String(100), nullable=False, index=True)
    work_title = Column(String(500), nullable=True)
    publication_year = Column(Integer, nullable=True)

    # Author reference
    talent_id = Column(Integer, ForeignKey("core_talent.talent_id"), nullable=True, index=True)
    author_position = Column(Integer, nullable=True)  # Author order position
    author_name = Column(String(255), nullable=True)  # Original author name from OpenAlex

    def __repr__(self):
        return f"<WorkAuthor(work={self.source_work_id}, author={self.author_name})>"
