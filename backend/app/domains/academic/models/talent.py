"""
Talent model.
"""

from sqlalchemy import JSON, Boolean, Column, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.domains.shared.models.base import TimestampMixin
from app.domains.shared.models.enums import RoleType, VisibilityStatus


class Talent(Base, TimestampMixin):
    """Academic talent model."""

    __tablename__ = "core_talent"

    talent_id = Column(Integer, primary_key=True, index=True)

    # Link to standardized layer
    std_author_id = Column(
        Integer, ForeignKey("std_author.std_author_id"), nullable=True, index=True
    )

    # Source tracking
    source_type = Column(String(50), nullable=True)
    source_record_id = Column(String(100), nullable=True, index=True, unique=True)
    last_sync_batch_id = Column(Integer, nullable=True)

    # Basic info
    name = Column(String(255), nullable=False, index=True)
    name_en = Column(String(255), nullable=True)
    orcid = Column(String(50), nullable=True, index=True)

    # Affiliation (legacy field - kept for backward compatibility)
    school_id = Column(Integer, ForeignKey("core_school.school_id"), nullable=True, index=True)

    # Primary institutions (education and company)
    education_school_id = Column(
        Integer, ForeignKey("core_school.school_id"), nullable=True, index=True
    )
    company_school_id = Column(
        Integer, ForeignKey("core_school.school_id"), nullable=True, index=True
    )

    current_title = Column(String(255), nullable=True)

    # Role identification (quick filter field)
    role_type = Column(String(20), default=RoleType.UNKNOWN.value, nullable=False, index=True)
    role_confidence = Column(Float, default=0.0)

    # Research info
    # topic_tags: Cached field computed from TalentTechTag table
    # Format: ["AI", "Machine Learning", "Deep Learning"]
    # This field is updated when tech_tags relationship changes
    topic_tags = Column(JSON, default=[])
    # openalex_topics: Research topics from OpenAlex API (topics field)
    # Format: ["Machine Learning", "Computer Vision", "Natural Language Processing"]
    openalex_topics = Column(JSON, default=[])

    # Summary for display
    summary = Column(Text, nullable=True)

    # Statistics
    works_count = Column(Integer, default=0)
    cited_by_count = Column(Integer, default=0)
    h_index = Column(Integer, default=0)
    latest_active_year = Column(Integer, nullable=True)

    # Status
    visibility_status = Column(String(20), default=VisibilityStatus.ACTIVE.value, nullable=False)
    is_visible = Column(Boolean, default=True, nullable=False)

    # Reserved fields
    unified_person_id = Column(String(100), nullable=True)  # For future unified person profile
    department_name = Column(String(255), nullable=True)
    lab_name = Column(String(255), nullable=True)
    extra_data = Column(JSON, nullable=True)  # Flexible storage for additional info

    # Relationships
    school = relationship("School", back_populates="talents", foreign_keys=[school_id])
    education_school = relationship("School", foreign_keys=[education_school_id])
    company_school = relationship("School", foreign_keys=[company_school_id])
    role_profile = relationship("RoleProfile", back_populates="talent", uselist=False)
    selected_works = relationship("SelectedWork", back_populates="talent")
    tech_tags = relationship("TalentTechTag", back_populates="talent")
    std_author = relationship("StdAuthor", back_populates="talent")
    embedding = relationship("TalentEmbedding", back_populates="talent", uselist=False)

    def update_topic_tags_from_tech_tags(self) -> None:
        """
        Update topic_tags from the tech_tags relationship.

        This method should be called after modifying tech_tags to keep
        the cached topic_tags field in sync. The topic_tags field is a
        denormalized cache for quick filtering and display.
        """
        if self.tech_tags:
            # Get unique tech domain names from tech_tags
            domain_names = set()
            for tag in self.tech_tags:
                if tag.is_enabled and tag.tech_domain:
                    domain_names.add(tag.tech_domain.domain_name)  # type: ignore[union-attr]
            self.topic_tags = sorted(domain_names)  # type: ignore[assignment]
        else:
            self.topic_tags = []  # type: ignore[assignment]

    @property
    def primary_school_id(self) -> int | None:
        """Get primary school ID (education -> company -> legacy)."""
        return self.education_school_id or self.company_school_id or self.school_id  # type: ignore[return-value]

    @property
    def primary_school_name(self) -> str | None:
        """Get primary school name (education -> company -> legacy)."""
        if self.education_school:
            return self.education_school.school_name  # type: ignore[no-any-return, union-attr]
        if self.company_school:
            return self.company_school.school_name  # type: ignore[no-any-return, union-attr]
        if self.school:
            return self.school.school_name  # type: ignore[no-any-return, union-attr]
        return None

    def __repr__(self) -> str:
        return f"<Talent(talent_id={self.talent_id}, name={self.name}, role={self.role_type})>"


class RoleProfile(Base, TimestampMixin):
    """Detailed role identification for talent."""

    __tablename__ = "core_role_profile"

    profile_id = Column(Integer, primary_key=True, index=True)
    talent_id = Column(Integer, ForeignKey("core_talent.talent_id"), unique=True, nullable=False)

    # Role details
    role_type = Column(String(20), default=RoleType.UNKNOWN.value, nullable=False)
    role_confidence = Column(Float, default=0.0)
    role_reason = Column(Text, nullable=True)

    # Identification metadata
    identification_method = Column(String(50), nullable=True)  # e.g., 'heuristic', 'manual', 'ml'
    identified_at = Column(String(50), nullable=True)  # ISO datetime string

    # Extended role info
    position_title = Column(String(255), nullable=True)
    academic_age = Column(Integer, nullable=True)

    # Relationships
    talent = relationship("Talent", back_populates="role_profile")

    def __repr__(self) -> str:
        return f"<RoleProfile(talent_id={self.talent_id}, role={self.role_type})>"


class SelectedWork(Base, TimestampMixin):
    """Representative works for talent detail page."""

    __tablename__ = "core_selected_work"

    work_id = Column(Integer, primary_key=True, index=True)
    talent_id = Column(Integer, ForeignKey("core_talent.talent_id"), nullable=False, index=True)

    # Work info
    title = Column(String(500), nullable=False)
    publication_year = Column(Integer, nullable=True)
    venue_name = Column(String(255), nullable=True)
    citation_count = Column(Integer, default=0)

    # Source reference
    source_work_id = Column(String(100), nullable=True)
    doi = Column(String(100), nullable=True)

    # Display order
    display_order = Column(Integer, default=0)

    # Relationships
    talent = relationship("Talent", back_populates="selected_works")

    def __repr__(self) -> str:
        return f"<SelectedWork(work_id={self.work_id}, title={self.title[:30]}...)>"
