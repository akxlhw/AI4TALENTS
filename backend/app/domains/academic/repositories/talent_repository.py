"""Repository for talent operations.

Security Note (S608):
This module uses raw SQL with f-strings for complex queries. All such queries are safe because:
- User inputs use parameterized placeholders (:param_name)
- Field names in filter clauses are from a whitelist
- Vector strings are validated by regex before use

Note: This module is now a backward-compatible re-export.
The actual implementation has been split into:
- repositories/talent/base_talent_repository.py
- repositories/talent/talent_search_repository.py
- repositories/talent/talent_export_repository.py
"""

# ruff: noqa: S608

from app.domains.academic.repositories.talent import (
    BaseTalentRepository,
    TalentExportRepository,
    TalentRepository,
    TalentSearchRepository,
)

__all__ = [
    "BaseTalentRepository",
    "TalentExportRepository",
    "TalentSearchRepository",
    "TalentRepository",
]
