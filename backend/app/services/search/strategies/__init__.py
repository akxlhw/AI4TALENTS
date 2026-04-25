"""Search strategies.

Each strategy encapsulates a single search mode, keeping the service
focused purely on coordination.
"""

from app.services.search.strategies.base import SearchContext, SearchStrategy
from app.services.search.strategies.fulltext import FulltextSearchStrategy
from app.services.search.strategies.hybrid import HybridSearchStrategy
from app.services.search.strategies.keyword import KeywordSearchStrategy
from app.services.search.strategies.semantic import SemanticSearchStrategy

__all__ = [
    "SearchContext",
    "SearchStrategy",
    "KeywordSearchStrategy",
    "FulltextSearchStrategy",
    "SemanticSearchStrategy",
    "HybridSearchStrategy",
]
