"""
Role Type Constants

Unified role type definitions for academic talent identification.
Matches frontend/src/constants/roleType.ts
"""

from enum import Enum


class RoleType(str, Enum):
    """Role type enum for academic talent classification."""

    PROFESSOR = "professor"  # 教授/研究员 (h_index >= 25 or high citation count)
    STUDENT = "student"  # 在读学生 (works <= 8 and low citations)
    GRADUATE = "graduate"  # 毕业/早期研究者 (8 < works < 30, transitioning)
    UNKNOWN = "unknown"  # 未知 (insufficient data)

    @property
    def display_text(self) -> str:
        """Get Chinese display text for the role type."""
        texts = {
            RoleType.PROFESSOR: "教授/研究员",
            RoleType.STUDENT: "学生",
            RoleType.GRADUATE: "毕业生",
            RoleType.UNKNOWN: "未知",
        }
        return texts.get(self, "未知")

    @property
    def color(self) -> str:
        """Get Ant Design tag color for the role type."""
        colors = {
            RoleType.PROFESSOR: "green",
            RoleType.STUDENT: "blue",
            RoleType.GRADUATE: "orange",
            RoleType.UNKNOWN: "default",
        }
        return colors.get(self, "default")


# Legacy role type mappings for backward compatibility
LEGACY_ROLE_TYPE_MAP: dict[str, str] = {
    "graduated": "graduate",
    "teaching_research": "professor",
    "associate_professor": "professor",
    "researcher": "graduate",
    "phd_student": "student",
    "master_student": "student",
}


def normalize_role_type(role_type: str) -> str:
    """
    Normalize role type string with backward compatibility.

    Args:
        role_type: Role type string (may be legacy or current)

    Returns:
        Normalized role type string
    """
    if role_type in LEGACY_ROLE_TYPE_MAP:
        return LEGACY_ROLE_TYPE_MAP[role_type]
    return role_type
