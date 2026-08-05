"""
Base builder class for object construction.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class BuildResult:
    """Result of a build operation."""

    success: bool
    records_processed: int
    records_created: int
    records_updated: int
    records_failed: int
    errors: list[str]
    started_at: datetime
    completed_at: datetime | None = None


class BaseBuilder(ABC):
    """
    Abstract base class for object builders.

    Builders transform raw source data into domain objects.
    """

    def __init__(self, batch_id: int):
        """
        Initialize builder.

        Args:
            batch_id: The sync batch ID being processed
        """
        self.batch_id = batch_id
        self.errors: list[str] = []

    @abstractmethod
    async def build(self) -> BuildResult:
        """
        Execute the build process.

        Returns:
            BuildResult with statistics and status
        """
        pass

    def log_error(self, message: str, record_id: str | None = None) -> None:
        """Log an error during building."""
        error_msg = f"[Batch {self.batch_id}] {message}"
        if record_id:
            error_msg = f"[Record {record_id}] {error_msg}"
        logger.error(error_msg)
        self.errors.append(error_msg)
