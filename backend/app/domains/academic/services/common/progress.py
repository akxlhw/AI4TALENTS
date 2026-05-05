"""
Progress tracking dataclasses for services.
"""

from dataclasses import dataclass, field


@dataclass
class BaseProgress:
    """Base class for progress tracking"""

    total: int = 0
    processed: int = 0
    failed: int = 0
    current_step: str = ""


@dataclass
class FetchProgress(BaseProgress):
    """Progress tracking for fetch operations"""

    fetched: int = 0


@dataclass
class CollectionProgress(BaseProgress):
    """Collection progress tracking"""

    task_id: int = 0
    status: str = "pending"
    total_venues: int = 0
    completed_venues: int = 0
    total_works: int = 0
    estimated_works: int = 0  # 预估论文总数
    total_authors: int = 0
    total_institutions: int = 0
    normalized_authors: int = 0
    normalized_schools: int = 0
    # Serving layer sync stats
    synced_authors: int = 0
    created_talents: int = 0
    updated_talents: int = 0
    created_tech_tags: int = 0
    created_schools: int = 0
    errors: list[str] = field(default_factory=list)
    # Incremental update tracking
    affected_school_ids: set[int] = field(default_factory=set)
