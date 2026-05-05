"""
Unified Role Identification Service.

This module provides a centralized, consistent approach to identify
academic talent roles based on OpenAlex data characteristics.

Role Types:
- professor: Senior researchers with significant academic impact
- student: Currently enrolled students with limited publications
- graduate: Early-career researchers who have recently graduated
- unknown: Insufficient data to determine role
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.models.enums import RoleType

logger = logging.getLogger(__name__)


@dataclass
class RoleIdentificationResult:
    """Result of role identification with metadata."""

    role_type: str
    confidence: float
    reason: str


class RoleIdentifier:
    """
    Unified role identification service for academic talents.

    This class provides a single source of truth for determining
    researcher roles based on OpenAlex metrics, ensuring consistency
    across all data collection and processing pipelines.

    Role Identification Logic (priority order):

    | Role      | Condition                          | Confidence |
    |-----------|------------------------------------|------------|
    | professor | h_index >= 25                      | 0.95       |
    | professor | works >= 50 && cited >= 2000       | 0.90       |
    | professor | works >= 30 && h_index >= 15       | 0.85       |
    | student   | works <= 3                         | 0.80       |
    | student   | works <= 8 && cited < 100          | 0.75       |
    | graduate  | 8 < works < 30                     | 0.70       |
    | unknown   | other cases                        | 0.50       |
    """

    # Professor thresholds
    PROFESSOR_H_INDEX_HIGH = 25
    PROFESSOR_WORKS_HIGH = 50
    PROFESSOR_CITED_HIGH = 2000
    PROFESSOR_WORKS_MEDIUM = 30
    PROFESSOR_H_INDEX_MEDIUM = 15

    # Student thresholds
    STUDENT_WORKS_VERY_LOW = 3
    STUDENT_WORKS_LOW = 8
    STUDENT_CITED_LOW = 100

    # Graduate thresholds
    GRADUATE_WORKS_MIN = 8
    GRADUATE_WORKS_MAX = 30

    @classmethod
    def identify(
        cls,
        works_count: int,
        cited_by_count: int,
        h_index: int = 0,
    ) -> RoleIdentificationResult:
        """
        Identify role type based on academic metrics.

        Args:
            works_count: Number of published works
            cited_by_count: Total citation count
            h_index: H-index value

        Returns:
            RoleIdentificationResult with role type, confidence, and reason
        """
        # Ensure non-negative values
        works_count = max(0, works_count or 0)
        cited_by_count = max(0, cited_by_count or 0)
        h_index = max(0, h_index or 0)

        # Professor identification (highest priority)
        if h_index >= cls.PROFESSOR_H_INDEX_HIGH:
            return RoleIdentificationResult(
                role_type=RoleType.PROFESSOR.value,
                confidence=0.95,
                reason=f"h_index >= {cls.PROFESSOR_H_INDEX_HIGH} ({h_index})",
            )

        if works_count >= cls.PROFESSOR_WORKS_HIGH and cited_by_count >= cls.PROFESSOR_CITED_HIGH:
            return RoleIdentificationResult(
                role_type=RoleType.PROFESSOR.value,
                confidence=0.90,
                reason=f"works >= {cls.PROFESSOR_WORKS_HIGH} ({works_count}) and cited >= {cls.PROFESSOR_CITED_HIGH} ({cited_by_count})",
            )

        if works_count >= cls.PROFESSOR_WORKS_MEDIUM and h_index >= cls.PROFESSOR_H_INDEX_MEDIUM:
            return RoleIdentificationResult(
                role_type=RoleType.PROFESSOR.value,
                confidence=0.85,
                reason=f"works >= {cls.PROFESSOR_WORKS_MEDIUM} ({works_count}) and h_index >= {cls.PROFESSOR_H_INDEX_MEDIUM} ({h_index})",
            )

        # Student identification
        if works_count <= cls.STUDENT_WORKS_VERY_LOW:
            return RoleIdentificationResult(
                role_type=RoleType.STUDENT.value,
                confidence=0.80,
                reason=f"works <= {cls.STUDENT_WORKS_VERY_LOW} ({works_count})",
            )

        if works_count <= cls.STUDENT_WORKS_LOW and cited_by_count < cls.STUDENT_CITED_LOW:
            return RoleIdentificationResult(
                role_type=RoleType.STUDENT.value,
                confidence=0.75,
                reason=f"works <= {cls.STUDENT_WORKS_LOW} ({works_count}) and cited < {cls.STUDENT_CITED_LOW} ({cited_by_count})",
            )

        # Graduate identification (early career researchers)
        if cls.GRADUATE_WORKS_MIN < works_count < cls.GRADUATE_WORKS_MAX:
            return RoleIdentificationResult(
                role_type=RoleType.GRADUATE.value,
                confidence=0.70,
                reason=f"works between {cls.GRADUATE_WORKS_MIN} and {cls.GRADUATE_WORKS_MAX} ({works_count})",
            )

        # Default to unknown for edge cases
        # This includes cases like high works but low citations, or unusual patterns
        return RoleIdentificationResult(
            role_type=RoleType.UNKNOWN.value,
            confidence=0.50,
            reason=f"Unable to classify: works={works_count}, cited={cited_by_count}, h_index={h_index}",
        )

    @classmethod
    def identify_from_author_data(cls, author_data: dict[str, Any]) -> RoleIdentificationResult:
        """
        Identify role type from OpenAlex author data.

        Args:
            author_data: Raw author data from OpenAlex API

        Returns:
            RoleIdentificationResult with role type, confidence, and reason
        """
        works_count = author_data.get("works_count", 0) or 0
        cited_by_count = author_data.get("cited_by_count", 0) or 0

        # Get h_index from summary_stats
        summary_stats = author_data.get("summary_stats", {}) or {}
        h_index = summary_stats.get("h_index", 0) or 0

        return cls.identify(works_count, cited_by_count, h_index)

    @classmethod
    def get_role_display_name(cls, role_type: str) -> str:
        """
        Get Chinese display name for a role type.

        Args:
            role_type: Role type string

        Returns:
            Chinese display name
        """
        display_names = {
            RoleType.PROFESSOR.value: "教授",
            RoleType.STUDENT.value: "学生",
            RoleType.GRADUATE.value: "毕业生",
            RoleType.UNKNOWN.value: "未知",
        }
        return display_names.get(role_type, "未知")


# Convenience functions for backward compatibility
def determine_role(works_count: int, cited_by_count: int, h_index: int = 0) -> tuple[str, float]:
    """
    Convenience function for backward compatibility.

    Args:
        works_count: Number of published works
        cited_by_count: Total citation count
        h_index: H-index value

    Returns:
        Tuple of (role_type, confidence)
    """
    result = RoleIdentifier.identify(works_count, cited_by_count, h_index)
    return result.role_type, result.confidence


def determine_role_from_author(author_data: dict[str, Any]) -> tuple[str, float]:
    """
    Convenience function for backward compatibility.

    Args:
        author_data: Raw author data from OpenAlex API

    Returns:
        Tuple of (role_type, confidence)
    """
    result = RoleIdentifier.identify_from_author_data(author_data)
    return result.role_type, result.confidence
