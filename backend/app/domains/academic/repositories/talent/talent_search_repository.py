"""Talent search repository with advanced search and filtering operations.

Implementation is split by query concern into sibling mixin modules:
- talent_keyword_search.py: keyword/JSON-field/paper-title search + common filters
- talent_vector_search.py: pgvector similarity search + JD raw-SQL filter builder
- talent_gin_search.py: GIN-index optimized searches + research-keyword aggregation

The TalentSearchRepository class below keeps the original public interface.
"""

from __future__ import annotations

from .talent_gin_search import TalentGinSearchMixin

__all__ = ["TalentSearchRepository"]


class TalentSearchRepository(TalentGinSearchMixin):
    """Repository for advanced talent search and filtering."""

    pass
