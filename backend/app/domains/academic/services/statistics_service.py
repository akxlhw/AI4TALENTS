"""
Statistics Service - 统计服务层

封装 StatisticsRepository 调用，遵循架构规范：Endpoint -> Service -> Repository
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.academic.models.statistics import OverviewStatSnapshot
from app.domains.academic.repositories.stat_repository import StatisticsRepository


class StatisticsService:
    """
    统计服务 - 封装系统统计相关的业务逻辑

    职责：
    - 获取概览统计数据
    - 国家数量统计
    - 技术领域/方向数量统计
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = StatisticsRepository(session)

    async def get_active_overview_stats(self) -> OverviewStatSnapshot | None:
        """
        获取当前激活的概览统计快照

        Returns:
            Optional[OverviewStatSnapshot]: 概览统计快照或None
        """
        return await self.repo.get_active_overview_stats()

    async def get_country_count(self) -> int:
        """
        获取有可见人才的国家数量

        Returns:
            int: 国家数量
        """
        return await self.repo.get_country_count()

    async def get_tech_domain_count(self) -> int:
        """
        获取已启用的技术领域数量

        Returns:
            int: 技术领域数量
        """
        return await self.repo.get_tech_domain_count()

    async def get_tech_direction_count(self) -> int:
        """
        获取已启用的技术方向数量

        Returns:
            int: 技术方向数量
        """
        return await self.repo.get_tech_direction_count()
