"""
Filter parameter dataclasses for repository methods.

Provides structured filter objects to reduce parameter sprawl
and enable reusable filter logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class PaginationParams:
    """Pagination parameters for list queries."""

    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        """Calculate offset for database query."""
        return (self.page - 1) * self.page_size

    @classmethod
    def from_dict(cls, data: dict) -> PaginationParams:
        """Create from dictionary."""
        return cls(
            page=data.get("page", 1),
            page_size=data.get("page_size", 20),
        )


@dataclass
class TalentFilterParams:
    """
    Filter parameters for talent queries.

    Used by TalentRepository.get_list, search services, etc.
    """

    # School filters
    school_id: int | None = None
    country_code: str | None = None

    # Role filters
    role_type: str | None = None

    # Metrics filters
    min_works: int | None = None
    min_citations: int | None = None

    # Tech domain filters
    tech_domain_id: int | None = None
    tech_direction_id: int | None = None

    # Text search
    keyword: str | None = None

    # Visibility
    visible_only: bool = True

    # Additional filters
    is_graduated: bool | None = None
    confirm_status: str | None = None

    def has_filters(self) -> bool:
        """Check if any filter is set."""
        return any(
            [
                self.school_id,
                self.country_code,
                self.role_type,
                self.min_works,
                self.min_citations,
                self.tech_domain_id,
                self.tech_direction_id,
                self.keyword,
                self.is_graduated is not None,
                self.confirm_status,
            ]
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        result: dict[str, Any] = {}
        if self.school_id is not None:
            result["school_id"] = self.school_id
        if self.country_code is not None:
            result["country_code"] = self.country_code
        if self.role_type is not None:
            result["role_type"] = self.role_type
        if self.min_works is not None:
            result["min_works"] = self.min_works
        if self.min_citations is not None:
            result["min_citations"] = self.min_citations
        if self.tech_domain_id is not None:
            result["tech_domain_id"] = self.tech_domain_id
        if self.tech_direction_id is not None:
            result["tech_direction_id"] = self.tech_direction_id
        if self.keyword is not None:
            result["keyword"] = self.keyword
        if self.is_graduated is not None:
            result["is_graduated"] = self.is_graduated
        if self.confirm_status is not None:
            result["confirm_status"] = self.confirm_status
        return result

    @classmethod
    def from_dict(cls, data: dict) -> TalentFilterParams:
        """Create from dictionary."""
        return cls(
            school_id=data.get("school_id"),
            country_code=data.get("country_code"),
            role_type=data.get("role_type"),
            min_works=data.get("min_works"),
            min_citations=data.get("min_citations"),
            tech_domain_id=data.get("tech_domain_id"),
            tech_direction_id=data.get("tech_direction_id"),
            keyword=data.get("keyword"),
            visible_only=data.get("visible_only", True),
            is_graduated=data.get("is_graduated"),
            confirm_status=data.get("confirm_status"),
        )


@dataclass
class VenueFilterParams:
    """Filter parameters for venue queries."""

    venue_type: str | None = None
    is_enabled: bool | None = None
    keyword: str | None = None
    tech_domain_id: int | None = None

    def has_filters(self) -> bool:
        """Check if any filter is set."""
        return any(
            [
                self.venue_type,
                self.is_enabled is not None,
                self.keyword,
                self.tech_domain_id,
            ]
        )

    @classmethod
    def from_dict(cls, data: dict) -> VenueFilterParams:
        """Create from dictionary."""
        return cls(
            venue_type=data.get("venue_type"),
            is_enabled=data.get("is_enabled"),
            keyword=data.get("keyword"),
            tech_domain_id=data.get("tech_domain_id"),
        )


@dataclass
class CollectTaskFilterParams:
    """Filter parameters for collect task queries."""

    status: str | None = None
    tech_domain_id: int | None = None

    def has_filters(self) -> bool:
        """Check if any filter is set."""
        return any([self.status, self.tech_domain_id])

    @classmethod
    def from_dict(cls, data: dict) -> CollectTaskFilterParams:
        """Create from dictionary."""
        return cls(
            status=data.get("status"),
            tech_domain_id=data.get("tech_domain_id"),
        )
