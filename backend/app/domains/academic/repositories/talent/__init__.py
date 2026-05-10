"""Talent repository sub-package.

Provides specialized repositories for talent operations:
- BaseTalentRepository: Core CRUD and list queries
- TalentExportRepository: Batch and export-oriented operations
- TalentSearchRepository: Advanced search and filtering
- TalentRepository: Backward-compatible aggregate of all three
"""

from .base_talent_repository import BaseTalentRepository
from .talent_export_repository import TalentExportRepository
from .talent_search_repository import TalentSearchRepository


class TalentRepository(TalentSearchRepository):
    """Backward-compatible aggregate repository for talent operations."""

    pass


__all__ = [
    "BaseTalentRepository",
    "TalentExportRepository",
    "TalentSearchRepository",
    "TalentRepository",
]
