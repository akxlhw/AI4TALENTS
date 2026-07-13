"""Lab talent model — AI lab researchers imported from crawler JSONL."""

from __future__ import annotations

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text

from app.core.database import Base
from app.domains.shared.models.base import TimestampMixin


class LabTalent(Base, TimestampMixin):
    """AI lab talent imported from ai-lab-talent-crawler JSONL output.

    Independent table (not core_talent) — per architecture isolation rules,
    the lab domain cannot import the academic domain's core_talent model.
    """

    __tablename__ = "lab_talent"

    talent_id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Basic info
    name = Column(String(255), nullable=False, index=True)

    # Role (coarse) + academic level (fine grain for students)
    role_section = Column(String(100), nullable=False)
    role_type = Column(String(20), nullable=False, index=True, default="unknown")
    academic_level = Column(
        String(20), nullable=True, index=True
    )  # phd/master/bachelor (students only)
    current_title = Column(String(255), nullable=True)  # role_raw from bio detail page

    # Contact & affiliation
    homepage = Column(String(500), nullable=True)
    email = Column(String(255), nullable=True)
    photo_url = Column(String(1000), nullable=True)  # person photo URL
    department = Column(String(255), nullable=True)
    research_areas = Column(JSON, default=list)

    # Cohort
    cohort_year = Column(Integer, nullable=True, index=True)
    cohort_source = Column(String(255), nullable=True)

    # Lab affiliation
    lab_name = Column(String(255), nullable=False, index=True)  # sub-lab (e.g. Stanford NLP Group)
    parent_lab = Column(
        String(255), nullable=False, index=True
    )  # top-level lab (e.g. Stanford AI Lab)
    lab_logo_url = Column(String(1000), nullable=True)  # copied from lab metadata header

    # Provenance
    source_url = Column(String(1000), nullable=True)
    source_detail_url = Column(String(1000), nullable=True)
    collected_at = Column(DateTime, nullable=True)

    # Dedup / identity
    dedup_hash = Column(String(64), nullable=False, unique=True, index=True)
    unified_person_id = Column(
        String(100), nullable=True, index=True
    )  # reserved for future cross-library identity

    # Homepage preview cache (cleaned HTML, fetched by HomepagePreviewService)
    homepage_cache = Column(Text, nullable=True)
    homepage_cached_at = Column(DateTime, nullable=True)

    # Visibility
    is_visible = Column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<LabTalent(talent_id={self.talent_id}, name={self.name}, lab={self.parent_lab})>"

    def to_summary_dict(self) -> dict:
        """Return a dict suitable for LabTalentSummary DTO conversion."""
        return {
            "talent_id": self.talent_id,
            "name": self.name,
            "role_section": self.role_section,
            "role_type": self.role_type,
            "academic_level": self.academic_level,
            "current_title": self.current_title,
            "homepage": self.homepage,
            "department": self.department,
            "research_areas": self.research_areas or [],
            "cohort_year": self.cohort_year,
            "lab_name": self.lab_name,
            "parent_lab": self.parent_lab,
            "lab_logo_url": self.lab_logo_url,
            "photo_url": self.photo_url,
            "is_visible": self.is_visible,
        }

    def to_detail_dict(self) -> dict:
        """Return a dict suitable for LabTalentDetail DTO conversion."""
        data = self.to_summary_dict()
        data.update(
            {
                "email": self.email,
                "photo_url": self.photo_url,
                "cohort_source": self.cohort_source,
                "source_url": self.source_url,
                "source_detail_url": self.source_detail_url,
                "collected_at": self.collected_at,
            }
        )
        return data


class LabInfo(Base, TimestampMixin):
    """Lab-level metadata (one row per parent lab).

    Populated from the ``type: lab`` header line in crawler JSONL output.
    Stores description, research focus, homepage, logo etc. for display
    on the search page context banner.
    """

    __tablename__ = "lab_info"

    lab_info_id = Column(Integer, primary_key=True, autoincrement=True)
    parent_lab = Column(String(255), nullable=False, unique=True, index=True)
    lab_slug = Column(String(100), nullable=True, index=True)
    description = Column(String(2000), nullable=True)
    research_focus = Column(String(1000), nullable=True)
    research_directions = Column(JSON, default=list)  # current_research_directions from crawler
    homepage = Column(String(500), nullable=True)
    logo_url = Column(String(1000), nullable=True)

    def __repr__(self) -> str:
        return f"<LabInfo(parent_lab={self.parent_lab})>"
