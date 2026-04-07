"""
Talent Service - 统一的人才服务入口

提供人才相关的业务逻辑操作，封装 Repository 调用。
遵循架构规范：Endpoint -> Service -> Repository
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.school import School
from app.models.talent import Talent
from app.models.tech_element import TalentTechTag
from app.repositories.school_repository import SchoolRepository
from app.repositories.talent_repository import TalentRepository


class TalentService:
    """
    人才服务 - 封装人才相关的业务逻辑

    职责：
    - 人才列表查询与筛选
    - 人才详情获取
    - 人才数据导出
    - 统计信息计算
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.talent_repo = TalentRepository(session)
        self.school_repo = SchoolRepository(session)

    async def get_talent_list(
        self,
        school_id: int | None = None,
        country_code: str | None = None,
        role_type: str | None = None,
        min_works: int | None = None,
        min_citations: int | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[list[Talent], int]:
        """
        获取人才列表（带筛选）

        Args:
            school_id: 学校ID筛选
            country_code: 国家代码筛选
            role_type: 角色类型筛选
            min_works: 最小论文数
            min_citations: 最小引用数
            keyword: 搜索关键词
            page: 页码
            page_size: 每页数量

        Returns:
            Tuple[List[Talent], int]: 人才列表和总数
        """
        return await self.talent_repo.get_list(
            school_id=school_id,
            country_code=country_code,
            role_type=role_type,
            min_works=min_works,
            min_citations=min_citations,
            keyword=keyword,
            page=page,
            page_size=page_size,
        )

    async def get_talent_by_id(
        self, talent_id: int, include_relations: bool = True
    ) -> Talent | None:
        """
        获取人才详情

        Args:
            talent_id: 人才ID
            include_relations: 是否包含关联数据

        Returns:
            Optional[Talent]: 人才详情或None
        """
        return await self.talent_repo.get_by_id(talent_id, include_relations)

    async def get_talent_with_relations(self, talent_id: int) -> Talent | None:
        """
        获取人才详情（包含关联数据）

        Args:
            talent_id: 人才ID

        Returns:
            Optional[Talent]: 人才详情（含学校、技术标签等）
        """
        result = await self.session.execute(
            select(Talent)
            .where(Talent.talent_id == talent_id)
            .options(
                selectinload(Talent.school),
                selectinload(Talent.tech_tags).selectinload(TalentTechTag.tech_element),
            )
        )
        return result.scalar_one_or_none()

    async def get_talents_by_ids(self, talent_ids: list[int]) -> list[Talent]:
        """
        批量获取人才

        Args:
            talent_ids: 人才ID列表

        Returns:
            List[Talent]: 人才列表
        """
        if not talent_ids:
            return []

        result = await self.session.execute(
            select(Talent)
            .where(Talent.talent_id.in_(talent_ids))
            .options(
                selectinload(Talent.school),
                selectinload(Talent.role_profile),
            )
        )
        return list(result.scalars().all())

    async def get_selected_works(self, talent_id: int, limit: int = 10):
        """
        获取人才的代表作品

        Args:
            talent_id: 人才ID
            limit: 返回数量限制

        Returns:
            List[SelectedWork]: 作品列表
        """
        return await self.talent_repo.get_selected_works(talent_id, limit)

    async def talent_exists(self, talent_id: int) -> bool:
        """
        检查人才是否存在

        Args:
            talent_id: 人才ID

        Returns:
            bool: 是否存在
        """
        talent = await self.get_talent_by_id(talent_id, include_relations=False)
        return talent is not None

    async def get_talent_collaborations(
        self,
        talent_id: int,
        limit: int = 10
    ) -> list[dict]:
        """
        获取人才的合作者

        Args:
            talent_id: 人才ID
            limit: 返回数量限制

        Returns:
            List[dict]: 合作者列表
        """
        # TODO: 实现合作者查询
        return []

    async def get_statistics(self) -> dict:
        """
        获取人才统计信息

        Returns:
            dict: 统计信息
        """
        # 总人数
        total_count = await self.session.execute(
            select(func.count(Talent.talent_id))
        )
        total = total_count.scalar() or 0

        # 按角色统计
        role_stats = await self.session.execute(
            select(Talent.role_type, func.count(Talent.talent_id))
            .group_by(Talent.role_type)
        )
        by_role = {row[0]: row[1] for row in role_stats.all()}

        # 学校数
        school_count = await self.session.execute(
            select(func.count(School.school_id))
        )
        schools = school_count.scalar() or 0

        return {
            "total_talents": total,
            "total_schools": schools,
            "by_role": by_role,
        }

    async def search_talents(
        self,
        query: str,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[list[Talent], int]:
        """
        搜索人才（关键词搜索）

        Args:
            query: 搜索关键词
            page: 页码
            page_size: 每页数量

        Returns:
            Tuple[List[Talent], int]: 人才列表和总数
        """
        return await self.talent_repo.search(query, page, page_size)

    async def update_talent(
        self,
        talent_id: int,
        updates: dict
    ) -> Talent | None:
        """
        更新人才信息

        Args:
            talent_id: 人才ID
            updates: 更新字段字典

        Returns:
            Optional[Talent]: 更新后的人才或None
        """
        talent = await self.get_talent_by_id(talent_id)
        if not talent:
            return None

        for key, value in updates.items():
            if hasattr(talent, key):
                setattr(talent, key, value)

        talent.updated_at = datetime.utcnow()
        await self.session.flush()
        return talent
