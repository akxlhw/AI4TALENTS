"""
Collect Task Constants

Unified constants for collect task management.
Matches frontend/src/constants/collectTask.ts
"""
from enum import Enum


class TaskStatus(str, Enum):
    """Task status enum for collect tasks."""

    PENDING = "pending"  # 待执行
    RUNNING = "running"  # 执行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 已取消

    @property
    def display_text(self) -> str:
        """Get Chinese display text for the status."""
        texts = {
            TaskStatus.PENDING: "待执行",
            TaskStatus.RUNNING: "执行中",
            TaskStatus.COMPLETED: "已完成",
            TaskStatus.FAILED: "失败",
            TaskStatus.CANCELLED: "已取消",
        }
        return texts.get(self, "未知")

    @property
    def color(self) -> str:
        """Get Ant Design tag color for the status."""
        colors = {
            TaskStatus.PENDING: "default",
            TaskStatus.RUNNING: "processing",
            TaskStatus.COMPLETED: "success",
            TaskStatus.FAILED: "error",
            TaskStatus.CANCELLED: "warning",
        }
        return colors.get(self, "default")

    @property
    def badge_status(self) -> str:
        """Get Ant Design Badge status for the status."""
        statuses = {
            TaskStatus.PENDING: "default",
            TaskStatus.RUNNING: "processing",
            TaskStatus.COMPLETED: "success",
            TaskStatus.FAILED: "error",
            TaskStatus.CANCELLED: "warning",
        }
        return statuses.get(self, "default")


class VenueType(str, Enum):
    """Venue type enum for academic venues."""

    CONFERENCE = "conference"  # 会议
    JOURNAL = "journal"  # 期刊
    WORKSHOP = "workshop"  # 研讨会

    @property
    def display_text(self) -> str:
        """Get Chinese display text for the venue type."""
        texts = {
            VenueType.CONFERENCE: "会议",
            VenueType.JOURNAL: "期刊",
            VenueType.WORKSHOP: "研讨会",
        }
        return texts.get(self, "未知")

    @property
    def color(self) -> str:
        """Get Ant Design tag color for the venue type."""
        colors = {
            VenueType.CONFERENCE: "blue",
            VenueType.JOURNAL: "purple",
            VenueType.WORKSHOP: "cyan",
        }
        return colors.get(self, "default")


# Time range constants
MIN_START_YEAR = 2015
DEFAULT_START_YEAR = 2020
