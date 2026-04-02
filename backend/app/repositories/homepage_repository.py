"""
Repository for homepage data operations.
首页数据查询Repository
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.school import School
from app.models.tech_element import TalentTechTag, TechElement


class HomepageRepository:
    """Repository for homepage data queries."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_hot_tech_elements(self, limit: int = 6) -> list[dict]:
        """
        Get hot tech elements by talent count.
        按人才数获取热门技术要素

        Args:
            limit: Maximum number of results

        Returns:
            List of dictionaries with tech element info and talent count
        """
        # Count talents per tech element through talent_tech_tag
        query = (
            select(
                TechElement.tech_element_id,
                TechElement.element_code,
                TechElement.element_name,
                func.count(func.distinct(TalentTechTag.talent_id)).label("talent_count"),
            )
            .select_from(TechElement)
            .outerjoin(
                TalentTechTag,
                TechElement.tech_element_id == TalentTechTag.tech_element_id
            )
            .where(TechElement.is_enabled.is_(True))
            .group_by(TechElement.tech_element_id)
            .order_by(func.count(func.distinct(TalentTechTag.talent_id)).desc())
            .limit(limit)
        )

        result = await self.session.execute(query)
        rows = result.all()

        return [
            {
                "tech_element_id": row.tech_element_id,
                "element_code": row.element_code,
                "element_name": row.element_name,
                "talent_count": row.talent_count,
            }
            for row in rows
        ]

    async def get_top_countries(self, limit: int = 5) -> list[dict]:
        """
        Get top countries by talent count.
        按人才数获取主要国家

        Args:
            limit: Maximum number of results

        Returns:
            List of dictionaries with country info and talent count
        """
        # Sum talent counts from schools grouped by country_code
        query = (
            select(
                School.country_code,
                School.country_name,
                func.sum(School.professor_count + School.student_count).label("talent_count"),
            )
            .select_from(School)
            .where(
                School.is_visible.is_(True),
                School.country_code != "XX",  # 排除"未知"国家
                School.country_code.isnot(None),
            )
            .group_by(School.country_code, School.country_name)
            .having(func.sum(School.professor_count + School.student_count) > 0)
            .order_by(func.sum(School.professor_count + School.student_count).desc())
            .limit(limit)
        )

        result = await self.session.execute(query)
        rows = result.all()

        return [
            {
                "country_code": row.country_code,
                "country_name": row.country_name,
                "talent_count": int(row.talent_count or 0),
            }
            for row in rows
        ]

    async def get_top_schools(self, limit: int = 5) -> list[dict]:
        """
        Get top schools by talent count.
        按人才数获取Top院校

        Args:
            limit: Maximum number of results

        Returns:
            List of dictionaries with school info and talent count
        """
        query = (
            select(
                School.school_id,
                School.school_name,
                School.country_name,
                School.country_code,
                (School.professor_count + School.student_count).label("talent_count"),
            )
            .select_from(School)
            .where(School.is_visible.is_(True))
            .order_by((School.professor_count + School.student_count).desc())
            .limit(limit)
        )

        result = await self.session.execute(query)
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
