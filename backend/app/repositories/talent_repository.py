"""
Repository for talent operations.
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy import func, or_, select, text, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.models.school import School
from app.models.talent import RoleProfile, SelectedWork, Talent, TalentTechTag
from app.models.raw_data import RawWork
from app.models.standardized import StdAuthor
from app.models.tech_domain import TechDirection, TechDomain
from app.schemas.filters import TalentFilterParams, PaginationParams

logger = logging.getLogger(__name__)


class TalentRepository:
    """Repository for Talent queries."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_list(
        self,
        school_id: int | None = None,
        country_code: str | None = None,
        role_type: str | None = None,
        min_works: int | None = None,
        min_citations: int | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
        visible_only: bool = True,
    ) -> tuple[list[Talent], int]:
        """
        Get paginated list of talents with filters.

        This method supports both individual parameters (for backward compatibility)
        and can be called with TalentFilterParams.

        Args:
            school_id: Filter by school ID
            country_code: Filter by country code (via school)
            role_type: Filter by role type
            min_works: Minimum works count
            min_citations: Minimum citation count
            keyword: Search keyword for name/title
            page: Page number (1-based)
            page_size: Items per page
            visible_only: If True, only return visible talents

        Returns:
            Tuple of (list of talents, total count)
        """
        # Create filter params from individual args
        filters = TalentFilterParams(
            school_id=school_id,
            country_code=country_code,
            role_type=role_type,
            min_works=min_works,
            min_citations=min_citations,
            keyword=keyword,
            visible_only=visible_only,
        )
        pagination = PaginationParams(page=page, page_size=page_size)

        return await self.get_list_with_params(filters, pagination)

    async def get_list_with_params(
        self,
        filters: TalentFilterParams,
        pagination: PaginationParams,
    ) -> tuple[list[Talent], int]:
        """
        Get paginated list of talents with filter params object.

        Args:
            filters: TalentFilterParams object
            pagination: PaginationParams object

        Returns:
            Tuple of (list of talents, total count)
        """
        query = (
            select(Talent)
            .options(
                selectinload(Talent.school),
                selectinload(Talent.education_school),
                selectinload(Talent.company_school),
            )
            .order_by(Talent.cited_by_count.desc())
        )

        # Apply filters using helper
        query = self._apply_talent_filters(query, filters)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        query = query.offset(pagination.offset).limit(pagination.page_size)

        result = await self.session.execute(query)
        talents = list(result.scalars().all())

        return talents, total

    def _apply_talent_filters(self, query, filters: TalentFilterParams):
        """Apply TalentFilterParams to a query. Reusable across methods."""
        if filters.visible_only:
            query = query.where(Talent.is_visible.is_(True))

        if filters.school_id:
            # Filter by school_id using OR logic (matches education or company institution)
            query = query.where(
                or_(
                    Talent.school_id == filters.school_id,
                    Talent.education_school_id == filters.school_id,
                    Talent.company_school_id == filters.school_id,
                )
            )

        if filters.country_code:
            # Join with explicit condition due to multiple FKs between Talent and School
            query = query.join(School, Talent.school_id == School.school_id).where(
                School.country_code == filters.country_code.upper()
            )

        if filters.role_type:
            query = query.where(Talent.role_type == filters.role_type)

        if filters.min_works is not None:
            query = query.where(Talent.works_count >= filters.min_works)

        if filters.min_citations is not None:
            query = query.where(Talent.cited_by_count >= filters.min_citations)

        if filters.keyword:
            keyword_pattern = f"%{filters.keyword}%"
            query = query.where(
                or_(
                    Talent.name.ilike(keyword_pattern),
                    Talent.name_en.ilike(keyword_pattern),
                    Talent.current_title.ilike(keyword_pattern),
                )
            )

        return query

    async def get_list_by_cursor(
        self,
        cursor: int | None = None,
        page_size: int = 20,
        school_id: int | None = None,
        country_code: str | None = None,
        role_type: str | None = None,
        min_works: int | None = None,
        min_citations: int | None = None,
        keyword: str | None = None,
        visible_only: bool = True,
    ) -> tuple[list[Talent], int | None]:
        """
        Get talents using cursor-based pagination (efficient for deep pagination).

        Cursor-based pagination uses talent_id as the cursor, which is much more
        efficient than OFFSET for large datasets.

        Args:
            cursor: Last talent_id from previous page (None for first page)
            page_size: Items per page
            school_id: Filter by school ID
            country_code: Filter by country code
            role_type: Filter by role type
            min_works: Minimum works count
            min_citations: Minimum citation count
            keyword: Search keyword
            visible_only: If True, only return visible talents

        Returns:
            Tuple of (list of talents, next_cursor or None if no more pages)
        """
        # Create filter params from args
        filters = TalentFilterParams(
            school_id=school_id,
            country_code=country_code,
            role_type=role_type,
            min_works=min_works,
            min_citations=min_citations,
            keyword=keyword,
            visible_only=visible_only,
        )

        return await self.get_list_by_cursor_with_params(cursor, page_size, filters)

    async def get_list_by_cursor_with_params(
        self,
        cursor: int | None,
        page_size: int,
        filters: TalentFilterParams,
    ) -> tuple[list[Talent], int | None]:
        """Cursor pagination with filter params object."""
        query = (
            select(Talent)
            .options(
                selectinload(Talent.school),
                selectinload(Talent.education_school),
                selectinload(Talent.company_school),
            )
            .order_by(Talent.talent_id.desc())
        )

        # Apply cursor filter
        if cursor is not None:
            query = query.where(Talent.talent_id < cursor)

        # Apply filters using helper
        query = self._apply_talent_filters(query, filters)

        # Fetch one extra to determine if there's a next page
        query = query.limit(page_size + 1)

        result = await self.session.execute(query)
        talents = list(result.scalars().all())

        # Determine next cursor
        next_cursor = None
        if len(talents) > page_size:
            talents = talents[:page_size]
            next_cursor = talents[-1].talent_id

        return talents, next_cursor

    async def get_by_id(
        self, talent_id: int, include_relations: bool = True
    ) -> Talent | None:
        """
        Get talent by ID.

        Args:
            talent_id: Talent ID
            include_relations: If True, load school and role_profile

        Returns:
            Talent instance or None
        """
        query = select(Talent).where(Talent.talent_id == talent_id)

        if include_relations:
            query = query.options(
                selectinload(Talent.school),
                selectinload(Talent.education_school),
                selectinload(Talent.company_school),
                selectinload(Talent.role_profile),
                selectinload(Talent.selected_works),
            )

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_talent_tech_tags(self, talent_id: int) -> list[tuple]:
        """
        Get tech tags for a talent with domain and direction info.

        Args:
            talent_id: Talent ID

        Returns:
            List of tuples (TalentTechTag, TechDomain, TechDirection)
        """
        result = await self.session.execute(
            select(TalentTechTag, TechDomain, TechDirection)
            .join(TechDomain, TalentTechTag.tech_domain_id == TechDomain.tech_domain_id)
            .outerjoin(TechDirection, TalentTechTag.tech_direction_id == TechDirection.tech_direction_id)
            .where(TalentTechTag.talent_id == talent_id)
        )
        return result.fetchall()

    async def get_by_source_id(self, source_record_id: str) -> Talent | None:
        """
        Get talent by source record ID (e.g., OpenAlex ID).

        Args:
            source_record_id: Source record ID

        Returns:
            Talent instance or None
        """
        result = await self.session.execute(
            select(Talent).where(Talent.source_record_id == source_record_id)
        )
        return result.scalar_one_or_none()

    async def get_by_orcid(self, orcid: str) -> Talent | None:
        """
        Get talent by ORCID.

        Args:
            orcid: ORCID identifier

        Returns:
            Talent instance or None
        """
        result = await self.session.execute(
            select(Talent).where(Talent.orcid == orcid)
        )
        return result.scalar_one_or_none()

    async def get_role_profile(self, talent_id: int) -> RoleProfile | None:
        """
        Get role profile for a talent.

        Args:
            talent_id: Talent ID

        Returns:
            RoleProfile instance or None
        """
        result = await self.session.execute(
            select(RoleProfile).where(RoleProfile.talent_id == talent_id)
        )
        return result.scalar_one_or_none()

    async def get_selected_works(
        self, talent_id: int, limit: int = 10
    ) -> list[SelectedWork]:
        """
        Get selected works for a talent.

        Args:
            talent_id: Talent ID
            limit: Maximum number of works to return

        Returns:
            List of SelectedWork instances
        """
        result = await self.session.execute(
            select(SelectedWork)
            .where(SelectedWork.talent_id == talent_id)
            .order_by(SelectedWork.display_order, SelectedWork.citation_count.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search(
        self,
        keyword: str,
        limit: int = 20,
        role_type: str | None = None,
    ) -> list[Talent]:
        """
        Search talents by keyword.

        Args:
            keyword: Search keyword
            limit: Maximum number of results
            role_type: Optional role type filter

        Returns:
            List of matching talents
        """
        keyword_pattern = f"%{keyword}%"

        query = (
            select(Talent)
            .options(selectinload(Talent.school))
            .where(
                Talent.is_visible.is_(True),
                or_(
                    Talent.name.ilike(keyword_pattern),
                    Talent.name_en.ilike(keyword_pattern),
                    Talent.current_title.ilike(keyword_pattern),
                ),
            )
            .order_by(Talent.cited_by_count.desc())
            .limit(limit)
        )

        if role_type:
            query = query.where(Talent.role_type == role_type)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_count_by_role(
        self, school_id: int | None = None
    ) -> dict[str, int]:
        """
        Get talent counts grouped by role type.

        Args:
            school_id: Optional school to filter by

        Returns:
            Dictionary with counts by role type
        """
        query = select(
            Talent.role_type,
            func.count(Talent.talent_id).label("count")
        ).where(Talent.is_visible.is_(True))

        if school_id:
            query = query.where(Talent.school_id == school_id)

        query = query.group_by(Talent.role_type)

        result = await self.session.execute(query)
        counts = {"professor": 0, "student": 0, "graduated": 0, "unknown": 0, "total": 0}

        for row in result.all():
            counts[row.role_type] = row.count
            counts["total"] += row.count

        return counts

    async def get_count_by_school(
        self, country_code: str | None = None
    ) -> dict[int, int]:
        """
        Get talent counts grouped by school.

        Args:
            country_code: Optional country code to filter schools by

        Returns:
            Dictionary mapping school_id to count
        """
        query = select(
            Talent.school_id,
            func.count(Talent.talent_id).label("count")
        ).where(
            Talent.is_visible.is_(True),
            Talent.school_id.isnot(None),
        )

        if country_code:
            query = query.join(School).where(School.country_code == country_code.upper())

        query = query.group_by(Talent.school_id)

        result = await self.session.execute(query)
        return {row.school_id: row.count for row in result.all()}

    # ========================================
    # New Search Methods for Service Layer Refactoring
    # ========================================

    async def get_by_ids(
        self,
        talent_ids: List[int],
        include_relations: bool = True,
        batch_size: int = 5000,
    ) -> List[Talent]:
        """
        Get multiple talents by IDs with batch processing.

        Uses batch processing to avoid PostgreSQL parameter limit (32767).

        Args:
            talent_ids: List of talent IDs to fetch
            include_relations: If True, load school relationship
            batch_size: Number of IDs per batch (default 5000)

        Returns:
            List of Talent instances
        """
        if not talent_ids:
            return []

        all_talents = []

        for i in range(0, len(talent_ids), batch_size):
            batch_ids = talent_ids[i:i + batch_size]
            query = select(Talent).where(Talent.talent_id.in_(batch_ids))

            if include_relations:
                query = query.options(selectinload(Talent.school))

            result = await self.session.execute(query)
            all_talents.extend(result.scalars().all())

        return all_talents

    async def search_by_json_field(
        self,
        field_name: str,
        keywords: List[str],
        match_mode: str = "any",
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[Talent], int]:
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
        if not keywords:
            return [], 0

        # Build base query
        query = (
            select(Talent)
            .options(selectinload(Talent.school))
            .where(Talent.is_visible.is_(True))
        )

        # Build JSON field search conditions
        conditions = []
        for keyword in keywords:
            pattern = f"%{keyword}%"
            conditions.append(
                text(f"core_talent.{field_name}::text ILIKE :pattern_{hash(keyword) % 10000}").bindparams(
                    **{f"pattern_{hash(keyword) % 10000}": pattern}
                )
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
        query_embedding: List[float],
        similarity_threshold: float = 0.7,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20,
        offset: int = 0,
        vector_type: str = "research",
    ) -> Tuple[List[Dict[str, Any]], int]:
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
        vector_str = '[' + ','.join(str(v) for v in query_embedding) + ']'

        # Security: Validate vector string contains only valid characters
        # This prevents potential SQL injection through the vector parameter
        import re
        if not re.match(r'^[\d\.\-\,\s\[\]eE+]+$', vector_str):
            raise ValueError("Invalid vector format: contains disallowed characters")

        distance_threshold = 1.0 - similarity_threshold

        # Build filter clauses
        filter_clauses = ["e.vector_type = :vector_type"]
        filter_params: Dict[str, Any] = {"vector_type": vector_type}

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

        # Count query
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

        # Data query
        data_query_str = f"""
            SELECT t.talent_id, t.name, t.name_en, t.current_title, t.school_id,
                   t.role_type, t.topic_tags, t.openalex_topics,
                   t.works_count, t.cited_by_count, t.h_index, t.orcid,
                   s.school_name,
                   e.embedding <=> '{vector_str}'::vector AS distance
            FROM core_talent t
            LEFT JOIN core_school s ON t.school_id = s.school_id
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
            items.append({
                "talent_id": row.talent_id,
                "name": row.name,
                "name_en": row.name_en,
                "title": row.current_title,
                "school_id": row.school_id,
                "school_name": row.school_name,
                "role_type": row.role_type,
                "topic_tags": row.topic_tags or [],
                "openalex_topics": row.openalex_topics or [],
                "works_count": row.works_count,
                "cited_by_count": row.cited_by_count,
                "h_index": row.h_index,
                "orcid": row.orcid,
                "similarity_score": similarity,
            })

        return items, total

    async def get_paper_titles_for_talents(
        self,
        talent_ids: List[int],
        limit_per_talent: int = 20,
    ) -> Dict[int, List[str]]:
        """
        Batch get paper titles for multiple talents.

        Fixes N+1 query problem by using a single query instead of
        one query per talent.

        Data path: Talent.std_author_id → StdAuthor.openalex_author_id → RawWork.author_ids

        Args:
            talent_ids: List of talent IDs
            limit_per_talent: Maximum papers per talent

        Returns:
            Dict mapping talent_id to list of paper titles
        """
        if not talent_ids:
            return {}

        # Batch size for PostgreSQL parameter limit
        BATCH_SIZE = 5000
        result: Dict[int, List[str]] = {tid: [] for tid in talent_ids}

        for i in range(0, len(talent_ids), BATCH_SIZE):
            batch_ids = talent_ids[i:i + BATCH_SIZE]

            # Step 1: Get std_author_id → openalex_author_id mapping
            author_query = (
                select(Talent.talent_id, StdAuthor.openalex_author_id)
                .join(StdAuthor, Talent.std_author_id == StdAuthor.std_author_id)
                .where(Talent.talent_id.in_(batch_ids))
                .where(StdAuthor.openalex_author_id.isnot(None))
            )
            author_result = await self.session.execute(author_query)
            talent_to_openalex = {
                row.talent_id: row.openalex_author_id
                for row in author_result.all()
            }

            if not talent_to_openalex:
                continue

            # Step 2: Batch query paper titles
            openalex_ids = list(talent_to_openalex.values())

            # Build OR conditions for author_ids search
            # author_ids is stored as JSON text, use LIKE pattern matching
            conditions = []
            for oid in openalex_ids:
                conditions.append(RawWork.author_ids.ilike(f'%"{oid}"%'))

            paper_query = (
                select(RawWork.author_ids, RawWork.title)
                .where(or_(*conditions))
                .limit(len(openalex_ids) * limit_per_talent)
            )
            paper_result = await self.session.execute(paper_query)

            # Step 3: Map papers back to talents
            for row in paper_result.all():
                if not row.title:
                    continue
                # Find which talent this paper belongs to
                for talent_id, openalex_id in talent_to_openalex.items():
                    if openalex_id and f'"{openalex_id}"' in (row.author_ids or ""):
                        if len(result[talent_id]) < limit_per_talent:
                            result[talent_id].append(row.title)
                        break  # Each paper maps to one talent in our query

        return result

    async def search_by_paper_titles(
        self,
        keywords: List[str],
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ) -> List[Talent]:
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
        params: Dict[str, Any] = {f"kw_{i}": f"%{kw}%" for i, kw in enumerate(keywords)}

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
        talent_ids = [row.talent_id for row in rows if hasattr(row, 'talent_id')]

        if not talent_ids:
            return []

        # Fetch full Talent objects with relationships
        talents = await self.get_by_ids(talent_ids, include_relations=True)

        return talents[:limit]

    async def search_by_research_keywords(
        self,
        keywords: List[str],
        search_scope: List[str] = ["openalex_topics", "paper_titles"],
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
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
        if not keywords:
            return []

        talents: List[Talent] = []
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

            candidates.append({
                "talent": talent,
                "paper_titles": paper_titles,
                "openalex_topics": openalex_topics,
                "matched_keywords": matched_keywords,
            })

        return candidates[:limit]

    def _apply_search_filters(self, query, filters: Optional[Dict[str, Any]]):
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
            from app.models.school import School
            # 子查询：获取指定国家的学校 ID 列表
            school_subquery = (
                select(School.school_id)
                .where(School.country_code == filters["country_code"].upper())
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
            from app.models.tech_domain import TalentTechTag
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
        keywords: List[str],
        match_mode: str = "exact",
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ) -> List[Talent]:
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
        import json

        if not keywords:
            return []

        # Build filter clauses for raw SQL
        filter_clauses = ["t.is_visible = TRUE"]
        params: Dict[str, Any] = {}

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
            for i, kw in enumerate(keywords):
                # Safely escape the keyword for JSON
                escaped_kw = json.dumps(kw)
                conditions.append(f"t.openalex_topics::jsonb @> '[{escaped_kw}]'::jsonb")

            conditions_sql = " OR ".join(conditions)
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
        talent_ids = [row.talent_id for row in rows if hasattr(row, 'talent_id')]
        if not talent_ids:
            return []

        return await self.get_by_ids(talent_ids, include_relations=True)

    async def _search_by_paper_titles_gin(
        self,
        keywords: List[str],
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ) -> List[Talent]:
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
        params: Dict[str, Any] = {f"kw_{i}": f"%{kw}%" for i, kw in enumerate(keywords)}

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
        keywords: List[str],
        talent: Talent,
        paper_titles: List[str] = None,
    ) -> List[str]:
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
            [t.lower() for t in (talent.openalex_topics or [])] +
            [t.lower() for t in (paper_titles or [])]
        )
        for keyword in keywords:
            if keyword.lower() in all_text:
                matched.add(keyword)
        return list(matched)
