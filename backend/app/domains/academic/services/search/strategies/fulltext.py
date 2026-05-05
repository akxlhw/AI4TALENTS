"""Fulltext search strategy (PostgreSQL tsvector)."""

from __future__ import annotations

import logging

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.academic.models.search import SearchTalentDocument
from app.domains.academic.services.search.strategies.base import SearchStrategy
from app.domains.academic.services.search.utils import apply_search_document_filters

logger = logging.getLogger(__name__)


class FulltextSearchStrategy(SearchStrategy):
    """Fulltext search using PostgreSQL tsvector.

    Falls back to keyword search when the document table is empty
    or when tsvector search returns no results.
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
        session = session or self.context.session

        try:
            # Check if fulltext search is available
            count_query = select(func.count()).select_from(SearchTalentDocument)
            count_result = await session.execute(count_query)
            doc_count = count_result.scalar() or 0

            if doc_count == 0:
                logger.info(
                    "SearchTalentDocument table is empty, falling back to keyword search"
                )
                return await self._fallback(query, page, page_size, filters)

            # Build tsquery with OR connector for partial matching
            search_terms = query.strip().split()
            tsquery = " | ".join(search_terms)

            query_stmt = (
                select(SearchTalentDocument)
                .where(SearchTalentDocument.is_active.is_(True))
                .where(
                    text("search_vector @@ to_tsquery('simple', :tsquery)").bindparams(
                        tsquery=tsquery
                    )
                )
            )
            query_stmt = apply_search_document_filters(query_stmt, filters)

            # Get total count
            count_query = select(func.count()).select_from(query_stmt.subquery())
            total_result = await session.execute(count_query)
            total = total_result.scalar() or 0

            # Fallback to ILIKE if tsquery returns no results
            if total == 0:
                logger.info(
                    f"tsquery search returned 0 results, falling back to ILIKE for query: {query}"
                )
                pattern = f"%{query}%"
                query_stmt = (
                    select(SearchTalentDocument)
                    .where(SearchTalentDocument.is_active.is_(True))
                    .where(SearchTalentDocument.search_text.ilike(pattern))
                )
                query_stmt = apply_search_document_filters(query_stmt, filters)

                count_query = select(func.count()).select_from(query_stmt.subquery())
                total_result = await session.execute(count_query)
                total = total_result.scalar() or 0

            # Apply pagination
            offset = (page - 1) * page_size
            query_stmt = query_stmt.order_by(SearchTalentDocument.cited_by_count.desc())
            query_stmt = query_stmt.offset(offset).limit(page_size)

            result = await session.execute(query_stmt)
            docs = list(result.scalars().all())

            # Convert results
            items = []
            for doc in docs:
                items.append(
                    {
                        "talent_id": doc.talent_id,
                        "name": doc.name,
                        "name_en": None,
                        "title": None,
                        "school_id": doc.school_id,
                        "school_name": doc.school_name,
                        "role_type": doc.role_type,
                        "topic_tags": doc.topic_tags or [],
                        "openalex_topics": [],
                        "works_count": doc.works_count,
                        "cited_by_count": doc.cited_by_count,
                        "h_index": doc.h_index,
                        "orcid": doc.orcid,
                    }
                )

            return {"total": total, "items": items}

        except Exception as e:
            logger.warning(f"Fulltext search failed: {e}, falling back to keyword search")
            return await self._fallback(query, page, page_size, filters)

    async def _fallback(
        self, query: str, page: int, page_size: int, filters: dict | None
    ) -> dict:
        """Delegate to keyword search strategy."""
        keyword = self.context.strategies.get("keyword")
        if keyword:
            return await keyword.search(query, page, page_size, filters)
        return {"total": 0, "items": []}
