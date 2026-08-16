"""Talent GIN-index optimized search mixin (openalex_topics / paper titles).

Split from talent_search_repository.py; mixed into TalentSearchRepository via
the inheritance chain.
"""

# ruff: noqa: S608

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import text

from app.domains.academic.models.talent import Talent

from .talent_vector_search import TalentVectorSearchMixin

logger = logging.getLogger(__name__)


class TalentGinSearchMixin(TalentVectorSearchMixin):
    """GIN index optimized searches and JD research-keyword aggregation."""

    # ========================================
    # GIN Index Optimized Search Methods
    # ========================================

    async def search_by_openalex_topics_gin(
        self,
        keywords: list[str],
        match_mode: str = "exact",
        filters: dict[str, Any] | None = None,
        limit: int = 100,
    ) -> list[Talent]:
        """
        Search talents by openalex_topics using GIN index.

        This method leverages the GIN index on openalex_topics for efficient
        JSON array containment queries, significantly faster than ILIKE scans.

        Args:
            keywords: List of keywords to search
            match_mode:
                - "exact": Precise match using @> operator (index accelerated)
                - "fuzzy": Substring match using jsonb_array_elements + ILIKE
            filters: Additional filters (school_id, role_type, etc.)
            limit: Maximum results

        Returns:
            List of matching Talent instances
        """
        if not keywords:
            return []

        # Build filter clauses and optional JOINs for raw SQL
        filter_clauses = ["t.is_visible = TRUE"]
        params: dict[str, Any] = {}
        join_clauses: list[str] = []
        if filters:
            self._build_jd_filters(filters, filter_clauses, params, join_clauses)

        filter_sql = " AND ".join(filter_clauses)
        join_sql = "\n".join(join_clauses)

        if match_mode == "exact":
            # Precise match: uses GIN index with @> operator
            conditions = []
            for _i, kw in enumerate(keywords):
                escaped_kw = json.dumps(kw)
                conditions.append(f"t.openalex_topics::jsonb @> '[{escaped_kw}]'::jsonb")
            conditions_sql = " OR ".join(conditions)
            query_str = f"""
                SELECT t.*
                FROM core_talent t
                {join_sql}
                WHERE {filter_sql}
                AND ({conditions_sql})
                ORDER BY t.cited_by_count DESC
                LIMIT :limit
            """
        else:
            # Fuzzy match: uses pg_trgm GIN index on openalex_topics::text
            keyword_conditions = []
            for i, kw in enumerate(keywords):
                keyword_conditions.append(f"t.openalex_topics::text ILIKE :pattern_{i}")
                params[f"pattern_{i}"] = f"%{kw}%"
            conditions_sql = " OR ".join(keyword_conditions)
            query_str = f"""
                SELECT t.*
                FROM core_talent t
                {join_sql}
                WHERE {filter_sql}
                AND ({conditions_sql})
                ORDER BY t.cited_by_count DESC
                LIMIT :limit
            """

        params["limit"] = limit
        result = await self.session.execute(text(query_str), params)
        rows = result.fetchall()

        # Get talent IDs and fetch full objects
        talent_ids = [row.talent_id for row in rows if hasattr(row, "talent_id")]
        if not talent_ids:
            return []

        return await self.get_by_ids(talent_ids, include_relations=True)

    async def _search_by_paper_titles_gin(
        self,
        keywords: list[str],
        filters: dict[str, Any] | None = None,
        limit: int = 100,
    ) -> list[Talent]:
        """
        Search talents by paper titles using pg_trgm GIN index.

        Uses the trigram index on raw_work.title for efficient ILIKE queries.

        Args:
            keywords: List of keywords to search in paper titles
            filters: Additional filters
            limit: Maximum results

        Returns:
            List of matching Talent instances
        """
        if not keywords:
            return []

        # Build OR conditions for keywords using ILIKE with pg_trgm index support
        keyword_conditions = " OR ".join([f"rw.title ILIKE :kw_{i}" for i in range(len(keywords))])
        params: dict[str, Any] = {f"kw_{i}": f"%{kw}%" for i, kw in enumerate(keywords)}

        # Build filter clauses with optional JOINs
        filter_clauses: list[str] = []
        join_clauses: list[str] = []
        if filters:
            self._build_jd_filters(filters, filter_clauses, params, join_clauses)

        filter_sql = " AND " + " AND ".join(filter_clauses) if filter_clauses else ""
        join_sql = "\n".join(join_clauses)

        # Safe: keyword_conditions uses parameterized placeholders, filter_sql uses whitelisted fields
        query_str = f"""
            SELECT DISTINCT t.talent_id
            FROM core_talent t
            INNER JOIN std_author sa ON sa.std_author_id = t.std_author_id
            INNER JOIN raw_work rw ON (
                rw.author_ids::jsonb ? sa.openalex_author_id
                OR rw.author_ids::text LIKE '%' || sa.openalex_author_id || '%'
            )
            {join_sql}
            WHERE t.is_visible = TRUE
            AND ({keyword_conditions})
            {filter_sql}
            LIMIT :limit
        """
        params["limit"] = limit

        result = await self.session.execute(text(query_str), params)
        talent_ids = [row.talent_id for row in result.fetchall()]

        if not talent_ids:
            return []

        # Fetch full Talent objects with relationships
        return await self.get_by_ids(talent_ids, include_relations=True)

    async def search_by_research_keywords(
        self,
        keywords: list[str],
        search_scope: list[str] = None,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Comprehensive search for JD matching using GIN indexes.

        Searches both openalex_topics (research direction) and paper titles
        with optimized index usage.

        Args:
            keywords: List of research area keywords
            search_scope: Fields to search ("openalex_topics", "paper_titles")
            filters: Additional filters
            limit: Maximum results

        Returns:
            List of dicts with keys: talent, paper_titles, openalex_topics, matched_keywords
        """
        if search_scope is None:
            search_scope = ["openalex_topics", "paper_titles"]
        if not keywords:
            return []

        talents: list[Talent] = []
        talent_id_set: set = set()

        # 1. Search openalex_topics using pg_trgm GIN index (fuzzy match)
        if "openalex_topics" in search_scope:
            topic_talents = await self.search_by_openalex_topics_gin(
                keywords=keywords,
                match_mode="fuzzy",
                filters=filters,
                limit=limit,
            )
            for t in topic_talents:
                if t.talent_id not in talent_id_set:
                    talents.append(t)
                    talent_id_set.add(t.talent_id)

        # 2. Search paper titles using pg_trgm GIN index
        if "paper_titles" in search_scope and len(talents) < limit:
            paper_talents = await self._search_by_paper_titles_gin(
                keywords=keywords,
                filters=filters,
                limit=limit,
            )
            for t in paper_talents:
                if t.talent_id not in talent_id_set:
                    talents.append(t)
                    talent_id_set.add(t.talent_id)

        logger.info(f"Found {len(talents)} candidates for keywords: {keywords}")

        # 3. Batch get paper titles
        talent_ids = [t.talent_id for t in talents]
        paper_titles_map = await self.get_paper_titles_for_talents(talent_ids)

        # 4. Build result with matched keywords
        candidates = []
        for talent in talents:
            paper_titles = paper_titles_map.get(talent.talent_id, [])
            openalex_topics = talent.openalex_topics or []
            matched_keywords = self._find_matched_keywords(keywords, talent, paper_titles)

            candidates.append(
                {
                    "talent": talent,
                    "paper_titles": paper_titles,
                    "openalex_topics": openalex_topics,
                    "matched_keywords": matched_keywords,
                }
            )

        return candidates[:limit]

    def _find_matched_keywords(
        self,
        keywords: list[str],
        talent: Talent,
        paper_titles: list[str] = None,
    ) -> list[str]:
        """
        Find which keywords matched a talent's profile.

        Args:
            keywords: List of search keywords
            talent: Talent instance
            paper_titles: Optional list of paper titles

        Returns:
            List of matched keywords
        """
        matched = set()
        all_text = " ".join(
            [t.lower() for t in (talent.openalex_topics or [])]
            + [t.lower() for t in (paper_titles or [])]
        )
        for keyword in keywords:
            if keyword.lower() in all_text:
                matched.add(keyword)
        return list(matched)
