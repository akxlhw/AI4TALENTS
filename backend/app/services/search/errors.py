"""Search error types (re-exported from llm.errors for convenience)."""

from app.services.llm.errors import (
    EmbeddingServiceError,
    EmptyQueryError,
    FulltextSearchError,
    InvalidSearchModeError,
    SearchError,
    SemanticSearchError,
    VectorParseError,
)

__all__ = [
    "SearchError",
    "EmptyQueryError",
    "InvalidSearchModeError",
    "SemanticSearchError",
    "FulltextSearchError",
    "VectorParseError",
    "EmbeddingServiceError",
]
