"""
Schemas module.
Pydantic models for API request/response handling.
"""
from app.schemas.common import (
    PaginationParams,
    PaginatedResponse,
    ErrorResponse,
    SuccessResponse,
    HealthResponse,
)
from app.schemas.overview import (
    OverviewStats,
    OverviewResponse,
    CountrySummary,
    CountryListResponse,
    SchoolSummary,
    SchoolDetail,
    SchoolStats,
    TalentSummary,
    TalentDetail,
    SelectedWorkResponse,
    TalentFilterParams,
    SearchTalentResult,
    SearchResponse,
)

__all__ = [
    # Common
    "PaginationParams",
    "PaginatedResponse",
    "ErrorResponse",
    "SuccessResponse",
    "HealthResponse",
    # Overview
    "OverviewStats",
    "OverviewResponse",
    # Countries
    "CountrySummary",
    "CountryListResponse",
    # Schools
    "SchoolSummary",
    "SchoolDetail",
    "SchoolStats",
    # Talents
    "TalentSummary",
    "TalentDetail",
    "SelectedWorkResponse",
    "TalentFilterParams",
    # Search
    "SearchTalentResult",
    "SearchResponse",
]
