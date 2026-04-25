"""
Schemas module.
Pydantic models for API request/response handling.
"""

from app.schemas.common import (
    ErrorResponse,
    HealthResponse,
    PaginatedResponse,
    PaginationParams,
    SuccessResponse,
)
from app.schemas.overview import (
    CountryListResponse,
    CountrySummary,
    OverviewResponse,
    OverviewStats,
    SchoolDetail,
    SchoolStats,
    SchoolSummary,
    SearchResponse,
    SearchTalentResult,
    SelectedWorkResponse,
    TalentDetail,
    TalentFilterParams,
    TalentSummary,
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
