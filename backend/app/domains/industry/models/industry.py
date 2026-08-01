"""Industry domain models — positions, globally-unique talents, position-talent links.

Independent industry_* table family per the cross-domain isolation rule:
this domain must NOT reuse academic/open_source/lab tables.
Design: docs/v5.0.0/02-技术设计.md §3
"""

from __future__ import annotations

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from app.core.database import Base
from app.domains.shared.models.base import TimestampMixin


class IndustryPosition(Base, TimestampMixin):
    """Recruiting position (first-class entity, lifecycle via status)."""

    __tablename__ = "industry_position"

    position_id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False, index=True)
    department = Column(String(255), nullable=True)
    tech_direction_codes = Column(JSON, default=list)  # codes of core_tech_direction
    level_min = Column(Integer, nullable=True)  # Huawei-style level lower bound (e.g. 19)
    level_max = Column(Integer, nullable=True)  # level upper bound (e.g. 20)
    jd_text = Column(Text, nullable=True)
    jd_features = Column(JSON, nullable=True)  # skills/experience/target companies
    status = Column(String(20), nullable=False, default="open", index=True)
    created_by = Column(Integer, ForeignKey("iam_user_account.user_id"), nullable=True)

    def __repr__(self) -> str:
        return f"<IndustryPosition(position_id={self.position_id}, title={self.title})>"

    def to_dict(self) -> dict:
        """Return a dict suitable for IndustryPositionResponse conversion."""
        return {
            "position_id": self.position_id,
            "title": self.title,
            "department": self.department,
            "tech_direction_codes": self.tech_direction_codes or [],
            "level_min": self.level_min,
            "level_max": self.level_max,
            "jd_text": self.jd_text,
            "jd_features": self.jd_features,
            "status": self.status,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class IndustryTalent(Base, TimestampMixin):
    """Industry candidate, globally unique by dedup_hash (name+org+title)."""

    __tablename__ = "industry_talent"

    talent_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    current_org = Column(String(255), nullable=True, index=True)
    current_title = Column(String(255), nullable=True)
    degree = Column(String(50), nullable=True)
    years_of_exp = Column(String(20), nullable=True)  # raw text for display
    years_of_exp_num = Column(Float, nullable=True)  # parsed number for filter/sort
    experiences = Column(JSON, default=list)  # [{range/year, org, title}]
    expect = Column(String(500), nullable=True)  # job intention
    location = Column(String(255), nullable=True)
    profile_url = Column(String(1000), nullable=True)  # LinkedIn /in/ or maimai page
    photo_url = Column(String(1000), nullable=True)
    source = Column(String(50), nullable=True)  # maimai / linkedin

    dedup_hash = Column(String(64), nullable=False, unique=True, index=True)
    unified_person_id = Column(
        String(100), nullable=True, index=True
    )  # reserved for cross-library identity
    is_visible = Column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<IndustryTalent(talent_id={self.talent_id}, name={self.name})>"

    def to_summary_dict(self) -> dict:
        """Return a dict suitable for IndustryTalentSummary DTO conversion."""
        return {
            "talent_id": self.talent_id,
            "name": self.name,
            "current_org": self.current_org,
            "current_title": self.current_title,
            "degree": self.degree,
            "years_of_exp": self.years_of_exp,
            "years_of_exp_num": self.years_of_exp_num,
            "location": self.location,
            "photo_url": self.photo_url,
            "source": self.source,
        }

    def to_detail_dict(self) -> dict:
        """Return a dict suitable for IndustryTalentDetail DTO conversion."""
        data = self.to_summary_dict()
        data.update(
            {
                "experiences": self.experiences or [],
                "expect": self.expect,
                "profile_url": self.profile_url,
                "unified_person_id": self.unified_person_id,
                "is_visible": self.is_visible,
                "created_at": self.created_at,
                "updated_at": self.updated_at,
            }
        )
        return data


class IndustryPositionTalent(Base, TimestampMixin):
    """Position-talent link with per-position match scores and recruiting state."""

    __tablename__ = "industry_position_talent"
    __table_args__ = (
        UniqueConstraint("position_id", "talent_id", name="uq_industry_position_talent"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    position_id = Column(
        Integer, ForeignKey("industry_position.position_id"), nullable=False, index=True
    )
    talent_id = Column(Integer, ForeignKey("industry_talent.talent_id"), nullable=False, index=True)

    match_score = Column(Float, nullable=True)  # overall 0-100
    score_school = Column(Float, nullable=True)  # school dimension 0-100
    score_company = Column(Float, nullable=True)  # company dimension 0-100
    score_direction = Column(Float, nullable=True)  # tech direction dimension 0-100
    match_tags = Column(JSON, default=list)
    match_reason = Column(Text, nullable=True)

    touched = Column(Boolean, default=False, nullable=False)
    status = Column(String(20), default="new", nullable=False, index=True)
    notes = Column(Text, nullable=True)

    batch = Column(String(50), nullable=True)  # import batch identifier
    source_platform = Column(String(50), nullable=True)  # maimai / linkedin

    def __repr__(self) -> str:
        return (
            f"<IndustryPositionTalent(position_id={self.position_id}, "
            f"talent_id={self.talent_id}, score={self.match_score})>"
        )

    def to_match_dict(self, title: str) -> dict:
        """Return a dict suitable for IndustryPositionMatchDetail DTO conversion."""
        return {
            "position_id": self.position_id,
            "title": title,
            "match_score": self.match_score,
            "status": self.status,
            "touched": self.touched,
            "score_school": self.score_school,
            "score_company": self.score_company,
            "score_direction": self.score_direction,
            "match_tags": self.match_tags or [],
            "match_reason": self.match_reason,
            "notes": self.notes,
            "batch": self.batch,
            "source_platform": self.source_platform,
            "updated_at": self.updated_at,
        }
