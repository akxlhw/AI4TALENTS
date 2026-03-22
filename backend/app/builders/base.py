"""
Base builder class for object construction.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging


logger = logging.getLogger(__name__)


@dataclass
class BuildResult:
    """Result of a build operation."""
    success: bool
    records_processed: int
    records_created: int
    records_updated: int
    records_failed: int
    errors: List[str]
    started_at: datetime
    completed_at: Optional[datetime] = None


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
        self.errors: List[str] = []

    @abstractmethod
    async def build(self) -> BuildResult:
        """
        Execute the build process.

        Returns:
            BuildResult with statistics and status
        """
        pass

    def log_error(self, message: str, record_id: Optional[str] = None):
        """Log an error during building."""
        error_msg = f"[Batch {self.batch_id}] {message}"
        if record_id:
            error_msg = f"[Record {record_id}] {error_msg}"
        logger.error(error_msg)
        self.errors.append(error_msg)

    def log_warning(self, message: str):
        """Log a warning during building."""
        logger.warning(f"[Batch {self.batch_id}] {message}")


def normalize_name(name: str) -> str:
    """
    Normalize a name for comparison.

    Args:
        name: Original name

    Returns:
        Normalized name (lowercase, trimmed)
    """
    if not name:
        return ""
    return name.strip().lower()


def extract_openalex_id(url_or_id: str) -> str:
    """
    Extract OpenAlex ID from URL or return as-is.

    Args:
        url_or_id: Full URL or just ID

    Returns:
        Just the ID part
    """
    if not url_or_id:
        return ""

    if url_or_id.startswith("https://"):
        return url_or_id.rstrip("/").split("/")[-1]

    return url_or_id


def calculate_quality_score(data: Dict[str, Any], required_fields: List[str]) -> float:
    """
    Calculate a quality score for a data record.

    Args:
        data: The data dictionary
        required_fields: Fields that should be present

    Returns:
        Quality score between 0 and 1
    """
    if not data:
        return 0.0

    score = 1.0

    # Check required fields
    for field in required_fields:
        if field not in data or not data[field]:
            score -= 0.2

    return max(0.0, min(1.0, score))
