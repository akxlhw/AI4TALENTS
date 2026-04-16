"""Search error types (re-exported from llm.errors for convenience)."""
from app.services.llm.errors import (
    SearchError,
    EmptyQueryError,
    InvalidSearchModeError,
    SemanticSearchError,
    FulltextSearchError,
    VectorParseError,
    EmbeddingServiceError,
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
