"""Pydantic schemas for lab talent API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class LabTalentSummary(BaseModel):
    """List item — lightweight talent info for search results."""

    talent_id: int
    name: str
    role_section: str
    role_type: str
    academic_level: str | None = None
    current_title: str | None = None
    homepage: str | None = None
    email: str | None = None
    photo_url: str | None = None
    department: str | None = None
    research_areas: list[str] = Field(default_factory=list)
    cohort_year: int | None = None
    lab_name: str
    parent_lab: str
    lab_logo_url: str | None = None

    class Config:
        from_attributes = True


class LabTalentDetail(LabTalentSummary):
    """Detail — full talent info for detail page."""

    cohort_source: str | None = None
    source_url: str | None = None
    source_detail_url: str | None = None
    collected_at: datetime | None = None


class LabWithTalents(BaseModel):
    """A parent lab with a preview of its talents."""

    name: str
    count: int
    logo_url: str | None = None
    talents: list[LabTalentSummary] = Field(default_factory=list)
    role_distribution: dict[str, int] = Field(default_factory=dict)


class LabProfileResponse(BaseModel):
    """Lab profile with metadata and aggregated stats for the search banner."""

    parent_lab: str
    description: str | None = None
    research_focus: str | None = None
    research_directions: list[str] = Field(default_factory=list)
    homepage: str | None = None
    logo_url: str | None = None
    total_talents: int = 0
    role_distribution: dict[str, int] = Field(default_factory=dict)
    sub_labs: list[str] = Field(default_factory=list)


class LabStatsResponse(BaseModel):
    """Overview statistics for the lab talent library."""

    total_talents: int
    total_parent_labs: int
    total_sub_labs: int
    parent_lab_distribution: list[dict[str, Any]] = Field(default_factory=list)
    role_distribution: list[dict[str, Any]] = Field(default_factory=list)
    academic_level_distribution: list[dict[str, Any]] = Field(default_factory=list)
    top_labs: list[dict[str, Any]] = Field(default_factory=list)


class SkipReason(BaseModel):
    """Reason a JSONL line was skipped during import."""

    line: int
    reason: str


class LabImportReport(BaseModel):
    """Report returned by the import endpoint."""

    parent_lab: str
    total_lines: int
    total_parsed: int
    inserted: int
    skipped: int
    skip_reasons: list[SkipReason] = Field(default_factory=list)
