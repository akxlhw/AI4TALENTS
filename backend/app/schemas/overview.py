"""
Overview API schemas.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class OverviewStats(BaseModel):
    """Overview statistics for homepage."""

    school_count: int = Field(description="Total number of schools")
    professor_count: int = Field(description="Total number of professors")
    student_count: int = Field(description="Total number of students")
    talent_count: int = Field(description="Total number of talents")
    country_count: int = Field(default=0, description="Total number of countries")
    tech_domain_count: int = Field(default=0, description="Total number of tech domains")
    tech_direction_count: int = Field(default=0, description="Total number of tech directions")


class OverviewResponse(BaseModel):
    """Overview API response."""

    stats: OverviewStats
    version: str = Field(description="Statistics version")
    generated_at: str = Field(description="Statistics generation timestamp")


class CountrySummary(BaseModel):
    """Country summary for list response."""

    country_code: str = Field(description="ISO 3166-1 alpha-2 country code")
    country_name_cn: str
    country_name_en: str | None = None
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
    school_alias: str | None = None
    country_code: str | None = None
    country_name: str | None = None
    professor_count: int = Field(default=0)
    student_count: int = Field(default=0)
    homepage_url: str | None = None
    is_top_school: bool = Field(default=False, description="是否为Top院校")


class SchoolDetail(BaseModel):
    """School detail response."""

    school_id: int
    school_name: str
    school_alias: str | None = None
    country_code: str | None = None
    country_name: str | None = None
    school_intro: str | None = None
    homepage_url: str | None = None
    professor_count: int = Field(default=0)
    student_count: int = Field(default=0)
    talent_count: int = Field(default=0)
    graduate_count: int = Field(default=0)
    unknown_count: int = Field(default=0)
    is_top_school: bool = Field(default=False, description="是否为Top院校")


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
    name_en: str | None = None
    orcid: str | None = None
    role_type: str
    role_confidence: float = 0.0
    school_id: int | None = None
    school_name: str | None = None
    current_title: str | None = None
    works_count: int = 0
    cited_by_count: int = 0
    h_index: int = 0
    topic_tags: list[str] = Field(default_factory=list)
    openalex_topics: list[str] = Field(default_factory=list, description="OpenAlex研究主题")


class TechTagItem(BaseModel):
    """Tech tag for talent."""

    tech_domain_id: int
    tech_domain_name: str
    tech_direction_id: int | None = None
    tech_direction_name: str | None = None


class TalentDetail(BaseModel):
    """Talent detail response."""

    talent_id: int
    name: str
    name_en: str | None = None
    orcid: str | None = None
    role_type: str
    role_confidence: float = 0.0
    school_id: int | None = None
    school_name: str | None = None
    current_title: str | None = None
    works_count: int = 0
    cited_by_count: int = 0
    h_index: int = 0
    latest_active_year: int | None = None
    topic_tags: list[str] = Field(default_factory=list)
    openalex_topics: list[str] = Field(default_factory=list, description="OpenAlex研究主题")
    tech_tags: list[TechTagItem] = Field(default_factory=list, description="技术领域标签")
    summary: str | None = None
    department_name: str | None = None
    lab_name: str | None = None

    # Role profile details
    role_reason: str | None = None
    academic_age: int | None = None

    # Representative works
    selected_works: list[SelectedWorkResponse] = Field(default_factory=list)


class SelectedWorkResponse(BaseModel):
    """Selected work for talent detail."""

    work_id: int
    title: str
    publication_year: int | None = None
    venue_name: str | None = None
    citation_count: int = 0
    doi: str | None = None


class TalentFilterParams(BaseModel):
    """Talent filter parameters."""

    school_id: int | None = None
    country_code: str | None = None
    role_type: str | None = None
    min_works: int | None = None
    min_citations: int | None = None
    keyword: str | None = None


class SearchTalentResult(BaseModel):
    """Search result for talent."""

    talent_id: int
    name: str
    name_en: str | None = None
    role_type: str
    school_name: str | None = None
    current_title: str | None = None
    works_count: int = 0
    cited_by_count: int = 0
    h_index: int = 0
    topic_tags: list[str] = Field(default_factory=list)
    openalex_topics: list[str] = Field(default_factory=list, description="OpenAlex研究主题")
    highlight: str | None = None


class SearchResponse(BaseModel):
    """Search API response."""

    items: list[SearchTalentResult]
    total: int
    query: str
    page: int
    page_size: int


# Resolve forward reference for TalentDetail
TalentDetail.model_rebuild()
