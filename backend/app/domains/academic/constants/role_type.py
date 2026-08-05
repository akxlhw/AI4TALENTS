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
