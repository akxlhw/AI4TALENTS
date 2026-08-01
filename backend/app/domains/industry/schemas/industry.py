"""Industry domain schemas — DTOs for positions, talents, links and import."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# ============ Position ============


class IndustryPositionCreate(BaseModel):
    """Payload for creating a position."""

    title: str = Field(..., min_length=1, max_length=255)
    department: str | None = Field(default=None, max_length=255)
    tech_direction_codes: list[str] = Field(default_factory=list)
    level_min: int | None = None
    level_max: int | None = None
    jd_text: str | None = None
    jd_features: dict[str, Any] | None = None
    status: str = Field(default="open", max_length=20)


class IndustryPositionUpdate(BaseModel):
    """Payload for updating a position (all fields optional)."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    department: str | None = Field(default=None, max_length=255)
    tech_direction_codes: list[str] | None = None
    level_min: int | None = None
    level_max: int | None = None
    jd_text: str | None = None
    jd_features: dict[str, Any] | None = None
    status: str | None = Field(default=None, max_length=20)


class IndustryPositionResponse(BaseModel):
    """Position row plus candidate aggregates (F-POS-04)."""

    position_id: int
    title: str
    department: str | None = None
    tech_direction_codes: list[str] = Field(default_factory=list)
    level_min: int | None = None
    level_max: int | None = None
    jd_text: str | None = None
    jd_features: dict[str, Any] | None = None
    status: str
    created_by: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    candidate_count: int = 0
    avg_match_score: float | None = None


# ============ Talent ============


class PositionHit(BaseModel):
    """One position a talent matched (summary granularity)."""

    position_id: int
    title: str
    match_score: float | None = None
    status: str = "new"
    touched: bool = False


class IndustryTalentSummary(BaseModel):
    """Talent card row: basic info + best score + matched positions."""

    talent_id: int
    name: str
    current_org: str | None = None
    current_title: str | None = None
    degree: str | None = None
    years_of_exp: str | None = None
    years_of_exp_num: float | None = None
    location: str | None = None
    photo_url: str | None = None
    source: str | None = None
    best_match_score: float | None = None
    positions: list[PositionHit] = Field(default_factory=list)


class IndustryPositionMatchDetail(PositionHit):
    """Full match record of a talent under one position."""

    score_school: float | None = None
    score_company: float | None = None
    score_direction: float | None = None
    match_tags: list[str] = Field(default_factory=list)
    match_reason: str | None = None
    notes: str | None = None
    batch: str | None = None
    source_platform: str | None = None
    updated_at: datetime | None = None


class IndustryTalentDetail(IndustryTalentSummary):
    """Full talent profile plus per-position match comparison."""

    experiences: list[dict[str, Any]] = Field(default_factory=list)
    expect: str | None = None
    profile_url: str | None = None
    unified_person_id: str | None = None
    is_visible: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None
    positions: list[IndustryPositionMatchDetail] = Field(default_factory=list)  # type: ignore[assignment]


class CandidateStatusPatch(BaseModel):
    """PATCH body for recruiting state on a position-talent link."""

    status: str | None = Field(default=None, max_length=20)
    touched: bool | None = None
    notes: str | None = None


# ============ Import ============


class SkipReason(BaseModel):
    """Reason a JSONL line was skipped during import."""

    line: int
    reason: str


class IndustryImportReport(BaseModel):
    """Report returned by the import endpoint."""

    total_lines: int
    total_parsed: int
    talents_inserted: int = 0
    talents_updated: int = 0
    links_inserted: int = 0
    links_updated: int = 0
    skipped: int = 0
    skip_reasons: list[SkipReason] = Field(default_factory=list)
    warnings: int = 0  # rows missing current_org (weak dedup discrimination)
