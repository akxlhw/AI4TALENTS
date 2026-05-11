"""
Tech Domain Service - 技术领域服务层

封装 TechDomainRepository 调用，遵循架构规范：Endpoint -> Service -> Repository
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.academic.models.talent import Talent
from app.domains.academic.models.tech_domain import TechDomain
from app.domains.academic.repositories.tech_domain_repository import TechDomainRepository


class TechDomainService:
    """
    技术领域服务 - 封装技术领域相关的业务逻辑

    职责：
    - 技术领域列表查询
    - 技术领域统计
    - 国家/院校分布
    - 人才列表查询
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = TechDomainRepository(session)

    async def get_all_domains(self) -> list[TechDomain]:
        """
        获取所有启用的技术领域

        Returns:
            List[TechDomain]: 技术领域列表
        """
        return await self.repo.get_all_domains()

    async def get_domain_by_id(self, domain_id: int) -> TechDomain | None:
        """
        根据ID获取技术领域

        Args:
            domain_id: 技术领域ID

        Returns:
            Optional[TechDomain]: 技术领域或None
        """
        return await self.repo.get_domain_by_id(domain_id)

    async def get_domain_stats(self, domain_id: int | None = None) -> dict:
        """
        获取技术领域统计

        Args:
            domain_id: 技术领域ID（None则返回全局统计）

        Returns:
            dict: 统计信息
        """
        return await self.repo.get_domain_stats(domain_id)

    async def get_overall_stats(self) -> dict:
        """
        获取总体统计

        Returns:
            dict: 总体统计信息
        """
        return await self.repo.get_overall_stats()

    async def get_country_distribution(
        self, domain_id: int | None = None, direction_id: int | None = None
    ) -> list[dict]:
        """
        获取国家分布

        Args:
            domain_id: 技术领域ID
            direction_id: 技术方向ID

        Returns:
            List[dict]: 国家分布数据
        """
        return await self.repo.get_country_distribution(domain_id, direction_id)

    async def get_school_distribution(
        self,
        domain_id: int | None = None,
        direction_id: int | None = None,
        country_code: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """
        获取院校分布

        Args:
            domain_id: 技术领域ID
            direction_id: 技术方向ID
            country_code: 国家代码
            page: 页码
            page_size: 每页数量

        Returns:
            Tuple[List[dict], int]: 院校分布数据和总数
        """
        return await self.repo.get_school_distribution(
            domain_id=domain_id,
            direction_id=direction_id,
            country_code=country_code,
            page=page,
            page_size=page_size,
        )

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
        """
        获取人才列表

        Args:
            domain_id: 技术领域ID
            direction_id: 技术方向ID
            country_code: 国家代码
            school_id: 院校ID
            role_type: 角色类型
            keyword: 搜索关键词
            page: 页码
            page_size: 每页数量

        Returns:
            Tuple[List[Talent], int]: 人才列表和总数
        """
        return await self.repo.get_talent_list(
            domain_id=domain_id,
            direction_id=direction_id,
            country_code=country_code,
            school_id=school_id,
            role_type=role_type,
            keyword=keyword,
            page=page,
            page_size=page_size,
        )
