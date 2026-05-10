"""
Technology Domain Repository.
技术领域数据访问层

Security Note (S608):
This module uses raw SQL with f-strings for complex queries. All such queries are safe because:
- User inputs use parameterized placeholders (:param_name)
- Field names in WHERE clauses are from a whitelist
"""

# ruff: noqa: S608

from __future__ import annotations

from sqlalchemy import and_, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.academic.models.school import School
from app.domains.academic.models.talent import Talent
from app.domains.academic.models.tech_domain import TalentTechTag, TechDirection, TechDomain


class TechDomainRepository:
    """Repository for tech domain operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_domains(self) -> list[TechDomain]:
        """Get all enabled tech domains with directions."""
        result = await self.session.execute(
            select(TechDomain)
            .where(TechDomain.is_enabled.is_(True))
            .options(selectinload(TechDomain.directions))
            .order_by(TechDomain.sort_order, TechDomain.tech_domain_id)
        )
        return list(result.scalars().all())

    async def get_domain_by_id(self, domain_id: int) -> TechDomain | None:
        """Get tech domain by ID."""
        result = await self.session.execute(
            select(TechDomain)
            .where(TechDomain.tech_domain_id == domain_id)
            .options(selectinload(TechDomain.directions))
        )
        return result.scalar_one_or_none()

    async def get_directions_by_domain(self, domain_id: int) -> list[TechDirection]:
        """Get all directions for a tech domain."""
        result = await self.session.execute(
            select(TechDirection)
            .where(
                and_(TechDirection.tech_domain_id == domain_id, TechDirection.is_enabled.is_(True))
            )
            .order_by(TechDirection.sort_order, TechDirection.tech_direction_id)
        )
        return list(result.scalars().all())

    async def get_domain_stats(self, domain_id: int | None = None) -> dict:
        """Get statistics for tech domain(s).

        Uses a single CTE query for efficiency.
        """
        if domain_id:
            cte_query = text(
                """
                WITH domain_tags AS (
                    SELECT DISTINCT ttt.talent_id, ttt.tech_direction_id,
                           t.role_type, t.school_id
                    FROM core_talent_tech_tag ttt
                    INNER JOIN core_talent t ON ttt.talent_id = t.talent_id
                    WHERE ttt.tech_domain_id = :domain_id
                )
                SELECT
                    (SELECT COUNT(DISTINCT talent_id) FROM domain_tags) AS talent_count,
                    (SELECT COUNT(DISTINCT talent_id) FROM domain_tags
                     WHERE role_type = 'professor') AS professor_count,
                    (SELECT COUNT(DISTINCT talent_id) FROM domain_tags
                     WHERE role_type IN ('student', 'graduated')) AS student_count,
                    (SELECT COUNT(DISTINCT tech_direction_id) FROM domain_tags) AS direction_count,
                    (SELECT COUNT(DISTINCT s.country_code)
                     FROM domain_tags et
                     INNER JOIN core_school s ON et.school_id = s.school_id
                     WHERE s.country_code IS NOT NULL) AS country_count,
                    (SELECT COUNT(DISTINCT s.school_id)
                     FROM domain_tags et
                     INNER JOIN core_school s ON et.school_id = s.school_id) AS school_count
            """
            )

            result = await self.session.execute(cte_query, {"domain_id": domain_id})
            row = result.one()

            return {
                "talent_count": row.talent_count or 0,
                "professor_count": row.professor_count or 0,
                "student_count": row.student_count or 0,
                "direction_count": row.direction_count or 0,
                "country_count": row.country_count or 0,
                "school_count": row.school_count or 0,
            }
        else:
            # Global stats
            domains_count = await self.session.execute(
                select(func.count(TechDomain.tech_domain_id)).where(TechDomain.is_enabled.is_(True))
            )
            directions_count = await self.session.execute(
                select(func.count(TechDirection.tech_direction_id)).where(
                    TechDirection.is_enabled.is_(True)
                )
            )
            talents_count = await self.session.execute(
                select(func.count(func.distinct(TalentTechTag.talent_id)))
            )

            return {
                "domain_count": domains_count.scalar() or 0,
                "direction_count": directions_count.scalar() or 0,
                "talent_count": talents_count.scalar() or 0,
            }

    async def get_overall_stats(self) -> dict:
        """Get overall statistics for the tech domain page.

        Uses a single CTE query for efficiency.
        """
        cte_query = text(
            """
            WITH enabled_tags AS (
                SELECT DISTINCT ttt.talent_id, ttt.tech_domain_id,
                       ttt.tech_direction_id, t.role_type, t.school_id
                FROM core_talent_tech_tag ttt
                INNER JOIN core_talent t ON ttt.talent_id = t.talent_id
                WHERE ttt.is_enabled = true
            )
            SELECT
                (SELECT COUNT(DISTINCT talent_id) FROM enabled_tags) AS talent_count,
                (SELECT COUNT(DISTINCT talent_id) FROM enabled_tags
                 WHERE role_type = 'professor') AS professor_count,
                (SELECT COUNT(DISTINCT talent_id) FROM enabled_tags
                 WHERE role_type IN ('student', 'graduated')) AS student_count,
                (SELECT COUNT(DISTINCT tech_domain_id) FROM enabled_tags) AS tech_domain_count,
                (SELECT COUNT(DISTINCT tech_direction_id) FROM enabled_tags) AS tech_direction_count,
                (SELECT COUNT(DISTINCT s.country_code)
                 FROM enabled_tags et
                 INNER JOIN core_school s ON et.school_id = s.school_id
                 WHERE s.country_code IS NOT NULL) AS country_count,
                (SELECT COUNT(DISTINCT s.school_id)
                 FROM enabled_tags et
                 INNER JOIN core_school s ON et.school_id = s.school_id) AS school_count
        """
        )

        result = await self.session.execute(cte_query)
        row = result.one()

        return {
            "talent_count": row.talent_count or 0,
            "professor_count": row.professor_count or 0,
            "student_count": row.student_count or 0,
            "country_count": row.country_count or 0,
            "school_count": row.school_count or 0,
            "tech_domain_count": row.tech_domain_count or 0,
            "tech_direction_count": row.tech_direction_count or 0,
        }

    async def get_country_distribution(
        self, domain_id: int | None = None, direction_id: int | None = None
    ) -> list[dict]:
        """Get talent distribution by country."""
        query = (
            select(
                School.country_code,
                School.country_name,
                func.count(func.distinct(Talent.talent_id)).label("talent_count"),
            )
            .select_from(TalentTechTag)
            .join(Talent, TalentTechTag.talent_id == Talent.talent_id)
            .join(School, Talent.school_id == School.school_id)
            .where(
                School.country_code.isnot(None),
            )
            .group_by(School.country_code, School.country_name)
            .order_by(func.count(func.distinct(Talent.talent_id)).desc())
        )

        conditions = [TalentTechTag.is_enabled.is_(True)]
        if domain_id:
            conditions.append(TalentTechTag.tech_domain_id == domain_id)
        if direction_id:
            conditions.append(TalentTechTag.tech_direction_id == direction_id)

        query = query.where(and_(*conditions))

        result = await self.session.execute(query)
        return [
            {
                "country_code": row.country_code,
                "country_name": row.country_name or row.country_code,
                "talent_count": row.talent_count,
            }
            for row in result.all()
        ]

    async def get_school_distribution(
        self,
        domain_id: int | None = None,
        direction_id: int | None = None,
        country_code: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """Get talent distribution by school."""
        # Base query for counting
        count_query = (
            select(func.count(func.distinct(School.school_id)))
            .select_from(TalentTechTag)
            .join(Talent, TalentTechTag.talent_id == Talent.talent_id)
            .join(School, Talent.school_id == School.school_id)
        )

        # Main query
        query = (
            select(
                School.school_id,
                School.school_name,
                School.country_name.label("country_name"),
                func.count(func.distinct(Talent.talent_id)).label("talent_count"),
            )
            .select_from(TalentTechTag)
            .join(Talent, TalentTechTag.talent_id == Talent.talent_id)
            .join(School, Talent.school_id == School.school_id)
            .group_by(School.school_id, School.school_name, School.country_name)
            .order_by(func.count(func.distinct(Talent.talent_id)).desc())
        )

        conditions = [TalentTechTag.is_enabled.is_(True)]
        if domain_id:
            conditions.append(TalentTechTag.tech_domain_id == domain_id)
        if direction_id:
            conditions.append(TalentTechTag.tech_direction_id == direction_id)
        if country_code:
            conditions.append(School.country_code == country_code.upper())

        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))

        # Get total count
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(query)
        items = [
            {
                "school_id": row.school_id,
                "school_name": row.school_name,
                "country_name": row.country_name,
                "talent_count": row.talent_count,
            }
            for row in result.all()
        ]

        return items, total

    async def get_talent_list_by_cursor(
        self,
        domain_id: int | None = None,
        direction_id: int | None = None,
        country_code: str | None = None,
        school_id: int | None = None,
        role_type: str | None = None,
        keyword: str | None = None,
        cursor: int | None = None,
        page_size: int = 20,
    ) -> tuple[list[Talent], int | None]:
        """
        Get talent list with cursor-based pagination (efficient for deep pagination).

        Uses talent_id as cursor for consistent and efficient pagination.

        Args:
            domain_id: Filter by tech domain
            direction_id: Filter by tech direction
            country_code: Filter by country code
            school_id: Filter by school
            role_type: Filter by role type
            keyword: Search keyword
            cursor: Last talent_id from previous page
            page_size: Items per page

        Returns:
            Tuple of (list of talents, next_cursor or None)
        """
        from sqlalchemy import text

        # Build WHERE conditions
        conditions = ["ttt.is_enabled IS TRUE"]
        params = {}

        if cursor is not None:
            conditions.append("t.talent_id < :cursor")
            params["cursor"] = cursor

        if domain_id:
            conditions.append("ttt.tech_domain_id = :domain_id")
            params["domain_id"] = domain_id
        if direction_id:
            conditions.append("ttt.tech_direction_id = :direction_id")
            params["direction_id"] = direction_id
        if school_id:
            conditions.append(
                "(t.education_school_id = :school_id OR t.company_school_id = :school_id OR t.school_id = :school_id)"
            )
            params["school_id"] = school_id
        if country_code:
            conditions.append("s.country_code = :country_code")
            params["country_code"] = country_code.upper()
        if role_type:
            conditions.append("t.role_type = :role_type")
            params["role_type"] = role_type
        if keyword:
            conditions.append("t.name LIKE :keyword")
            params["keyword"] = f"%{keyword}%"

        where_clause = " AND ".join(conditions)

        # Main query with cursor pagination (fetch one extra for next_cursor)
        # Use DISTINCT ON to avoid JSON equality comparison issues in PostgreSQL
        # Priority: education_school -> company_school -> legacy school
        # Safe: where_clause uses only whitelisted field names with parameterized values
        main_sql = text(
            f"""
            SELECT DISTINCT ON (t.talent_id) t.talent_id, t.name, t.name_en, t.role_type,
                   t.current_title, t.h_index, t.works_count, t.topic_tags,
                   t.openalex_topics,
                   COALESCE(es.school_id, cs.school_id, s.school_id) as school_id,
                   COALESCE(es.school_name, cs.school_name, s.school_name) as school_name
            FROM core_talent_tech_tag ttt
            INNER JOIN core_talent t ON ttt.talent_id = t.talent_id
            LEFT JOIN core_school es ON t.education_school_id = es.school_id
            LEFT JOIN core_school cs ON t.company_school_id = cs.school_id
            LEFT JOIN core_school s ON t.school_id = s.school_id
            WHERE {where_clause}
            ORDER BY t.talent_id DESC
            LIMIT :limit
        """
        )
        params["limit"] = page_size + 1

        result = await self.session.execute(main_sql, params)

        # Build Talent objects
        talents = []
        for row in result.fetchall():
            import json

            topic_tags = row.topic_tags or []
            if isinstance(topic_tags, str):
                try:
                    topic_tags = json.loads(topic_tags)
                except (json.JSONDecodeError, TypeError):
                    topic_tags = []

            openalex_topics = row.openalex_topics if hasattr(row, "openalex_topics") else []
            if openalex_topics is None:
                openalex_topics = []
            if isinstance(openalex_topics, str):
                try:
                    openalex_topics = json.loads(openalex_topics)
                except (json.JSONDecodeError, TypeError):
                    openalex_topics = []

            talent = Talent(
                talent_id=row.talent_id,
                name=row.name,
                name_en=row.name_en,
                role_type=row.role_type,
                current_title=row.current_title,
                h_index=row.h_index,
                works_count=row.works_count,
                topic_tags=topic_tags,
                openalex_topics=openalex_topics,
            )
            if row.school_id:
                talent.school = School(
                    school_id=row.school_id,
                    school_name=row.school_name,
                )
            talents.append(talent)

        # Determine next cursor
        next_cursor = None
        if len(talents) > page_size:
            talents = talents[:page_size]
            next_cursor = talents[-1].talent_id

        return talents, next_cursor

    async def get_talent_list(
        self,
        domain_id: int | None = None,
        direction_id: int | None = None,
        country_code: str | None = None,
        school_id: int | None = None,
        role_type: str | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Talent], int]:
        """Get talent list with filters - optimized with raw SQL for speed."""
        from sqlalchemy import text

        # Build WHERE conditions
        conditions = ["ttt.is_enabled IS TRUE"]
        params = {}

        if domain_id:
            conditions.append("ttt.tech_domain_id = :domain_id")
            params["domain_id"] = domain_id
        if direction_id:
            conditions.append("ttt.tech_direction_id = :direction_id")
            params["direction_id"] = direction_id
        if school_id:
            conditions.append(
                "(t.education_school_id = :school_id OR t.company_school_id = :school_id OR t.school_id = :school_id)"
            )
            params["school_id"] = school_id
        if country_code:
            conditions.append("s.country_code = :country_code")
            params["country_code"] = country_code.upper()
        if role_type:
            conditions.append("t.role_type = :role_type")
            params["role_type"] = role_type
        if keyword:
            conditions.append("t.name LIKE :keyword")
            params["keyword"] = f"%{keyword}%"

        where_clause = " AND ".join(conditions)

        # Count query - fast with DISTINCT
        # JOIN all three school fields for country_code filtering
        # Safe: where_clause uses only whitelisted field names with parameterized values
        count_sql = text(
            f"""
            SELECT COUNT(DISTINCT t.talent_id)
            FROM core_talent_tech_tag ttt
            INNER JOIN core_talent t ON ttt.talent_id = t.talent_id
            LEFT JOIN core_school s ON COALESCE(t.education_school_id, t.company_school_id, t.school_id) = s.school_id
            WHERE {where_clause}
        """
        )
        total_result = await self.session.execute(count_sql, params)
        total = total_result.scalar() or 0

        # Main query with pagination
        # Use subquery to avoid JSON equality comparison issues in PostgreSQL
        # Priority: education_school -> company_school -> legacy school
        # Safe: where_clause uses only whitelisted field names with parameterized values
        offset = (page - 1) * page_size
        main_sql = text(
            f"""
            SELECT t.talent_id, t.name, t.name_en, t.role_type,
                   t.current_title, t.h_index, t.works_count, t.topic_tags,
                   t.openalex_topics,
                   COALESCE(es.school_id, cs.school_id, s.school_id) as school_id,
                   COALESCE(es.school_name, cs.school_name, s.school_name) as school_name
            FROM core_talent t
            LEFT JOIN core_school es ON t.education_school_id = es.school_id
            LEFT JOIN core_school cs ON t.company_school_id = cs.school_id
            LEFT JOIN core_school s ON t.school_id = s.school_id
            WHERE t.talent_id IN (
                SELECT DISTINCT ttt.talent_id
                FROM core_talent_tech_tag ttt
                WHERE {where_clause}
            )
            ORDER BY t.h_index DESC NULLS LAST
            LIMIT :limit OFFSET :offset
        """
        )
        params["limit"] = page_size
        params["offset"] = offset

        result = await self.session.execute(main_sql, params)

        # Build Talent objects with school data
        talents = []
        for row in result.fetchall():
            # Parse topic_tags if it's a string
            topic_tags = row.topic_tags or []
            if isinstance(topic_tags, str):
                try:
                    import json

                    topic_tags = json.loads(topic_tags)
                except (json.JSONDecodeError, TypeError):
                    topic_tags = []

            # Parse openalex_topics if it's a string (access by attribute name)
            openalex_topics = row.openalex_topics if hasattr(row, "openalex_topics") else []
            if openalex_topics is None:
                openalex_topics = []
            if isinstance(openalex_topics, str):
                try:
                    import json

                    openalex_topics = json.loads(openalex_topics)
                except (json.JSONDecodeError, TypeError):
                    openalex_topics = []

            talent = Talent(
                talent_id=row.talent_id,
                name=row.name,
                name_en=row.name_en,
                role_type=row.role_type,
                current_title=row.current_title,
                h_index=row.h_index,
                works_count=row.works_count,
                topic_tags=topic_tags,
                openalex_topics=openalex_topics,
            )
            if row.school_id:
                talent.school = School(
                    school_id=row.school_id,
                    school_name=row.school_name,
                )
            talents.append(talent)

        return talents, total
