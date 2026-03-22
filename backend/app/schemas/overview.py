"""
Overview API schemas.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class OverviewStats(BaseModel):
    """Overview statistics for homepage."""

    school_count: int = Field(description="Total number of schools")
    professor_count: int = Field(description="Total number of professors")
    student_count: int = Field(description="Total number of students")
    talent_count: int = Field(description="Total number of talents")


class OverviewResponse(BaseModel):
    """Overview API response."""

    stats: OverviewStats
    version: str = Field(description="Statistics version")
    generated_at: str = Field(description="Statistics generation timestamp")


class CountrySummary(BaseModel):
    """Country summary for list response."""

    country_id: int
    country_code: str
    country_name_cn: str
    country_name_en: Optional[str] = None
    school_count: int = Field(default=0, description="Number of schools in this country")
    professor_count: int = Field(default=0, description="Number of professors in this country")


class CountryListResponse(BaseModel):
    """Countries list response."""

    items: list[CountrySummary]
    total: int


class SchoolSummary(BaseModel):
    """School summary for list response."""

    school_id: int
    school_name: str
    school_alias: Optional[str] = None
    country_id: int
    country_name: Optional[str] = None
    country_code: Optional[str] = None
    professor_count: int = Field(default=0)
    student_count: int = Field(default=0)
    homepage_url: Optional[str] = None


class SchoolDetail(BaseModel):
    """School detail response."""

    school_id: int
    school_name: str
    school_alias: Optional[str] = None
    country_id: int
    country_name: Optional[str] = None
    country_code: Optional[str] = None
    school_intro: Optional[str] = None
    homepage_url: Optional[str] = None
    professor_count: int = Field(default=0)
    student_count: int = Field(default=0)
    talent_count: int = Field(default=0)
    graduate_count: int = Field(default=0)
    unknown_count: int = Field(default=0)


class SchoolStats(BaseModel):
    """School statistics."""

    professor_count: int = 0
    student_count: int = 0
    talent_count: int = 0
    graduate_count: int = 0
    unknown_count: int = 0


class TalentSummary(BaseModel):
    """Talent summary for list response."""

    talent_id: int
    name: str
    name_en: Optional[str] = None
    orcid: Optional[str] = None
    role_type: str
    role_confidence: float = 0.0
    school_id: Optional[int] = None
    school_name: Optional[str] = None
    current_title: Optional[str] = None
    works_count: int = 0
    cited_by_count: int = 0
    h_index: int = 0
    topic_tags: list[str] = Field(default_factory=list)


class TalentDetail(BaseModel):
    """Talent detail response."""

    talent_id: int
    name: str
    name_en: Optional[str] = None
    orcid: Optional[str] = None
    role_type: str
    role_confidence: float = 0.0
    school_id: Optional[int] = None
    school_name: Optional[str] = None
    current_title: Optional[str] = None
    works_count: int = 0
    cited_by_count: int = 0
    h_index: int = 0
    latest_active_year: Optional[int] = None
    topic_tags: list[str] = Field(default_factory=list)
    research_interests: Optional[str] = None
    summary: Optional[str] = None
    department_name: Optional[str] = None
    lab_name: Optional[str] = None

    # Role profile details
    role_reason: Optional[str] = None
    academic_age: Optional[int] = None

    # Representative works
    selected_works: list["SelectedWorkResponse"] = Field(default_factory=list)


class SelectedWorkResponse(BaseModel):
    """Selected work for talent detail."""

    work_id: int
    title: str
    publication_year: Optional[int] = None
    venue_name: Optional[str] = None
    citation_count: int = 0
    doi: Optional[str] = None


class TalentFilterParams(BaseModel):
    """Talent filter parameters."""

    school_id: Optional[int] = None
    country_id: Optional[int] = None
    role_type: Optional[str] = None
    min_works: Optional[int] = None
    min_citations: Optional[int] = None
    keyword: Optional[str] = None


class SearchTalentResult(BaseModel):
    """Search result for talent."""

    talent_id: int
    name: str
    name_en: Optional[str] = None
    role_type: str
    school_name: Optional[str] = None
    current_title: Optional[str] = None
    works_count: int = 0
    cited_by_count: int = 0
    h_index: int = 0
    topic_tags: list[str] = Field(default_factory=list)
    highlight: Optional[str] = None


class SearchResponse(BaseModel):
    """Search API response."""

    items: list[SearchTalentResult]
    total: int
    query: str
    page: int
    page_size: int


# Resolve forward reference for TalentDetail
TalentDetail.model_rebuild()
