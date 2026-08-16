"""Talent vector similarity search mixin (pgvector) and JD filter builder.

Split from talent_search_repository.py; mixed into TalentSearchRepository via
the inheritance chain.
"""

# ruff: noqa: S608

from __future__ import annotations

import logging
import re
from typing import Any

from sqlalchemy import text

from .talent_keyword_search import TalentKeywordSearchMixin

logger = logging.getLogger(__name__)


class TalentVectorSearchMixin(TalentKeywordSearchMixin):
    """Vector similarity search over talent embeddings (pgvector)."""

    async def search_by_vector_similarity(
        self,
        query_embedding: list[float],
        similarity_threshold: float = 0.7,
        filters: dict[str, Any] | None = None,
        limit: int = 20,
        offset: int = 0,
        vector_type: str = "research",
    ) -> tuple[list[dict[str, Any]], int]:
        """
        Search talents by vector similarity using pgvector.

        Args:
            query_embedding: Query vector (1536 dimensions for OpenAI embeddings)
            similarity_threshold: Minimum similarity score (0.0-1.0)
            filters: Additional filters
            limit: Maximum results
            offset: Result offset for pagination
            vector_type: Vector type to search (research/papers)

        Returns:
            Tuple of (list of talent dicts with similarity_score, total count)
        """
        # Convert embedding to PostgreSQL vector format with validation
        vector_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

        # Security: Validate vector string contains only valid characters
        # This prevents potential SQL injection through the vector parameter
        if not re.match(r"^[\d\.\-\,\s\[\]eE+]+$", vector_str):
            raise ValueError("Invalid vector format: contains disallowed characters")

        distance_threshold = 1.0 - similarity_threshold

        # Build filter clauses
        filter_clauses = ["e.vector_type = :vector_type"]
        filter_params: dict[str, Any] = {"vector_type": vector_type}
        join_clauses: list[str] = []

        if filters:
            # Use shared filter builder for consistency (handles school_id OR across 3 FK columns,
            # role_type, min_citations, country_code with JOINs, tech_domain_id with EXISTS)
            self._build_jd_filters(filters, filter_clauses, filter_params, join_clauses)

        filter_sql = " AND " + " AND ".join(filter_clauses)
        join_sql = "\n".join(join_clauses)

        # Count query - Safe: vector_str validated by regex, filter_sql uses whitelisted fields
        count_query_str = f"""
            SELECT COUNT(*) as total
            FROM core_talent t
            {join_sql}
            INNER JOIN core_talent_embedding e ON t.talent_id = e.talent_id
            WHERE t.is_visible = TRUE
            AND e.embedding <=> '{vector_str}'::vector <= :distance_threshold
            {filter_sql}
        """
        filter_params["distance_threshold"] = distance_threshold
        count_result = await self.session.execute(text(count_query_str), filter_params)
        total = count_result.scalar() or 0

        # Data query - Safe: vector_str validated by regex, filter_sql uses whitelisted fields
        data_query_str = f"""
            SELECT t.talent_id, t.name, t.name_en, t.current_title, t.school_id,
                   t.role_type, t.topic_tags, t.openalex_topics,
                   t.works_count, t.cited_by_count, t.h_index, t.orcid,
                   s.school_name,
                   es.school_name AS education_school_name,
                   cs.school_name AS company_school_name,
                   e.embedding <=> '{vector_str}'::vector AS distance
            FROM core_talent t
            {join_sql}
            LEFT JOIN core_school s ON t.school_id = s.school_id
            LEFT JOIN core_school es ON t.education_school_id = es.school_id
            LEFT JOIN core_school cs ON t.company_school_id = cs.school_id
            INNER JOIN core_talent_embedding e ON t.talent_id = e.talent_id
            WHERE t.is_visible = TRUE
            AND e.embedding <=> '{vector_str}'::vector <= :distance_threshold
            {filter_sql}
            ORDER BY distance ASC
            LIMIT :limit OFFSET :offset
        """
        filter_params["limit"] = limit
        filter_params["offset"] = offset

        result = await self.session.execute(text(data_query_str), filter_params)
        rows = result.fetchall()

        # Convert to dicts
        items = []
        for row in rows:
            similarity = 1.0 - (row.distance or 0)
            items.append(
                {
                    "talent_id": row.talent_id,
                    "name": row.name,
                    "name_en": row.name_en,
                    "title": row.current_title,
                    "school_id": row.school_id,
                    "school_name": row.school_name,
                    "education_school_name": row.education_school_name,
                    "company_school_name": row.company_school_name,
                    "role_type": row.role_type,
                    "topic_tags": row.topic_tags or [],
                    "openalex_topics": row.openalex_topics or [],
                    "works_count": row.works_count,
                    "cited_by_count": row.cited_by_count,
                    "h_index": row.h_index,
                    "orcid": row.orcid,
                    "similarity_score": similarity,
                }
            )

        return items, total

    def _build_jd_filters(
        self,
        filters: dict[str, Any] | None,
        filter_clauses: list[str],
        params: dict[str, Any],
        join_clauses: list[str],
    ) -> None:
        """Build filter clauses, params, and JOINs for raw SQL JD match queries.

        Mutates filter_clauses, params, and join_clauses in place.
        Handles: school_id, role_type, min_citations, country_code, tech_domain_id.
        """
        if not filters:
            return

        if "school_id" in filters:
            filter_clauses.append(
                "(t.school_id = :school_id OR t.education_school_id = :school_id "
                "OR t.company_school_id = :school_id)"
            )
            params["school_id"] = filters["school_id"]

        if "role_type" in filters:
            filter_clauses.append("t.role_type = :role_type")
            params["role_type"] = filters["role_type"]

        if "min_citations" in filters:
            filter_clauses.append("t.cited_by_count >= :min_citations")
            params["min_citations"] = filters["min_citations"]

        if "country_code" in filters:
            join_clauses.append("LEFT JOIN core_school s ON t.school_id = s.school_id")
            join_clauses.append("LEFT JOIN core_school es ON t.education_school_id = es.school_id")
            join_clauses.append("LEFT JOIN core_school cs ON t.company_school_id = cs.school_id")
            filter_clauses.append(
                "(s.country_code = :country_code OR es.country_code = :country_code "
                "OR cs.country_code = :country_code)"
            )
            params["country_code"] = filters["country_code"].upper()

        if "tech_domain_id" in filters:
            filter_clauses.append(
                "EXISTS ("
                "SELECT 1 FROM core_talent_tech_tag tt "
                "WHERE tt.talent_id = t.talent_id "
                "AND tt.tech_domain_id = :tech_domain_id "
                "AND tt.is_enabled = TRUE"
                ")"
            )
            params["tech_domain_id"] = filters["tech_domain_id"]
