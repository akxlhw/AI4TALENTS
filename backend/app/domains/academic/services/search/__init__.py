"""Search service module."""

from app.domains.academic.services.search.errors import EmptyQueryError, InvalidSearchModeError, SearchError
from app.domains.academic.services.search.search_service import SearchService
from app.domains.academic.services.search.types import SearchConfig, SearchMode, SearchResult

__all__ = [
    "SearchService",
    "SearchMode",
    "SearchConfig",
    "SearchResult",
    "SearchError",
    "EmptyQueryError",
    "InvalidSearchModeError",
]
