"""
Talent Pool Service - 人才池服务层

封装 TalentPoolRepository 调用，遵循架构规范：Endpoint -> Service -> Repository
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.academic.repositories.talent_pool_repository import TalentPoolRepository
from app.domains.shared.models.iam import TalentPool


class TalentPoolService:
    """
    人才池服务 - 封装人才池相关的业务逻辑

    职责：
    - 人才池的创建、更新、删除
    - 成员的添加、移除、查询
    - 人才池权限校验
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = TalentPoolRepository(session)

    async def create_pool_and_commit(
        self, user_id: int, name: str, pool_type: str = "custom", desc: str | None = None
    ) -> TalentPool:
        """
        创建人才池并提交

        Args:
            user_id: 用户ID
            name: 人才池名称
            pool_type: 类型
            desc: 描述

        Returns:
            TalentPool: 创建的人才池
        """
        return await self.repo.create_pool_and_commit(
            user_id=user_id, name=name, pool_type=pool_type, desc=desc
        )

    async def get_pool_by_id(self, pool_id: int) -> TalentPool | None:
        """
        获取人才池详情

        Args:
            pool_id: 人才池ID

        Returns:
            Optional[TalentPool]: 人才池或None
        """
        return await self.repo.get_pool_by_id(pool_id)

    async def list_user_pools(self, user_id: int) -> list[TalentPool]:
        """
        获取用户的所有人才池

        Args:
            user_id: 用户ID

        Returns:
            List[TalentPool]: 人才池列表
        """
        return await self.repo.list_user_pools(user_id)

    async def update_pool_and_commit(
        self,
        pool_id: int,
        name: str | None = None,
        desc: str | None = None,
        status: str | None = None,
    ) -> TalentPool | None:
        """
        更新人才池并提交

        Args:
            pool_id: 人才池ID
            name: 名称
            desc: 描述
            status: 状态

        Returns:
            Optional[TalentPool]: 更新后的人才池或None
        """
        return await self.repo.update_pool_and_commit(pool_id, name=name, desc=desc, status=status)

    async def delete_pool_and_commit(self, pool_id: int) -> bool:
        """
        删除人才池（归档）并提交

        Args:
            pool_id: 人才池ID

        Returns:
            bool: 是否成功删除
        """
        return await self.repo.delete_pool_and_commit(pool_id)

    async def add_member_and_commit(
        self, pool_id: int, talent_id: int, added_by: int, notes: str | None = None
    ):
        """
        添加成员并提交

        Args:
            pool_id: 人才池ID
            talent_id: 人才ID
            added_by: 添加者ID
            notes: 备注
        """
        return await self.repo.add_member_and_commit(
            pool_id=pool_id, talent_id=talent_id, added_by=added_by, notes=notes
        )

    async def remove_member_and_commit(self, pool_id: int, talent_id: int) -> bool:
        """
        移除成员并提交

        Args:
            pool_id: 人才池ID
            talent_id: 人才ID

        Returns:
            bool: 是否成功移除
        """
        return await self.repo.remove_member_and_commit(pool_id, talent_id)

    async def get_pool_members(
        self, pool_id: int, page: int = 1, page_size: int = 20
    ) -> tuple[list[dict], int]:
        """
        获取人才池成员列表

        Args:
            pool_id: 人才池ID
            page: 页码
            page_size: 每页数量

        Returns:
            Tuple[List[dict], int]: 成员列表和总数
        """
        return await self.repo.get_pool_members(pool_id, page, page_size)

    async def is_member(self, pool_id: int, talent_id: int) -> bool:
        """
        检查人才是否在人才池中

        Args:
            pool_id: 人才池ID
            talent_id: 人才ID

        Returns:
            bool: 是否在池中
        """
        return await self.repo.is_member(pool_id, talent_id)
