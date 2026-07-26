"""Pydantic schemas for lab talent API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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

    model_config = ConfigDict(from_attributes=True)


class LabTalentDetail(LabTalentSummary):
    """Detail — full talent info for detail page."""

    advisor: str | None = None
    co_advisor: str | None = None
    cohort_source: str | None = None
    source_url: str | None = None
    source_detail_url: str | None = None
    social_links: dict[str, str] = Field(default_factory=dict)
    collected_at: datetime | None = None


class LabWithTalents(BaseModel):
    """A parent lab with a preview of its talents."""

    name: str
    count: int
    logo_url: str | None = None
    description: str | None = None
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


class AdvisorStudentItem(BaseModel):
    """A student supervised by the current talent."""

    talent_id: int
    name: str
    role_type: str
    academic_level: str | None = None
    cohort_year: int | None = None
    parent_lab: str


class MentorshipResponse(BaseModel):
    """Mentorship data for the talent detail page."""

    advisor: str | None = None
    co_advisor: str | None = None
    advisor_talent_id: int | None = None  # link if advisor is also in DB
    co_advisor_talent_id: int | None = None
    students: list[AdvisorStudentItem] = Field(default_factory=list)


class AdvisorNetworkNode(BaseModel):
    """A node in the advisor-student network graph."""

    name: str
    talent_id: int | None = None
    role_type: str
    is_student: bool


class AdvisorNetworkEdge(BaseModel):
    """An edge (advisor→student) in the network graph."""

    source: str
    target: str
    type: str  # advisor / co_advisor


class AdvisorNetworkResponse(BaseModel):
    """Advisor-student network for ECharts force-directed graph."""

    nodes: list[AdvisorNetworkNode] = Field(default_factory=list)
    edges: list[AdvisorNetworkEdge] = Field(default_factory=list)


class HomepagePreviewResponse(BaseModel):
    """Cleaned personal homepage HTML for inline preview."""

    html: str
    base_url: str
    title: str = ""
    status: str  # ok / fetch_error / http_XXX / no_homepage
