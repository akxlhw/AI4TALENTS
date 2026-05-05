"""Semantic search strategy (vector similarity)."""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.repositories.talent_repository import TalentRepository
from app.domains.shared.services.llm.errors import LLMError
from app.services.search.strategies.base import SearchContext, SearchStrategy

logger = logging.getLogger(__name__)


class SemanticSearchStrategy(SearchStrategy):
    """Semantic search using vector similarity (research + papers weighted fusion).

    Falls back to fulltext search when embedding service is unavailable
    or when vector search fails.
    """

    async def search(
        self,
        query: str,
        page: int,
        page_size: int,
        filters: dict | None,
        fields: list[str] | None = None,
        fuzzy: bool = False,
        session: AsyncSession | None = None,
    ) -> dict:
        if self.context.embedding_service is None:
            logger.warning(
                "Semantic search requested but no embedding service, falling back to fulltext"
            )
            return await self._fallback(query, page, page_size, filters)

        try:
            query_embedding = await self.context.embedding_service.get_query_embedding(query)

            RESEARCH_WEIGHT = 0.6
            PAPERS_WEIGHT = 0.4
            extended_limit = min(page_size * settings.SEARCH_HYBRID_EXTENDED_FACTOR, 100)

            async def _search_research():
                async with AsyncSessionLocal() as s:
                    repo = TalentRepository(s)
                    return await repo.search_by_vector_similarity(
                        query_embedding=query_embedding,
                        similarity_threshold=settings.SEARCH_SEMANTIC_THRESHOLD,
                        filters=filters,
                        limit=extended_limit,
                        offset=0,
                        vector_type="research",
                    )

            async def _search_papers():
                async with AsyncSessionLocal() as s:
                    repo = TalentRepository(s)
                    return await repo.search_by_vector_similarity(
                        query_embedding=query_embedding,
                        similarity_threshold=settings.SEARCH_SEMANTIC_THRESHOLD,
                        filters=filters,
                        limit=extended_limit,
                        offset=0,
                        vector_type="papers",
                    )

            (research_items, _), (papers_items, _) = await asyncio.gather(
                _search_research(),
                _search_papers(),
            )

            merged_items = self._merge_vector_scores(
                research_items=research_items,
                papers_items=papers_items,
                research_weight=RESEARCH_WEIGHT,
                papers_weight=PAPERS_WEIGHT,
            )

            offset = (page - 1) * page_size
            total = len(merged_items)
            paginated_items = merged_items[offset : offset + page_size]

            precise_count = sum(
                1
                for item in paginated_items
                if item.get("similarity_score", 0) >= settings.SEARCH_PRECISE_THRESHOLD
            )
            similar_count = sum(
                1
                for item in paginated_items
                if settings.SEARCH_SIMILAR_THRESHOLD_MIN
                <= item.get("similarity_score", 0)
                < settings.SEARCH_PRECISE_THRESHOLD
            )

            logger.info(
                f"Semantic search found {total} results "
                f"(research={len(research_items)}, papers={len(papers_items)}) "
                f"for query: {query}"
            )

            return {
                "total": total,
                "items": paginated_items,
                "precise_count": precise_count,
                "similar_count": similar_count,
            }

        except LLMError as e:
            logger.warning(f"Semantic search LLM error: {e}, falling back to fulltext")
            return await self._fallback(query, page, page_size, filters)
        except ValueError as e:
            logger.warning(f"Semantic search vector error: {e}, falling back to fulltext")
            return await self._fallback(query, page, page_size, filters)
        except Exception as e:
            logger.error(
                f"Semantic search unexpected error: {e}, falling back to fulltext"
            )
            return await self._fallback(query, page, page_size, filters)

    @staticmethod
    def _merge_vector_scores(
        research_items: list[dict],
        papers_items: list[dict],
        research_weight: float,
        papers_weight: float,
    ) -> list[dict]:
        """Merge multi-vector search results by talent_id."""
        merged_map: dict = {}

        for item in research_items:
            tid = item["talent_id"]
            score = item.get("similarity_score", 0) * research_weight
            merged_map[tid] = {
                **item,
                "similarity_score": score,
                "_research_score": item.get("similarity_score", 0),
                "_papers_score": 0.0,
                "match_sources": ["semantic_research"],
            }

        for item in papers_items:
            tid = item["talent_id"]
            score = item.get("similarity_score", 0) * papers_weight
            if tid in merged_map:
                merged_map[tid]["similarity_score"] += score
                merged_map[tid]["_papers_score"] = item.get("similarity_score", 0)
                merged_map[tid]["match_sources"].append("semantic_papers")
            else:
                merged_map[tid] = {
                    **item,
                    "similarity_score": score,
                    "_research_score": 0.0,
                    "_papers_score": item.get("similarity_score", 0),
                    "match_sources": ["semantic_papers"],
                }

        return sorted(
            merged_map.values(),
            key=lambda x: x.get("similarity_score", 0),
            reverse=True,
        )

    async def _fallback(
        self, query: str, page: int, page_size: int, filters: dict | None
    ) -> dict:
        """Delegate to fulltext search strategy."""
        fulltext = self.context.strategies.get("fulltext")
        if fulltext:
            return await fulltext.search(query, page, page_size, filters)
        keyword = self.context.strategies.get("keyword")
        if keyword:
            return await keyword.search(query, page, page_size, filters)
        return {"total": 0, "items": []}
