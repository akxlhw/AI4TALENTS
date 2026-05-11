"""
Homepage Service - 首页服务层

封装 HomepageRepository 调用，遵循架构规范：Endpoint -> Service -> Repository
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.academic.repositories.homepage_repository import HomepageRepository


class HomepageService:
    """
    首页服务 - 封装首页聚合数据相关的业务逻辑

    职责：
    - 热门技术领域查询
    - 主要国家统计
    - Top院校查询
    - 热门研究方向查询
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = HomepageRepository(session)

    async def get_hot_tech_domains(self, limit: int = 6) -> list[dict]:
        """
        获取热门技术领域（按人才数排序）

        Args:
            limit: 返回数量限制

        Returns:
            List[dict]: 热门技术领域列表
        """
        return await self.repo.get_hot_tech_domains(limit=limit)

    async def get_top_countries(self, limit: int = 5) -> list[dict]:
        """
        获取主要国家（按人才数排序）

        Args:
            limit: 返回数量限制

        Returns:
            List[dict]: 主要国家列表
        """
        return await self.repo.get_top_countries(limit=limit)

    async def get_top_schools(
        self, limit: int = 5, country_code: str | None = None
    ) -> list[dict]:
        """
        获取Top院校（按人才数排序）

        Args:
            limit: 返回数量限制
            country_code: 按国家代码筛选（"CN"国内，"__OVERSEAS__"海外）

        Returns:
            List[dict]: Top院校列表
        """
        return await self.repo.get_top_schools(limit=limit, country_code=country_code)

    async def get_hot_research_topics(self, limit: int = 5) -> list[dict]:
        """
        获取热门研究方向（按人才数排序）

        Args:
            limit: 返回数量限制

        Returns:
            List[dict]: 热门研究方向列表
        """
        return await self.repo.get_hot_research_topics(limit=limit)
