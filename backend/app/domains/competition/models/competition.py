"""Competition domain models — contest series, contests, talents, teams, results.

Independent comp_* table family per the cross-domain isolation rule:
this domain must NOT reuse academic/open_source/lab tables.
Design: docs/competition-v1.0/01_架构与数据模型.md
"""

from __future__ import annotations

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)

from app.core.database import Base
from app.domains.shared.models.base import TimestampMixin


class CompSeries(Base, TimestampMixin):
    """Contest series/brand (codeforces, icpc, ioi, imo, ipho, kaggle, ...)."""

    __tablename__ = "comp_series"

    series_id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    name_en = Column(String(255), nullable=True)
    homepage = Column(String(500), nullable=True)
    description = Column(String(2000), nullable=True)
    logo_url = Column(String(1000), nullable=True)
    is_enabled = Column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<CompSeries(code={self.code}, name={self.name})>"


class CompContest(Base, TimestampMixin):
    """A single contest instance (e.g. Codeforces Round 951 Div. 1)."""

    __tablename__ = "comp_contest"
    __table_args__ = (
        UniqueConstraint("source_code", "external_id", name="uq_comp_contest_source_external"),
    )

    contest_id = Column(Integer, primary_key=True, autoincrement=True)
    series_id = Column(Integer, ForeignKey("comp_series.series_id"), nullable=False, index=True)
    source_code = Column(String(50), nullable=False, index=True)
    external_id = Column(String(100), nullable=False)
    name = Column(String(500), nullable=False)
    start_time = Column(DateTime, nullable=True, index=True)
    duration_seconds = Column(Integer, nullable=True)
    season = Column(String(50), nullable=True, index=True)
    status = Column(String(20), nullable=False, default="finished")
    source_url = Column(String(1000), nullable=True)
    raw_meta = Column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<CompContest({self.source_code}:{self.external_id} {self.name})>"


class CompTalent(Base, TimestampMixin):
    """A competitive-contest participant (identity = source_code + handle)."""

    __tablename__ = "comp_talent"
    __table_args__ = (
        UniqueConstraint("source_code", "handle_lower", name="uq_comp_talent_source_handle"),
    )

    talent_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    handle = Column(String(255), nullable=False, index=True)
    handle_lower = Column(String(255), nullable=False, index=True)
    source_code = Column(String(50), nullable=False, index=True)

    # Profile (best-effort, merged non-null on upsert)
    real_name = Column(String(255), nullable=True)
    school = Column(String(255), nullable=True, index=True)
    country_code = Column(String(10), nullable=True, index=True)
    avatar_url = Column(String(1000), nullable=True)
    profile_url = Column(String(1000), nullable=True)

    # Aggregates (recomputed on import)
    current_rating = Column(Integer, nullable=True, index=True)
    max_rating = Column(Integer, nullable=True)
    rank_title = Column(String(50), nullable=True, index=True)
    global_rank = Column(Integer, nullable=True)
    contests_count = Column(Integer, nullable=False, default=0)
    medals_gold = Column(Integer, nullable=False, default=0)
    medals_silver = Column(Integer, nullable=False, default=0)
    medals_bronze = Column(Integer, nullable=False, default=0)
    specialties = Column(JSON, nullable=True)
    last_contest_at = Column(DateTime, nullable=True, index=True)

    # Identity / provenance
    dedup_hash = Column(String(64), unique=True, nullable=False, index=True)
    unified_person_id = Column(String(100), nullable=True, index=True)
    is_visible = Column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<CompTalent({self.source_code}:{self.handle})>"


class CompTeam(Base, TimestampMixin):
    """A team for team-based contests (ICPC, CTF, RoboCup, supercomputing)."""

    __tablename__ = "comp_team"
    __table_args__ = (
        UniqueConstraint("source_code", "name_lower", "school", name="uq_comp_team_identity"),
    )

    team_id = Column(Integer, primary_key=True, autoincrement=True)
    source_code = Column(String(50), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    name_lower = Column(String(255), nullable=False, index=True)
    school = Column(String(255), nullable=True, index=True)
    country_code = Column(String(10), nullable=True, index=True)
    logo_url = Column(String(1000), nullable=True)
    dedup_hash = Column(String(64), unique=True, nullable=False, index=True)

    def __repr__(self) -> str:
        return f"<CompTeam({self.source_code}:{self.name})>"


class CompResult(Base, TimestampMixin):
    """A result of a talent or a team in one contest."""

    __tablename__ = "comp_result"
    __table_args__ = (
        UniqueConstraint("talent_id", "contest_id", name="uq_comp_result_talent_contest"),
        # Team results are unique per team per contest — but ONLY for team-owned
        # rows (talent_id IS NULL). Personal results may also carry team_id
        # (members of the same team), so a plain (team_id, contest_id) unique
        # constraint would wrongly reject them.
        Index(
            "uq_comp_result_team_contest",
            "team_id",
            "contest_id",
            unique=True,
            postgresql_where=text("talent_id IS NULL"),
        ),
        CheckConstraint(
            "talent_id IS NOT NULL OR team_id IS NOT NULL",
            name="ck_comp_result_has_owner",
        ),
    )

    result_id = Column(Integer, primary_key=True, autoincrement=True)
    talent_id = Column(Integer, ForeignKey("comp_talent.talent_id"), nullable=True, index=True)
    team_id = Column(Integer, ForeignKey("comp_team.team_id"), nullable=True, index=True)
    contest_id = Column(Integer, ForeignKey("comp_contest.contest_id"), nullable=False, index=True)

    rank = Column(Integer, nullable=True)
    score = Column(Float, nullable=True)
    rating_before = Column(Integer, nullable=True)
    rating_after = Column(Integer, nullable=True)
    award = Column(String(20), nullable=True, index=True)  # gold/silver/bronze/hm/none
    team_name = Column(String(255), nullable=True)  # denormalized display name
    team_members = Column(JSON, nullable=True)  # [{handle?, real_name, role?}]
    source_url = Column(String(1000), nullable=True)
    raw_meta = Column(JSON, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<CompResult(talent={self.talent_id}, team={self.team_id}, contest={self.contest_id})>"
        )
