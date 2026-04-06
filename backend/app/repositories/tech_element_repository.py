"""
Technology Element Repository.
技术要素数据访问层
"""

from __future__ import annotations

from sqlalchemy import and_, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import IS_SQLITE
from app.models.school import School
from app.models.talent import Talent
from app.models.tech_element import TalentTechTag, TechDirection, TechElement


class TechElementRepository:
    """Repository for tech element operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_elements(self) -> list[TechElement]:
        """Get all enabled tech elements with directions."""
        result = await self.session.execute(
            select(TechElement)
            .where(TechElement.is_enabled.is_(True))
            .options(selectinload(TechElement.directions))
            .order_by(TechElement.sort_order, TechElement.tech_element_id)
        )
        return list(result.scalars().all())

    async def get_element_by_id(self, element_id: int) -> TechElement | None:
        """Get tech element by ID."""
        result = await self.session.execute(
            select(TechElement)
            .where(TechElement.tech_element_id == element_id)
            .options(selectinload(TechElement.directions))
        )
        return result.scalar_one_or_none()

    async def get_directions_by_element(self, element_id: int) -> list[TechDirection]:
        """Get all directions for a tech element."""
        result = await self.session.execute(
            select(TechDirection)
            .where(and_(
                TechDirection.tech_element_id == element_id,
                TechDirection.is_enabled.is_(True)
            ))
            .order_by(TechDirection.sort_order, TechDirection.tech_direction_id)
        )
        return list(result.scalars().all())

    async def get_element_stats(self, element_id: int | None = None) -> dict:
        """Get statistics for tech element(s).

        Optimized to use a single CTE query for PostgreSQL.
        """
        if element_id:
            if not IS_SQLITE:
                # PostgreSQL: Single CTE query
                cte_query = text("""
                    WITH element_tags AS (
                        SELECT DISTINCT ttt.talent_id, ttt.tech_direction_id,
                               t.role_type, t.school_id
                        FROM core_talent_tech_tag ttt
                        INNER JOIN core_talent t ON ttt.talent_id = t.talent_id
                        WHERE ttt.tech_element_id = :element_id
                    )
                    SELECT
                        (SELECT COUNT(DISTINCT talent_id) FROM element_tags) AS talent_count,
                        (SELECT COUNT(DISTINCT talent_id) FROM element_tags
                         WHERE role_type = 'professor') AS professor_count,
                        (SELECT COUNT(DISTINCT talent_id) FROM element_tags
                         WHERE role_type IN ('student', 'graduated')) AS student_count,
                        (SELECT COUNT(DISTINCT tech_direction_id) FROM element_tags) AS direction_count,
                        (SELECT COUNT(DISTINCT s.country_code)
                         FROM element_tags et
                         INNER JOIN core_school s ON et.school_id = s.school_id
                         WHERE s.country_code IS NOT NULL) AS country_count,
                        (SELECT COUNT(DISTINCT s.school_id)
                         FROM element_tags et
                         INNER JOIN core_school s ON et.school_id = s.school_id) AS school_count
                """)

                result = await self.session.execute(cte_query, {'element_id': element_id})
                row = result.one()

                return {
                    'talent_count': row.talent_count or 0,
                    'professor_count': row.professor_count or 0,
                    'student_count': row.student_count or 0,
                    'direction_count': row.direction_count or 0,
                    'country_count': row.country_count or 0,
                    'school_count': row.school_count or 0,
                }

            # SQLite fallback: Separate queries
            base_query = select(
                func.count(func.distinct(TalentTechTag.talent_id)).label('talent_count'),
                func.count(func.distinct(TalentTechTag.tech_direction_id)).label('direction_count'),
            ).where(TalentTechTag.tech_element_id == element_id)

            professor_count_query = select(
                func.count(func.distinct(Talent.talent_id))
            ).select_from(TalentTechTag).join(
                Talent, TalentTechTag.talent_id == Talent.talent_id
            ).where(and_(
                TalentTechTag.tech_element_id == element_id,
                Talent.role_type == 'professor'
            ))

            student_count_query = select(
                func.count(func.distinct(Talent.talent_id))
            ).select_from(TalentTechTag).join(
                Talent, TalentTechTag.talent_id == Talent.talent_id
            ).where(and_(
                TalentTechTag.tech_element_id == element_id,
                Talent.role_type.in_(['student', 'graduated'])
            ))

            country_count_query = select(
                func.count(func.distinct(School.country_code))
            ).select_from(TalentTechTag).join(
                Talent, TalentTechTag.talent_id == Talent.talent_id
            ).join(
                School, Talent.school_id == School.school_id
            ).where(
                TalentTechTag.tech_element_id == element_id,
                School.country_code.isnot(None),
            )

            school_count_query = select(
                func.count(func.distinct(School.school_id))
            ).select_from(TalentTechTag).join(
                Talent, TalentTechTag.talent_id == Talent.talent_id
            ).join(
                School, Talent.school_id == School.school_id
            ).where(TalentTechTag.tech_element_id == element_id)

            result = await self.session.execute(base_query)
            row = result.one()

            professor_result = await self.session.execute(professor_count_query)
            student_result = await self.session.execute(student_count_query)
            country_result = await self.session.execute(country_count_query)
            school_result = await self.session.execute(school_count_query)

            return {
                'talent_count': row.talent_count or 0,
                'professor_count': professor_result.scalar() or 0,
                'student_count': student_result.scalar() or 0,
                'direction_count': row.direction_count or 0,
                'country_count': country_result.scalar() or 0,
                'school_count': school_result.scalar() or 0,
            }
        else:
            # Global stats
            elements_count = await self.session.execute(
                select(func.count(TechElement.tech_element_id)).where(TechElement.is_enabled.is_(True))
            )
            directions_count = await self.session.execute(
                select(func.count(TechDirection.tech_direction_id)).where(TechDirection.is_enabled.is_(True))
            )
            talents_count = await self.session.execute(
                select(func.count(func.distinct(TalentTechTag.talent_id)))
            )

            return {
                'element_count': elements_count.scalar() or 0,
                'direction_count': directions_count.scalar() or 0,
                'talent_count': talents_count.scalar() or 0,
            }

    async def get_overall_stats(self) -> dict:
        """
        Get overall statistics for the tech element page.

        Optimized to use a single CTE query for PostgreSQL,
        falls back to multiple queries for SQLite.
        """
        if not IS_SQLITE:
            # PostgreSQL: Use single CTE query for efficiency
            cte_query = text("""
                WITH enabled_tags AS (
                    SELECT DISTINCT ttt.talent_id, ttt.tech_element_id,
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
                    (SELECT COUNT(DISTINCT tech_element_id) FROM enabled_tags) AS tech_element_count,
                    (SELECT COUNT(DISTINCT tech_direction_id) FROM enabled_tags) AS tech_direction_count,
                    (SELECT COUNT(DISTINCT s.country_code)
                     FROM enabled_tags et
                     INNER JOIN core_school s ON et.school_id = s.school_id
                     WHERE s.country_code IS NOT NULL) AS country_count,
                    (SELECT COUNT(DISTINCT s.school_id)
                     FROM enabled_tags et
                     INNER JOIN core_school s ON et.school_id = s.school_id) AS school_count
            """)

            result = await self.session.execute(cte_query)
            row = result.one()

            return {
                'talent_count': row.talent_count or 0,
                'professor_count': row.professor_count or 0,
                'student_count': row.student_count or 0,
                'country_count': row.country_count or 0,
                'school_count': row.school_count or 0,
                'tech_element_count': row.tech_element_count or 0,
                'tech_direction_count': row.tech_direction_count or 0,
            }

        # SQLite fallback: Use separate queries
        # Total talent count with tech tags
        talent_count_query = select(
            func.count(func.distinct(Talent.talent_id))
        ).select_from(TalentTechTag).join(
            Talent, TalentTechTag.talent_id == Talent.talent_id
        ).where(TalentTechTag.is_enabled.is_(True))

        # Professor count
        professor_count_query = select(
            func.count(func.distinct(Talent.talent_id))
        ).select_from(TalentTechTag).join(
            Talent, TalentTechTag.talent_id == Talent.talent_id
        ).where(and_(
            TalentTechTag.is_enabled.is_(True),
            Talent.role_type == 'professor'
        ))

        # Student count
        student_count_query = select(
            func.count(func.distinct(Talent.talent_id))
        ).select_from(TalentTechTag).join(
            Talent, TalentTechTag.talent_id == Talent.talent_id
        ).where(and_(
            TalentTechTag.is_enabled.is_(True),
            Talent.role_type.in_(['student', 'graduated'])
        ))

        # Country count
        country_count_query = select(
            func.count(func.distinct(School.country_code))
        ).select_from(TalentTechTag).join(
            Talent, TalentTechTag.talent_id == Talent.talent_id
        ).join(
            School, Talent.school_id == School.school_id
        ).where(
            TalentTechTag.is_enabled.is_(True),
            School.country_code.isnot(None),
        )

        # School count
        school_count_query = select(
            func.count(func.distinct(School.school_id))
        ).select_from(TalentTechTag).join(
            Talent, TalentTechTag.talent_id == Talent.talent_id
        ).join(
            School, Talent.school_id == School.school_id
        ).where(TalentTechTag.is_enabled.is_(True))

        # Tech element count
        element_count_query = select(
            func.count(func.distinct(TechElement.tech_element_id))
        ).select_from(TalentTechTag).join(
            TechElement, TalentTechTag.tech_element_id == TechElement.tech_element_id
        ).where(TalentTechTag.is_enabled.is_(True))

        # Tech direction count
        direction_count_query = select(
            func.count(func.distinct(TalentTechTag.tech_direction_id))
        ).where(TalentTechTag.is_enabled.is_(True))

        # Execute all queries
        talent_count = await self.session.execute(talent_count_query)
        professor_count = await self.session.execute(professor_count_query)
        student_count = await self.session.execute(student_count_query)
        country_count = await self.session.execute(country_count_query)
        school_count = await self.session.execute(school_count_query)
        element_count = await self.session.execute(element_count_query)
        direction_count = await self.session.execute(direction_count_query)

        return {
            'talent_count': talent_count.scalar() or 0,
            'professor_count': professor_count.scalar() or 0,
            'student_count': student_count.scalar() or 0,
            'country_count': country_count.scalar() or 0,
            'school_count': school_count.scalar() or 0,
            'tech_element_count': element_count.scalar() or 0,
            'tech_direction_count': direction_count.scalar() or 0,
        }

    async def get_country_distribution(
        self, element_id: int | None = None, direction_id: int | None = None
    ) -> list[dict]:
        """Get talent distribution by country."""
        query = select(
            School.country_code,
            School.country_name,
            func.count(func.distinct(Talent.talent_id)).label('talent_count'),
        ).select_from(TalentTechTag).join(
            Talent, TalentTechTag.talent_id == Talent.talent_id
        ).join(
            School, Talent.school_id == School.school_id
        ).where(
            School.country_code.isnot(None),
        ).group_by(
            School.country_code, School.country_name
        ).order_by(func.count(func.distinct(Talent.talent_id)).desc())

        conditions = [TalentTechTag.is_enabled.is_(True)]
        if element_id:
            conditions.append(TalentTechTag.tech_element_id == element_id)
        if direction_id:
            conditions.append(TalentTechTag.tech_direction_id == direction_id)

        query = query.where(and_(*conditions))

        result = await self.session.execute(query)
        return [
            {
                'country_code': row.country_code,
                'country_name': row.country_name or row.country_code,
                'talent_count': row.talent_count,
            }
            for row in result.all()
        ]

    async def get_school_distribution(
        self, element_id: int | None = None, direction_id: int | None = None,
        country_code: str | None = None, page: int = 1, page_size: int = 20
    ) -> tuple[list[dict], int]:
        """Get talent distribution by school."""
        # Base query for counting
        count_query = select(
            func.count(func.distinct(School.school_id))
        ).select_from(TalentTechTag).join(
            Talent, TalentTechTag.talent_id == Talent.talent_id
        ).join(
            School, Talent.school_id == School.school_id
        )

        # Main query
        query = select(
            School.school_id,
            School.school_name,
            School.country_name.label('country_name'),
            func.count(func.distinct(Talent.talent_id)).label('talent_count'),
        ).select_from(TalentTechTag).join(
            Talent, TalentTechTag.talent_id == Talent.talent_id
        ).join(
            School, Talent.school_id == School.school_id
        ).group_by(
            School.school_id, School.school_name, School.country_name
        ).order_by(func.count(func.distinct(Talent.talent_id)).desc())

        conditions = [TalentTechTag.is_enabled.is_(True)]
        if element_id:
            conditions.append(TalentTechTag.tech_element_id == element_id)
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
                'school_id': row.school_id,
                'school_name': row.school_name,
                'country_name': row.country_name,
                'talent_count': row.talent_count,
            }
            for row in result.all()
        ]

        return items, total

    async def get_talent_list_by_cursor(
        self,
        element_id: int | None = None,
        direction_id: int | None = None,
        country_code: str | None = None,
        school_id: int | None = None,
        role_type: str | None = None,
        keyword: str | None = None,
        cursor: int | None = None,
        page_size: int = 20
    ) -> tuple[list[Talent], int | None]:
        """
        Get talent list with cursor-based pagination (efficient for deep pagination).

        Uses talent_id as cursor for consistent and efficient pagination.

        Args:
            element_id: Filter by tech element
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
        conditions = ["ttt.is_enabled = 1"]
        params = {}

        if cursor is not None:
            conditions.append("t.talent_id < :cursor")
            params['cursor'] = cursor

        if element_id:
            conditions.append("ttt.tech_element_id = :element_id")
            params['element_id'] = element_id
        if direction_id:
            conditions.append("ttt.tech_direction_id = :direction_id")
            params['direction_id'] = direction_id
        if school_id:
            conditions.append("t.school_id = :school_id")
            params['school_id'] = school_id
        if country_code:
            conditions.append("s.country_code = :country_code")
            params['country_code'] = country_code.upper()
        if role_type:
            conditions.append("t.role_type = :role_type")
            params['role_type'] = role_type
        if keyword:
            conditions.append("t.name LIKE :keyword")
            params['keyword'] = f'%{keyword}%'

        where_clause = " AND ".join(conditions)

        # Main query with cursor pagination (fetch one extra for next_cursor)
        main_sql = text(f"""
            SELECT DISTINCT t.talent_id, t.name, t.name_en, t.role_type,
                   t.current_title, t.h_index, t.works_count, t.topic_tags,
                   t.openalex_topics,
                   s.school_id, s.school_name
            FROM core_talent_tech_tag ttt
            INNER JOIN core_talent t ON ttt.talent_id = t.talent_id
            LEFT JOIN core_school s ON t.school_id = s.school_id
            WHERE {where_clause}
            ORDER BY t.talent_id DESC
            LIMIT :limit
        """)
        params['limit'] = page_size + 1

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

            openalex_topics = row.openalex_topics if hasattr(row, 'openalex_topics') else []
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
        self, element_id: int | None = None, direction_id: int | None = None,
        country_code: str | None = None, school_id: int | None = None,
        role_type: str | None = None, keyword: str | None = None,
        page: int = 1, page_size: int = 20
    ) -> tuple[list[Talent], int]:
        """Get talent list with filters - optimized with raw SQL for speed."""
        from sqlalchemy import text

        # Build WHERE conditions
        conditions = ["ttt.is_enabled = 1"]
        params = {}

        if element_id:
            conditions.append("ttt.tech_element_id = :element_id")
            params['element_id'] = element_id
        if direction_id:
            conditions.append("ttt.tech_direction_id = :direction_id")
            params['direction_id'] = direction_id
        if school_id:
            conditions.append("t.school_id = :school_id")
            params['school_id'] = school_id
        if country_code:
            conditions.append("s.country_code = :country_code")
            params['country_code'] = country_code.upper()
        if role_type:
            conditions.append("t.role_type = :role_type")
            params['role_type'] = role_type
        if keyword:
            conditions.append("t.name LIKE :keyword")
            params['keyword'] = f'%{keyword}%'

        where_clause = " AND ".join(conditions)

        # Count query - fast with DISTINCT
        count_sql = text(f"""
            SELECT COUNT(DISTINCT t.talent_id)
            FROM core_talent_tech_tag ttt
            INNER JOIN core_talent t ON ttt.talent_id = t.talent_id
            LEFT JOIN core_school s ON t.school_id = s.school_id
            WHERE {where_clause}
        """)
        total_result = await self.session.execute(count_sql, params)
        total = total_result.scalar() or 0

        # Main query with pagination
        offset = (page - 1) * page_size
        main_sql = text(f"""
            SELECT DISTINCT t.talent_id, t.name, t.name_en, t.role_type,
                   t.current_title, t.h_index, t.works_count, t.topic_tags,
                   t.openalex_topics,
                   s.school_id, s.school_name
            FROM core_talent_tech_tag ttt
            INNER JOIN core_talent t ON ttt.talent_id = t.talent_id
            LEFT JOIN core_school s ON t.school_id = s.school_id
            WHERE {where_clause}
            ORDER BY t.h_index DESC NULLS LAST
            LIMIT :limit OFFSET :offset
        """)
        params['limit'] = page_size
        params['offset'] = offset

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
            openalex_topics = row.openalex_topics if hasattr(row, 'openalex_topics') else []
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
