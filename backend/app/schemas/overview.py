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

    stats: OverviewStats = Field(description="Statistics data")
    version: str = Field(description="Statistics version")
    generated_at: str = Field(description="Statistics generation timestamp")


class CountrySummary(BaseModel):
    """Country summary for list response."""

    country_code: str = Field(description="ISO 3166-1 alpha-2 country code")
    country_name_cn: str = Field(description="国家中文名")
    country_name_en: str | None = Field(default=None, description="Country name in English")
    school_count: int = Field(default=0, description="Number of schools in this country")
    professor_count: int = Field(default=0, description="Number of professors in this country")


class CountryListResponse(BaseModel):
    """Countries list response."""

    items: list[CountrySummary] = Field(description="Country list")
    total: int = Field(description="Total count")


class SchoolSummary(BaseModel):
    """School summary for list response."""

    school_id: int = Field(description="School ID")
    school_name: str = Field(description="School name")
    school_alias: str | None = Field(default=None, description="School alias")
    country_code: str | None = Field(default=None, description="Country code")
    country_name: str | None = Field(default=None, description="Country name")
    professor_count: int = Field(default=0, description="Number of professors")
    student_count: int = Field(default=0, description="Number of students")
    homepage_url: str | None = Field(default=None, description="School homepage URL")
    is_top_school: bool = Field(default=False, description="是否为Top院校")


class SchoolDetail(BaseModel):
    """School detail response."""

    school_id: int = Field(description="School ID")
    school_name: str = Field(description="School name")
    school_alias: str | None = Field(default=None, description="School alias")
    country_code: str | None = Field(default=None, description="Country code")
    country_name: str | None = Field(default=None, description="Country name")
    school_intro: str | None = Field(default=None, description="School introduction")
    homepage_url: str | None = Field(default=None, description="School homepage URL")
    professor_count: int = Field(default=0, description="Number of professors")
    student_count: int = Field(default=0, description="Number of students")
    talent_count: int = Field(default=0, description="Total number of talents")
    graduate_count: int = Field(default=0, description="Number of graduates")
    unknown_count: int = Field(default=0, description="Number of unknown role types")
    is_top_school: bool = Field(default=False, description="是否为Top院校")


class SchoolStats(BaseModel):
    """School statistics."""

    professor_count: int = Field(default=0, description="Number of professors")
    student_count: int = Field(default=0, description="Number of students")
    talent_count: int = Field(default=0, description="Total number of talents")
    graduate_count: int = Field(default=0, description="Number of graduates")
    unknown_count: int = Field(default=0, description="Number of unknown role types")


class TalentSummary(BaseModel):
    """Talent summary for list response."""

    talent_id: int = Field(description="Talent ID")
    name: str = Field(description="Name")
    name_en: str | None = Field(default=None, description="English name")
    orcid: str | None = Field(default=None, description="ORCID identifier")
    role_type: str = Field(description="Role type: professor/student")
    role_confidence: float = Field(default=0.0, description="Role detection confidence")
    school_id: int | None = Field(default=None, description="School ID")
    school_name: str | None = Field(default=None, description="School name")
    # Primary institutions (v1.5)
    education_school_id: int | None = Field(default=None, description="Primary education institution ID")
    education_school_name: str | None = Field(default=None, description="Primary education institution name")
    company_school_id: int | None = Field(default=None, description="Primary company/organization ID")
    company_school_name: str | None = Field(default=None, description="Primary company/organization name")
    current_title: str | None = Field(default=None, description="Current title/position")
    works_count: int = Field(default=0, description="Number of works")
    cited_by_count: int = Field(default=0, description="Citation count")
    h_index: int = Field(default=0, description="H-index")
    topic_tags: list[str] = Field(default_factory=list, description="Topic tags")
    openalex_topics: list[str] = Field(default_factory=list, description="OpenAlex研究主题")


class TechTagItem(BaseModel):
    """Tech tag for talent."""

    tech_domain_id: int = Field(description="Tech domain ID")
    tech_domain_name: str = Field(description="Tech domain name")
    tech_direction_id: int | None = Field(default=None, description="Tech direction ID")
    tech_direction_name: str | None = Field(default=None, description="Tech direction name")


