"""
Repository for homepage data operations.
首页数据查询Repository
"""

import logging

from sqlalchemy import BigInteger, Column, Integer, MetaData, Table, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.academic.models.school import School
from app.domains.academic.models.statistics import ResearchTopicStats
from app.domains.academic.models.talent import Talent
from app.domains.academic.models.tech_domain import TalentTechTag, TechDomain

logger = logging.getLogger(__name__)

# Materialized view: mv_school_talent_count
# Refreshed by Phase 10 (phase_10_school_stats.py) after each collection.
# Counts talents via ANY affiliation: school_id, education_school_id, or company_school_id.
mv_school_talent_count = Table(
    "mv_school_talent_count",
    MetaData(),
    Column("school_id", Integer, primary_key=True),
    Column("talent_count", BigInteger),
    Column("professor_count", BigInteger),
    Column("student_count", BigInteger),
)


class HomepageRepository:
    """Repository for homepage data queries."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_hot_tech_domains(self, limit: int = 6) -> list[dict]:
        """
        Get hot tech domains by talent count.
        按人才数获取热门技术领域

        Args:
            limit: Maximum number of results

        Returns:
            List of dictionaries with tech domain info and talent count
        """
        # Count talents per tech domain through talent_tech_tag
        query = (
            select(
                TechDomain.tech_domain_id,
                TechDomain.domain_code,
                TechDomain.domain_name,
                func.count(func.distinct(TalentTechTag.talent_id)).label("talent_count"),
            )
            .select_from(TechDomain)
            .outerjoin(TalentTechTag, TechDomain.tech_domain_id == TalentTechTag.tech_domain_id)
            .where(TechDomain.is_enabled.is_(True))
            .group_by(TechDomain.tech_domain_id)
            .order_by(func.count(func.distinct(TalentTechTag.talent_id)).desc())
            .limit(limit)
        )

        result = await self.session.execute(query)
        rows = result.all()

        return [
            {
                "tech_domain_id": row.tech_domain_id,
                "domain_code": row.domain_code,
                "domain_name": row.domain_name,
                "talent_count": row.talent_count,
            }
            for row in rows
        ]

    async def _mv_exists(self) -> bool:
        """Check whether the materialized view exists in the current database."""
        result = await self.session.execute(text("""
                SELECT 1 FROM pg_matviews
                WHERE matviewname = 'mv_school_talent_count'
                LIMIT 1
                """))
        return result.scalar() is not None

    async def get_top_countries(self, limit: int = 5) -> list[dict]:
        """
        Get top countries by talent count.
        按人才数获取主要国家

        Falls back to a real-time COUNT query when the materialized view
        is unavailable (e.g. missing or locked).

        Args:
            limit: Maximum number of results

        Returns:
            List of dictionaries with country info and talent count
        """
        if await self._mv_exists():
            result = await self.session.execute(
                select(
                    School.country_code,
                    School.country_name,
                    func.sum(mv_school_talent_count.c.talent_count).label("talent_count"),
                )
                .select_from(School)
                .join(
                    mv_school_talent_count,
                    School.school_id == mv_school_talent_count.c.school_id,
                )
                .where(
                    School.is_visible.is_(True),
                    School.country_code != "XX",  # 排除"未知"国家
                    School.country_code.isnot(None),
                )
                .group_by(School.country_code, School.country_name)
                .having(func.sum(mv_school_talent_count.c.talent_count) > 0)
                .order_by(func.sum(mv_school_talent_count.c.talent_count).desc())
                .limit(limit)
            )
            rows = result.all()
        else:
            logger.warning(
                "Materialized view mv_school_talent_count missing; "
                "falling back to real-time COUNT for get_top_countries"
            )
            # Fallback: real-time COUNT via talent-school affiliation
            fallback_query = (
                select(
                    School.country_code,
                    School.country_name,
                    func.count(func.distinct(Talent.talent_id)).label("talent_count"),
                )
                .select_from(School)
                .join(
                    Talent,
                    (
                        (Talent.school_id == School.school_id)
                        | (Talent.education_school_id == School.school_id)
                        | (Talent.company_school_id == School.school_id)
                    ),
                )
                .where(
                    School.is_visible.is_(True),
                    School.country_code != "XX",
                    School.country_code.isnot(None),
                    Talent.is_visible.is_(True),
                )
                .group_by(School.country_code, School.country_name)
                .having(func.count(func.distinct(Talent.talent_id)) > 0)
                .order_by(func.count(func.distinct(Talent.talent_id)).desc())
                .limit(limit)
            )
            result = await self.session.execute(fallback_query)
            rows = result.all()

        return [
            {
                "country_code": row.country_code,
                "country_name": row.country_name,
                "talent_count": int(row.talent_count or 0),
            }
            for row in rows
        ]

    async def get_hot_research_topics(self, limit: int = 5) -> list[dict]:
        """
        Get hot research topics from pre-computed table.
        从预计算表获取热门研究方向

        Args:
            limit: Maximum number of results

        Returns:
            List of dictionaries with topic name and talent count
        """
        query = (
            select(ResearchTopicStats.topic_name, ResearchTopicStats.talent_count)
            .order_by(ResearchTopicStats.talent_count.desc())
            .limit(limit)
        )

        result = await self.session.execute(query)
        rows = result.all()

        return [
            {
                "topic_name": row.topic_name,
                "talent_count": row.talent_count,
            }
            for row in rows
        ]

    async def get_top_schools(self, limit: int = 5, country_code: str | None = None) -> list[dict]:
        """
        Get top schools by talent count.
        按人才数获取Top院校

        Uses mv_school_talent_count materialized view for consistent
        affiliation-based counting (school_id OR education_school_id OR company_school_id).

        Falls back to a real-time COUNT query when the materialized view
        is unavailable (e.g. missing or locked).

        Args:
            limit: Maximum number of results
            country_code: Filter by country code (e.g. "CN" for domestic,
                or "__OVERSEAS__" for all non-CN/non-XX countries)

        Returns:
            List of dictionaries with school info and talent count
        """
        if await self._mv_exists():
            mv_query = (
                select(
                    School.school_id,
                    School.school_name,
                    School.country_name,
                    School.country_code,
                    mv_school_talent_count.c.talent_count,
                )
                .select_from(School)
                .join(
                    mv_school_talent_count,
                    School.school_id == mv_school_talent_count.c.school_id,
                )
                .where(School.is_visible.is_(True))
            )

            if country_code == "__OVERSEAS__":
                mv_query = mv_query.where(
                    School.country_code.notin_(["CN", "XX"]),
                )
            elif country_code:
                mv_query = mv_query.where(School.country_code == country_code)

            mv_query = mv_query.order_by(mv_school_talent_count.c.talent_count.desc()).limit(limit)

            result = await self.session.execute(mv_query)
            rows = result.all()
        else:
            logger.warning(
                "Materialized view mv_school_talent_count missing; "
                "falling back to real-time COUNT for get_top_schools"
            )
            # Fallback: real-time COUNT via talent-school affiliation
            primary_school = func.coalesce(
                Talent.education_school_id, Talent.company_school_id, Talent.school_id
            )
            fallback_subq = (
                select(primary_school.label("sid"), func.count().label("tc"))
                .where(Talent.is_visible.is_(True), primary_school.isnot(None))
                .group_by(primary_school)
                .subquery()
            )
            fallback_query = (
                select(
                    School.school_id,
                    School.school_name,
                    School.country_name,
                    School.country_code,
                    fallback_subq.c.tc.label("talent_count"),
                )
                .select_from(School)
                .join(fallback_subq, School.school_id == fallback_subq.c.sid)
                .where(School.is_visible.is_(True))
            )

            if country_code == "__OVERSEAS__":
                fallback_query = fallback_query.where(
                    School.country_code.notin_(["CN", "XX"]),
                )
            elif country_code:
                fallback_query = fallback_query.where(School.country_code == country_code)

            fallback_query = fallback_query.order_by(fallback_subq.c.tc.desc()).limit(limit)

            result = await self.session.execute(fallback_query)
            rows = result.all()

        return [
            {
                "school_id": row.school_id,
                "school_name": row.school_name,
                "country_name": row.country_name,
                "country_code": row.country_code,
                "talent_count": int(row.talent_count or 0),
            }
            for row in rows
        ]
