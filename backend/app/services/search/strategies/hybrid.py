"""Hybrid search strategy (fulltext + semantic fusion via RRF)."""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.services.search.strategies.base import SearchContext, SearchStrategy
from app.services.search.utils import get_english_translation

logger = logging.getLogger(__name__)


class HybridSearchStrategy(SearchStrategy):
    """Hybrid search combining fulltext and semantic results via Reciprocal Rank Fusion.

    Falls back to fulltext search when embedding service is unavailable,
    or to keyword search on unexpected errors.
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
            logger.info("Hybrid search: no embedding service, using fulltext only")
            return await self._fallback_fulltext(query, page, page_size, filters)

        try:
            extended_page_size = min(
                page_size * settings.SEARCH_HYBRID_EXTENDED_FACTOR, 100
            )
            english_translation = get_english_translation(query)

            # Fulltext search with independent session
            async def _do_fulltext_search():
                async with AsyncSessionLocal() as s:
                    fulltext_items = {}
                    fulltext = self.context.strategies.get("fulltext")
                    if not fulltext:
                        return {"items": []}

                    # 1. Chinese fulltext search
                    chinese_result = await fulltext.search(
                        query, 1, extended_page_size, filters, session=s
                    )
                    for item in chinese_result["items"]:
                        tid = item["talent_id"]
                        if tid not in fulltext_items:
                            fulltext_items[tid] = item

                    # 2. English translation fulltext search
                    if english_translation:
                        logger.info(
                            f"Hybrid search: also searching with English translation "
                            f"'{english_translation}'"
                        )
                        english_result = await fulltext.search(
                            english_translation, 1, extended_page_size, filters, session=s
                        )
                        for item in english_result["items"]:
                            tid = item["talent_id"]
                            if tid not in fulltext_items:
                                fulltext_items[tid] = item

                    return {"items": list(fulltext_items.values())}

            # Parallel execution
            semantic = self.context.strategies.get("semantic")

            async def _empty_semantic():
                return {"items": []}

            fulltext_result, semantic_result = await asyncio.gather(
                _do_fulltext_search(),
                semantic.search(query, 1, extended_page_size, filters)
                if semantic
                else _empty_semantic(),
            )

            # Reciprocal Rank Fusion
            k = settings.SEARCH_RRF_CONSTANT
            score_map = {}
            item_map = {}

            for rank, item in enumerate(fulltext_result["items"], 1):
                tid = item["talent_id"]
                score_map[tid] = score_map.get(tid, 0) + 1.0 / (k + rank)
                item["similarity_score"] = settings.SEARCH_PRECISE_THRESHOLD
                item["match_sources"] = ["fulltext"]
                item["_research_score"] = 0.0
                item["_papers_score"] = 0.0
                item_map[tid] = item

            for rank, item in enumerate(semantic_result["items"], 1):
                tid = item["talent_id"]
                score_map[tid] = score_map.get(tid, 0) + 1.0 / (k + rank)
                if tid in item_map:
                    existing_score = item_map[tid].get("similarity_score", 0)
                    new_score = item.get("similarity_score", 0)
                    if new_score > existing_score:
                        item_map[tid]["similarity_score"] = new_score
                    semantic_sources = item.get("match_sources", [])
                    item_map[tid]["match_sources"].extend(semantic_sources)
                    item_map[tid]["_research_score"] = item.get("_research_score", 0)
                    item_map[tid]["_papers_score"] = item.get("_papers_score", 0)
                else:
                    item_map[tid] = item

            sorted_ids = sorted(
                item_map.keys(),
                key=lambda x: (item_map[x].get("similarity_score", 0), score_map.get(x, 0)),
                reverse=True,
            )

            precise_count = sum(
                1
                for tid in sorted_ids
                if item_map[tid].get("similarity_score", 0) >= settings.SEARCH_PRECISE_THRESHOLD
            )
            similar_count = sum(
                1
                for tid in sorted_ids
                if settings.SEARCH_SIMILAR_THRESHOLD_MIN
                <= item_map[tid].get("similarity_score", 0)
                < settings.SEARCH_PRECISE_THRESHOLD
            )

            fulltext_count = sum(
                1
                for tid in sorted_ids
                if "fulltext" in item_map[tid].get("match_sources", [])
            )
            semantic_count = sum(
                1
                for tid in sorted_ids
                if any(
                    s.startswith("semantic_")
                    for s in item_map[tid].get("match_sources", [])
                )
            )

            offset = (page - 1) * page_size
            paginated_ids = sorted_ids[offset : offset + page_size]
            items = [item_map[tid] for tid in paginated_ids if tid in item_map]

            logger.info(
                f"Hybrid search: fulltext={len(fulltext_result['items'])}, "
                f"semantic={len(semantic_result['items'])}, "
                f"merged={len(sorted_ids)}, returned={len(items)}, "
                f"precise={precise_count}, similar={similar_count}, "
                f"fulltext_match={fulltext_count}, semantic_match={semantic_count}"
            )

            return {
                "total": len(sorted_ids),
                "items": items,
                "precise_count": precise_count,
                "similar_count": similar_count,
                "fulltext_count": fulltext_count,
                "semantic_count": semantic_count,
            }

        except Exception as e:
            logger.error(
                f"Hybrid search unexpected error: {e}, falling back to keyword search"
            )
            return await self._fallback_keyword(
                query, page, page_size, filters, fields, fuzzy
            )

    async def _fallback_fulltext(
        self, query: str, page: int, page_size: int, filters: dict | None
    ) -> dict:
        fulltext = self.context.strategies.get("fulltext")
        if fulltext:
            return await fulltext.search(query, page, page_size, filters)
        return {"total": 0, "items": []}

    async def _fallback_keyword(
        self,
        query: str,
        page: int,
        page_size: int,
        filters: dict | None,
        fields: list[str] | None = None,
        fuzzy: bool = False,
    ) -> dict:
        keyword = self.context.strategies.get("keyword")
        if keyword:
            return await keyword.search(query, page, page_size, filters, fields, fuzzy)
        return {"total": 0, "items": []}
