"""Talent keyword search mixin: ILIKE keyword search and JSON-field search.

Split from talent_search_repository.py; mixed into TalentSearchRepository via
the inheritance chain (TalentKeywordSearchMixin -> TalentVectorSearchMixin ->
TalentGinSearchMixin -> TalentSearchRepository).
"""

# ruff: noqa: S608

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.orm import selectinload

from app.domains.academic.models.talent import Talent

from .talent_export_repository import TalentExportRepository

logger = logging.getLogger(__name__)


class TalentKeywordSearchMixin(TalentExportRepository):
    """Keyword-based talent search (name/title ILIKE, JSON fields, paper titles)."""

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
