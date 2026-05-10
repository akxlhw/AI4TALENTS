"""Talent search repository with advanced search and filtering operations."""

# ruff: noqa: S608

from __future__ import annotations

import json
import logging
import re
from typing import Any

from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.orm import selectinload

from app.domains.academic.models.talent import Talent

from .talent_export_repository import TalentExportRepository

logger = logging.getLogger(__name__)


class TalentSearchRepository(TalentExportRepository):
    """Repository for advanced talent search and filtering."""

    async def search(
        self,
        keyword: str,
        limit: int = 20,
        offset: int = 0,
        role_type: str | None = None,
    ) -> list[Talent]:
        """
        Search talents by keyword.

        Args:
            keyword: Search keyword
            limit: Maximum number of results
            offset: Result offset for pagination
            role_type: Optional role type filter

        Returns:
            List of matching talents
        """
        keyword_pattern = f"%{keyword}%"

        query = (
            select(Talent)
            .options(
                selectinload(Talent.school),
                selectinload(Talent.education_school),
                selectinload(Talent.company_school),
            )
            .where(
                Talent.is_visible.is_(True),
                or_(
                    Talent.name.ilike(keyword_pattern),
                    Talent.name_en.ilike(keyword_pattern),
                    Talent.current_title.ilike(keyword_pattern),
                ),
            )
            .order_by(Talent.cited_by_count.desc())
            .offset(offset)
            .limit(limit)
        )

        if role_type:
            query = query.where(Talent.role_type == role_type)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def search_count(
        self,
        keyword: str,
        role_type: str | None = None,
    ) -> int:
        """
        Get total count of talents matching search criteria.

        Args:
            keyword: Search keyword
            role_type: Optional role type filter

        Returns:
            Total matching count
        """
        keyword_pattern = f"%{keyword}%"

        query = select(func.count(Talent.talent_id)).where(
            Talent.is_visible.is_(True),
            or_(
                Talent.name.ilike(keyword_pattern),
                Talent.name_en.ilike(keyword_pattern),
                Talent.current_title.ilike(keyword_pattern),
            ),
        )

        if role_type:
            query = query.where(Talent.role_type == role_type)

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def search_by_json_field(
        self,
        field_name: str,
        keywords: list[str],
        match_mode: str = "any",
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Talent], int]:
        """
        Search talents by JSON array field (openalex_topics or topic_tags).

        Args:
            field_name: JSON field to search ("openalex_topics" or "topic_tags")
            keywords: List of keywords to match
            match_mode: "any" for OR match, "all" for AND match
            filters: Additional filters (school_id, role_type, min_citations, etc.)
            limit: Maximum results
            offset: Result offset for pagination

        Returns:
            Tuple of (list of talents, total count)
        """
        # Whitelist for JSON field names to prevent SQL injection
        allowed_fields = {"openalex_topics", "topic_tags"}
        if field_name not in allowed_fields:
            raise ValueError(f"Invalid field_name: {field_name}. Allowed: {allowed_fields}")

        if not keywords:
            return [], 0

        # Build base query
        query = (
            select(Talent).options(selectinload(Talent.school)).where(Talent.is_visible.is_(True))
        )

        # Build JSON field search conditions
        conditions = []
        for keyword in keywords:
            pattern = f"%{keyword}%"
            conditions.append(
                text(
                    f"core_talent.{field_name}::text ILIKE :pattern_{hash(keyword) % 10000}"
                ).bindparams(**{f"pattern_{hash(keyword) % 10000}": pattern})
            )

        if match_mode == "any":
            query = query.where(or_(*conditions))
        else:  # all
            query = query.where(and_(*conditions))

        # Apply filters
        query = self._apply_search_filters(query, filters)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        query = query.order_by(Talent.cited_by_count.desc()).offset(offset).limit(limit)

        result = await self.session.execute(query)
        talents = list(result.scalars().all())

        return talents, total

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

        if filters:
            if "school_id" in filters:
                filter_clauses.append("t.school_id = :school_id")
                filter_params["school_id"] = filters["school_id"]
            if "role_type" in filters:
                filter_clauses.append("t.role_type = :role_type")
                filter_params["role_type"] = filters["role_type"]
            if "min_citations" in filters:
                filter_clauses.append("t.cited_by_count >= :min_citations")
                filter_params["min_citations"] = filters["min_citations"]

        filter_sql = " AND " + " AND ".join(filter_clauses)

        # Count query - Safe: vector_str validated by regex, filter_sql uses whitelisted fields
        count_query_str = f"""
            SELECT COUNT(*) as total
            FROM core_talent t
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

    async def search_by_paper_titles(
        self,
        keywords: list[str],
        filters: dict[str, Any] | None = None,
        limit: int = 100,
    ) -> list[Talent]:
        """
        Search talents by their paper titles.

        Data path: RawWork.title → RawWork.author_ids → StdAuthor.openalex_author_id → Talent

        Args:
            keywords: List of keywords to search in paper titles
            filters: Additional filters
            limit: Maximum results

        Returns:
            List of matching Talent instances
        """
        if not keywords:
            return []

        # Use raw SQL for the complex join
        conditions_sql = " OR ".join([f"rw.title ILIKE :kw_{i}" for i in range(len(keywords))])
        params: dict[str, Any] = {f"kw_{i}": f"%{kw}%" for i, kw in enumerate(keywords)}

        # Safe: conditions_sql uses parameterized placeholders, filters use whitelisted fields
        query_str = f"""
            SELECT DISTINCT t.*
            FROM core_talent t
            INNER JOIN std_author sa ON sa.std_author_id = t.std_author_id
            INNER JOIN raw_work rw ON rw.author_ids ILIKE '%' || sa.openalex_author_id || '%'
            WHERE t.is_visible = TRUE
            AND ({conditions_sql})
        """

        # Add filter clauses
        if filters:
            if "school_id" in filters:
                query_str += " AND t.school_id = :school_id"
                params["school_id"] = filters["school_id"]
            if "role_type" in filters:
                query_str += " AND t.role_type = :role_type"
                params["role_type"] = filters["role_type"]

        query_str += " LIMIT :limit"
        params["limit"] = limit

        result = await self.session.execute(text(query_str), params)
        rows = result.fetchall()

        # Get talent IDs from result
        talent_ids = [row.talent_id for row in rows if hasattr(row, "talent_id")]

        if not talent_ids:
            return []

        # Fetch full Talent objects with relationships
        talents = await self.get_by_ids(talent_ids, include_relations=True)

        return talents[:limit]

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

    def _apply_search_filters(self, query, filters: dict[str, Any] | None):
        """Apply common filters to a query."""
        if not filters:
            return query

        if "school_id" in filters:
            # Filter by school_id using OR logic (matches education or company institution)
            query = query.where(
                or_(
                    Talent.school_id == filters["school_id"],
                    Talent.education_school_id == filters["school_id"],
                    Talent.company_school_id == filters["school_id"],
                )
            )

        if "role_type" in filters:
            query = query.where(Talent.role_type == filters["role_type"])

        if "min_citations" in filters:
            query = query.where(Talent.cited_by_count >= filters["min_citations"])

        if "min_works" in filters:
            query = query.where(Talent.works_count >= filters["min_works"])

        if "school_ids" in filters:
            # Filter by school_ids using OR logic (matches education or company institution)
            query = query.where(
                or_(
                    Talent.school_id.in_(filters["school_ids"]),
                    Talent.education_school_id.in_(filters["school_ids"]),
                    Talent.company_school_id.in_(filters["school_ids"]),
                )
            )

        if "exclude_ids" in filters:
            query = query.where(~Talent.talent_id.in_(filters["exclude_ids"]))

        # 按国家筛选（需要 JOIN School 表）
        # 使用子查询避免 JOIN 重复问题
        if "country_code" in filters:
            from app.domains.academic.models.school import School

            # 子查询：获取指定国家的学校 ID 列表
            school_subquery = select(School.school_id).where(
                School.country_code == filters["country_code"].upper()
            )
            # Filter by country using OR logic (matches education or company institution)
            query = query.where(
                or_(
                    Talent.school_id.in_(school_subquery),
                    Talent.education_school_id.in_(school_subquery),
                    Talent.company_school_id.in_(school_subquery),
                )
            )

        # 按技术领域筛选（通过 TalentTechTag 关联）
        if "tech_domain_id" in filters:
            from app.domains.academic.models.tech_domain import TalentTechTag

            # 子查询：获取属于指定技术领域的人才 ID
            subquery = (
                select(TalentTechTag.talent_id)
                .where(TalentTechTag.tech_domain_id == filters["tech_domain_id"])
                .where(TalentTechTag.is_enabled.is_(True))
                .distinct()
            )
            query = query.where(Talent.talent_id.in_(subquery))

        return query

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

        # Build filter clauses for raw SQL
        filter_clauses = ["t.is_visible = TRUE"]
        params: dict[str, Any] = {}

        if filters:
            if "school_id" in filters:
                filter_clauses.append("t.school_id = :school_id")
                params["school_id"] = filters["school_id"]
            if "role_type" in filters:
                filter_clauses.append("t.role_type = :role_type")
                params["role_type"] = filters["role_type"]
            if "min_citations" in filters:
                filter_clauses.append("t.cited_by_count >= :min_citations")
                params["min_citations"] = filters["min_citations"]

        filter_sql = " AND ".join(filter_clauses)

        if match_mode == "exact":
            # Precise match: uses GIN index with @> operator
            # Build OR conditions with safely escaped JSON values
            conditions = []
            for _i, kw in enumerate(keywords):
                # Safely escape the keyword for JSON
                escaped_kw = json.dumps(kw)
                conditions.append(f"t.openalex_topics::jsonb @> '[{escaped_kw}]'::jsonb")

            conditions_sql = " OR ".join(conditions)
            # Safe: escaped_kw uses json.dumps for proper escaping, filter_sql uses whitelisted fields
            query_str = f"""
                SELECT t.*
                FROM core_talent t
                WHERE {filter_sql}
                AND ({conditions_sql})
                ORDER BY t.cited_by_count DESC
                LIMIT :limit
            """
        else:
            # Fuzzy match: uses pg_trgm GIN index on openalex_topics::text
            # This supports ILIKE substring matching with index acceleration
            keyword_conditions = []
            for i, kw in enumerate(keywords):
                keyword_conditions.append(f"t.openalex_topics::text ILIKE :pattern_{i}")
                params[f"pattern_{i}"] = f"%{kw}%"

            conditions_sql = " OR ".join(keyword_conditions)
            # Safe: conditions_sql uses parameterized placeholders, filter_sql uses whitelisted fields
            query_str = f"""
                SELECT t.*
                FROM core_talent t
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

        # Build filter clauses
        filter_clauses = []
        if filters:
            if "school_id" in filters:
                filter_clauses.append("t.school_id = :school_id")
                params["school_id"] = filters["school_id"]
            if "role_type" in filters:
                filter_clauses.append("t.role_type = :role_type")
                params["role_type"] = filters["role_type"]

        filter_sql = " AND " + " AND ".join(filter_clauses) if filter_clauses else ""

        # Safe: keyword_conditions uses parameterized placeholders, filter_sql uses whitelisted fields
        query_str = f"""
            SELECT DISTINCT t.talent_id
            FROM core_talent t
            INNER JOIN std_author sa ON sa.std_author_id = t.std_author_id
            INNER JOIN raw_work rw ON (
                rw.author_ids::jsonb ? sa.openalex_author_id
                OR rw.author_ids::text LIKE '%' || sa.openalex_author_id || '%'
            )
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