class TalentDetail(BaseModel):
    """Talent detail response."""

    talent_id: int = Field(description="Talent ID")
    name: str = Field(description="Name")
    name_en: str | None = Field(default=None, description="English name")
    orcid: str | None = Field(default=None, description="ORCID identifier")
    role_type: str = Field(description="Role type")
    role_confidence: float = Field(default=0.0, description="Role detection confidence")
    school_id: int | None = Field(default=None, description="School ID")
    school_name: str | None = Field(default=None, description="School name")
    # Primary institutions (v1.5)
    education_school_id: int | None = Field(default=None, description="Primary education institution ID")
    education_school_name: str | None = Field(default=None, description="Primary education institution name")
    company_school_id: int | None = Field(default=None, description="Primary company/organization ID")
    company_school_name: str | None = Field(default=None, description="Primary company/organization name")
    current_title: str | None = Field(default=None, description="Current title/position")
    works_count: int = Field(default=0, description="Number of works")
    cited_by_count: int = Field(default=0, description="Citation count")
    h_index: int = Field(default=0, description="H-index")
    latest_active_year: int | None = Field(default=None, description="Latest active publication year")
    topic_tags: list[str] = Field(default_factory=list, description="Topic tags")
    openalex_topics: list[str] = Field(default_factory=list, description="OpenAlex研究主题")
    tech_tags: list[TechTagItem] = Field(default_factory=list, description="技术领域标签")
    summary: str | None = Field(default=None, description="Talent summary/recruitment assessment")
    department_name: str | None = Field(default=None, description="Department name")
    lab_name: str | None = Field(default=None, description="Laboratory name")

    # Role profile details
    role_reason: str | None = Field(default=None, description="Reason for role classification")
    academic_age: int | None = Field(default=None, description="Academic age (years since first work)")

    # Representative works
    selected_works: list[SelectedWorkResponse] = Field(default_factory=list, description="Selected representative works")


class SelectedWorkResponse(BaseModel):
    """Selected work for talent detail."""

    work_id: int = Field(description="Work ID")
    title: str = Field(description="Work title")
    publication_year: int | None = Field(default=None, description="Publication year")
    venue_name: str | None = Field(default=None, description="Venue/conference name")
    citation_count: int = Field(default=0, description="Citation count")
    doi: str | None = Field(default=None, description="DOI identifier")


class TalentFilterParams(BaseModel):
    """Talent filter parameters."""

    school_id: int | None = Field(default=None, description="Filter by school ID")
    country_code: str | None = Field(default=None, description="Filter by country code")
    role_type: str | None = Field(default=None, description="Filter by role type")
    min_works: int | None = Field(default=None, description="Minimum number of works")
    min_citations: int | None = Field(default=None, description="Minimum citation count")
    keyword: str | None = Field(default=None, description="Keyword filter")


class SearchTalentResult(BaseModel):
    """Search result for talent."""

    talent_id: int = Field(description="Talent ID")
    name: str = Field(description="Name")
    name_en: str | None = Field(default=None, description="English name")
    role_type: str = Field(description="Role type")
    school_name: str | None = Field(default=None, description="School name")
    current_title: str | None = Field(default=None, description="Current title/position")
    works_count: int = Field(default=0, description="Number of works")
    cited_by_count: int = Field(default=0, description="Citation count")
    h_index: int = Field(default=0, description="H-index")
    topic_tags: list[str] = Field(default_factory=list, description="Topic tags")
    openalex_topics: list[str] = Field(default_factory=list, description="OpenAlex研究主题")
    highlight: str | None = Field(default=None, description="Highlighted search result snippet")


class SearchResponse(BaseModel):
    """Search API response."""

    items: list[SearchTalentResult] = Field(description="Search results")
    total: int = Field(description="Total count")
    query: str = Field(description="Search query")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Items per page")


class ComparisonFieldItem(BaseModel):
    """Comparison field definition."""

    key: str = Field(description="Field key")
    label: str = Field(description="Field display label")


class TalentCompareItem(BaseModel):
    """Talent data for comparison."""

    talent_id: int = Field(description="Talent ID")
    name: str = Field(description="Name")
    name_en: str | None = Field(default=None, description="English name")
    orcid: str | None = Field(default=None, description="ORCID identifier")
    role_type: str = Field(description="Role type")
    school_id: int | None = Field(default=None, description="School ID")
    school_name: str | None = Field(default=None, description="School name")
    current_title: str | None = Field(default=None, description="Current title/position")
    department_name: str | None = Field(default=None, description="Department name")
    lab_name: str | None = Field(default=None, description="Laboratory name")
    works_count: int = Field(default=0, description="Number of works")
    cited_by_count: int = Field(default=0, description="Citation count")
    h_index: int = Field(default=0, description="H-index")
    latest_active_year: int | None = Field(default=None, description="Latest active publication year")
    topic_tags: list[str] = Field(default_factory=list, description="Topic tags")
    openalex_topics: list[str] = Field(default_factory=list, description="OpenAlex研究主题")
    academic_age: int | None = Field(default=None, description="Academic age")


class TalentCompareResponse(BaseModel):
    """Talent comparison response."""

    talents: list[TalentCompareItem] = Field(description="Talent data list")
    comparison_fields: list[ComparisonFieldItem] = Field(description="Comparison field definitions")


# Resolve forward reference for TalentDetail
TalentDetail.model_rebuild()
