"""
Technology Element Repository.
技术要素数据访问层
"""
from typing import Optional, List, Tuple
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.tech_element import TechElement, TechDirection, TalentTechTag
from app.models.talent import Talent
from app.models.school import School
from app.models.country import Country


class TechElementRepository:
    """Repository for tech element operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_elements(self) -> List[TechElement]:
        """Get all enabled tech elements with directions."""
        result = await self.session.execute(
            select(TechElement)
            .where(TechElement.is_enabled == True)
            .options(selectinload(TechElement.directions))
            .order_by(TechElement.sort_order, TechElement.tech_element_id)
        )
        return list(result.scalars().all())

    async def get_element_by_id(self, element_id: int) -> Optional[TechElement]:
        """Get tech element by ID."""
        result = await self.session.execute(
            select(TechElement)
            .where(TechElement.tech_element_id == element_id)
            .options(selectinload(TechElement.directions))
        )
        return result.scalar_one_or_none()

    async def get_directions_by_element(self, element_id: int) -> List[TechDirection]:
        """Get all directions for a tech element."""
        result = await self.session.execute(
            select(TechDirection)
            .where(and_(
                TechDirection.tech_element_id == element_id,
                TechDirection.is_enabled == True
            ))
            .order_by(TechDirection.sort_order, TechDirection.tech_direction_id)
        )
        return list(result.scalars().all())

    async def get_element_stats(self, element_id: Optional[int] = None) -> dict:
        """Get statistics for tech element(s)."""
        if element_id:
            # Stats for specific element
            base_query = select(
                func.count(func.distinct(TalentTechTag.talent_id)).label('talent_count'),
                func.count(func.distinct(TalentTechTag.tech_direction_id)).label('direction_count'),
            ).where(TalentTechTag.tech_element_id == element_id)

            # Country and school counts
            country_count_query = select(
                func.count(func.distinct(Country.country_id))
            ).select_from(TalentTechTag).join(
                Talent, TalentTechTag.talent_id == Talent.talent_id
            ).join(
                School, Talent.school_id == School.school_id
            ).join(
                Country, School.country_id == Country.country_id
            ).where(TalentTechTag.tech_element_id == element_id)

            school_count_query = select(
                func.count(func.distinct(School.school_id))
            ).select_from(TalentTechTag).join(
                Talent, TalentTechTag.talent_id == Talent.talent_id
            ).join(
                School, Talent.school_id == School.school_id
            ).where(TalentTechTag.tech_element_id == element_id)

            result = await self.session.execute(base_query)
            row = result.one()

            country_result = await self.session.execute(country_count_query)
            school_result = await self.session.execute(school_count_query)

            return {
                'talent_count': row.talent_count or 0,
                'direction_count': row.direction_count or 0,
                'country_count': country_result.scalar() or 0,
                'school_count': school_result.scalar() or 0,
            }
        else:
            # Global stats
            elements_count = await self.session.execute(
                select(func.count(TechElement.tech_element_id)).where(TechElement.is_enabled == True)
            )
            directions_count = await self.session.execute(
                select(func.count(TechDirection.tech_direction_id)).where(TechDirection.is_enabled == True)
            )
            talents_count = await self.session.execute(
                select(func.count(func.distinct(TalentTechTag.talent_id)))
            )

            return {
                'element_count': elements_count.scalar() or 0,
                'direction_count': directions_count.scalar() or 0,
                'talent_count': talents_count.scalar() or 0,
            }

    async def get_country_distribution(
        self, element_id: Optional[int] = None, direction_id: Optional[int] = None
    ) -> List[dict]:
        """Get talent distribution by country."""
        query = select(
            Country.country_id,
            Country.country_name_cn,
            Country.country_code,
            func.count(func.distinct(Talent.talent_id)).label('talent_count'),
        ).select_from(TalentTechTag).join(
            Talent, TalentTechTag.talent_id == Talent.talent_id
        ).join(
            School, Talent.school_id == School.school_id
        ).join(
            Country, School.country_id == Country.country_id
        ).group_by(
            Country.country_id, Country.country_name_cn, Country.country_code
        ).order_by(func.count(func.distinct(Talent.talent_id)).desc())

        conditions = [TalentTechTag.is_enabled == True]
        if element_id:
            conditions.append(TalentTechTag.tech_element_id == element_id)
        if direction_id:
            conditions.append(TalentTechTag.tech_direction_id == direction_id)

        query = query.where(and_(*conditions))

        result = await self.session.execute(query)
        return [
            {
                'country_id': row.country_id,
                'country_name': row.country_name_cn or row.country_code,
                'country_code': row.country_code,
                'talent_count': row.talent_count,
            }
            for row in result.all()
        ]

    async def get_school_distribution(
        self, element_id: Optional[int] = None, direction_id: Optional[int] = None,
        country_id: Optional[int] = None, page: int = 1, page_size: int = 20
    ) -> Tuple[List[dict], int]:
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
            Country.country_name_cn.label('country_name'),
            func.count(func.distinct(Talent.talent_id)).label('talent_count'),
        ).select_from(TalentTechTag).join(
            Talent, TalentTechTag.talent_id == Talent.talent_id
        ).join(
            School, Talent.school_id == School.school_id
        ).join(
            Country, School.country_id == Country.country_id
        ).group_by(
            School.school_id, School.school_name, Country.country_name_cn
        ).order_by(func.count(func.distinct(Talent.talent_id)).desc())

        conditions = [TalentTechTag.is_enabled == True]
        if element_id:
            conditions.append(TalentTechTag.tech_element_id == element_id)
        if direction_id:
            conditions.append(TalentTechTag.tech_direction_id == direction_id)
        if country_id:
            conditions.append(School.country_id == country_id)

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

    async def get_talent_list(
        self, element_id: Optional[int] = None, direction_id: Optional[int] = None,
        country_id: Optional[int] = None, school_id: Optional[int] = None,
        role_type: Optional[str] = None, keyword: Optional[str] = None,
        page: int = 1, page_size: int = 20
    ) -> Tuple[List[Talent], int]:
        """Get talent list with filters."""
        query = select(Talent).join(
            TalentTechTag, Talent.talent_id == TalentTechTag.talent_id
        ).join(
            School, Talent.school_id == School.school_id, isouter=True
        ).where(TalentTechTag.is_enabled == True)

        # Apply filters
        if element_id:
            query = query.where(TalentTechTag.tech_element_id == element_id)
        if direction_id:
            query = query.where(TalentTechTag.tech_direction_id == direction_id)
        if country_id:
            query = query.where(School.country_id == country_id)
        if school_id:
            query = query.where(Talent.school_id == school_id)
        if role_type:
            query = query.where(Talent.role_type == role_type)
        if keyword:
            query = query.where(Talent.name.ilike(f'%{keyword}%'))

        # Count query
        count_query = select(func.count(func.distinct(Talent.talent_id))).select_from(
            query.subquery()
        )
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination and ordering
        query = query.distinct(Talent.talent_id).order_by(
            Talent.h_index.desc().nullslast()
        ).offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(query.options(selectinload(Talent.school)))
        talents = list(result.scalars().all())

        return talents, total
