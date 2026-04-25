"""Search Service implementation.

The service is intentionally thin: it validates parameters, delegates to
search strategies, and assembles the final SearchResult.
Each search mode's business logic lives in its own strategy under
``strategies/``.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.talent_repository import TalentRepository
from app.services.search.errors import EmptyQueryError
from app.services.search.strategies import (
    FulltextSearchStrategy,
    HybridSearchStrategy,
    KeywordSearchStrategy,
    SearchContext,
    SemanticSearchStrategy,
)
from app.services.search.types import SearchConfig, SearchMode, SearchResult

# Re-export utilities for backward compatibility
from app.services.search.utils import (  # noqa: F401
    CHINESE_TO_ENGLISH_MAP,
    SYNONYM_MAP,
    expand_query_with_synonyms,
    get_english_translation,
)

logger = logging.getLogger(__name__)


class SearchService:
    """搜索服务

    支持多种搜索模式：
    - KEYWORD: 使用 ILIKE 进行模式匹配
    - FULLTEXT: 使用 PostgreSQL tsvector 全文搜索
    - SEMANTIC: 使用向量相似度搜索
    - HYBRID: 结合多种搜索模式
    """

    def __init__(
        self,
        session: AsyncSession,
        embedding_service: Any = None,
        config: SearchConfig | None = None,
        talent_repository: TalentRepository | None = None,
    ) -> None:
        self.session = session
        self.embedding_service = embedding_service
        self.config = config or SearchConfig()
        self.talent_repo = talent_repository or TalentRepository(session)

        context = SearchContext(
            session=session,
            talent_repo=self.talent_repo,
            embedding_service=embedding_service,
            config=self.config,
        )

        self._strategies = {
            SearchMode.KEYWORD: KeywordSearchStrategy(context),
            SearchMode.FULLTEXT: FulltextSearchStrategy(context),
            SearchMode.SEMANTIC: SemanticSearchStrategy(context),
            SearchMode.HYBRID: HybridSearchStrategy(context),
        }
        # Allow strategies to reference each other for fallback chains
        context.strategies = {
            mode.value: strategy for mode, strategy in self._strategies.items()
        }

    async def search(
        self,
        query: str,
        mode: SearchMode | str = SearchMode.KEYWORD,
        fields: list[str] | None = None,
        fuzzy: bool = False,
        page: int = 1,
        page_size: int | None = None,
        filters: dict | None = None,
    ) -> SearchResult:
        """统一搜索入口

        Args:
            query: 搜索关键词
            mode: 搜索模式
            fields: 搜索字段列表
            fuzzy: 是否启用模糊匹配
            page: 页码
            page_size: 每页数量
            filters: 额外过滤条件

        Returns:
            SearchResult: 搜索结果

        Raises:
            EmptyQueryError: 空查询
        """
        start_time = time.time()

        # Validate query
        query = query.strip()
        if len(query) < self.config.min_query_length:
            raise EmptyQueryError()

        # Normalize mode
        if isinstance(mode, str):
            try:
                mode = SearchMode(mode.lower())
            except ValueError:
                mode = SearchMode.KEYWORD

        # Normalize pagination
        if page_size is None:
            page_size = self.config.default_page_size
        page_size = min(page_size, self.config.max_page_size)
        page = max(1, page)

        # Select strategy
        strategy = self._strategies.get(mode, self._strategies[SearchMode.KEYWORD])

        # Execute search
        result = await strategy.search(
            query=query,
            page=page,
            page_size=page_size,
            filters=filters,
            fields=fields,
            fuzzy=fuzzy,
        )

        took_ms = (time.time() - start_time) * 1000

        return SearchResult(
            total=result["total"],
            page=page,
            page_size=page_size,
            items=result["items"],
            search_mode=mode.value if isinstance(mode, SearchMode) else mode,
            took_ms=took_ms,
            precise_count=result.get("precise_count", 0),
            similar_count=result.get("similar_count", 0),
            fulltext_count=result.get("fulltext_count", 0),
            semantic_count=result.get("semantic_count", 0),
        )
