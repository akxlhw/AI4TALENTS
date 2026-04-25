"""Search service module."""

from app.services.search.errors import EmptyQueryError, InvalidSearchModeError, SearchError
from app.services.search.search_service import SearchService
from app.services.search.types import SearchConfig, SearchMode, SearchResult

__all__ = [
    "SearchService",
    "SearchMode",
    "SearchConfig",
    "SearchResult",
    "SearchError",
    "EmptyQueryError",
    "InvalidSearchModeError",
]
