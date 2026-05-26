"""
OS Favourite Service - 开源人才收藏与人才池业务逻辑

从 OpenSourceService 中拆分出的收藏（Favourite）与人才池（Talent Pool）相关方法。
遵循架构规范：Endpoint -> Service -> Repository
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.domains.open_source.models.open_source import (
    OSFavourite,
    OSPoolMember,
    OSTalentPool,
)
from app.domains.open_source.repositories.open_source import OpenSourceRepository

logger = logging.getLogger(__name__)


class OSFavouriteService:
    """
    开源人才收藏与人才池服务

    职责：
    - 收藏管理（增删改查）
    - 人才池管理（增删改查）
    - 人才池成员管理
    """

    def __init__(self, session: AsyncSession):
        self.repo = OpenSourceRepository(session)

    # ============= Favourites =============

    async def list_favourites(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        keyword: str | None = None,
    ) -> tuple[list[OSFavourite], int]:
        """
        获取用户收藏列表

        Args:
            user_id: 用户ID
            page: 页码
            page_size: 每页数量
            keyword: 搜索关键词

        Returns:
            Tuple[List[OSFavourite], int]: 收藏列表和总数
        """
        return await self.repo.list_favourites(
            user_id=user_id,
            page=page,
            page_size=page_size,
            keyword=keyword,
        )

    async def get_favourite_ids(self, user_id: int) -> list[int]:
        """
        获取用户收藏的开发者ID列表

        Args:
            user_id: 用户ID

        Returns:
            List[int]: 开发者ID列表
        """
        return await self.repo.get_favourite_ids(user_id)

    async def add_favourite(
        self, user_id: int, developer_id: int, notes: str | None = None
    ) -> OSFavourite:
        """
        添加收藏

        Args:
            user_id: 用户ID
            developer_id: 开发者ID
            notes: 备注

        Returns:
            OSFavourite: 创建的收藏记录

        Raises:
            ValueError: 已收藏
        """
        existing = await self.repo.get_favourite(user_id, developer_id)
        if existing:
            raise ConflictError("Already favorited")

        return await self.repo.create_favourite(
            user_id=user_id,
            developer_id=developer_id,
            notes=notes,
        )

    async def update_favourite(
        self,
        user_id: int,
        developer_id: int,
        notes: str | None = None,
        followup_status: str | None = None,
    ) -> OSFavourite | None:
        """
        更新收藏

        Args:
            user_id: 用户ID
            developer_id: 开发者ID
            notes: 备注
            followup_status: 跟进状态

        Returns:
            Optional[OSFavourite]: 更新后的收藏或None
        """
        favourite = await self.repo.get_favourite(user_id, developer_id)
        if not favourite:
            return None
        data = {}
        if notes is not None:
            data["notes"] = notes
        if followup_status is not None:
            data["followup_status"] = followup_status
        return await self.repo.update_favourite(favourite, data)

    async def remove_favourite(self, user_id: int, developer_id: int) -> bool:
        """
        移除收藏

        Args:
            user_id: 用户ID
            developer_id: 开发者ID

        Returns:
            bool: 是否移除成功
        """
        favourite = await self.repo.get_favourite(user_id, developer_id)
        if not favourite:
            return False
        await self.repo.delete_favourite(favourite)
        return True

    # ============= Talent Pool =============

    async def list_talent_pools(self, user_id: int) -> list[OSTalentPool]:
        """
        获取用户的人才池列表

        Args:
            user_id: 用户ID

        Returns:
            List[OSTalentPool]: 人才池列表
        """
        return await self.repo.list_talent_pools(user_id)

    async def create_talent_pool(
        self,
        user_id: int,
        pool_name: str,
        pool_type: str | None = "custom",
        scope_desc: str | None = None,
    ) -> OSTalentPool:
        """
        创建人才池

        Args:
            user_id: 用户ID
            pool_name: 人才池名称
            pool_type: 人才池类型
            scope_desc: 描述

        Returns:
            OSTalentPool: 创建的人才池
        """
        return await self.repo.create_talent_pool({
            "owner_user_id": user_id,
            "pool_name": pool_name,
            "pool_type": pool_type,
            "scope_desc": scope_desc,
        })

    async def update_talent_pool(
        self, pool_id: int, update_data: dict[str, Any]
    ) -> OSTalentPool | None:
        """
        更新人才池

        Args:
            pool_id: 人才池ID
            update_data: 更新字段字典

        Returns:
            Optional[OSTalentPool]: 更新后的人才池或None
        """
        return await self.repo.update_talent_pool(pool_id, update_data)

    async def delete_talent_pool(self, pool_id: int) -> bool:
        """
        删除人才池

        Args:
            pool_id: 人才池ID

        Returns:
            bool: 是否删除成功
        """
        return await self.repo.delete_talent_pool(pool_id)

    async def add_pool_member(
        self, pool_id: int, developer_id: int, notes: str | None = None
    ) -> OSPoolMember:
        """
        添加成员到人才池

        Args:
            pool_id: 人才池ID
            developer_id: 开发者ID
            notes: 备注

        Returns:
            OSPoolMember: 添加的成员记录

        Raises:
            ValueError: 成员已存在
        """
        existing = await self.repo.get_pool_member(pool_id, developer_id)
        if existing:
            raise ConflictError("Already in pool")

        return await self.repo.add_pool_member(pool_id, developer_id)

    async def remove_pool_member(self, pool_id: int, developer_id: int) -> bool:
        """
        从人才池移除成员

        Args:
            pool_id: 人才池ID
            developer_id: 开发者ID

        Returns:
            bool: 是否移除成功
        """
        member = await self.repo.get_pool_member(pool_id, developer_id)
        if not member:
            return False
        await self.repo.remove_pool_member(member)
        return True

    async def list_pool_members(
        self, pool_id: int, page: int = 1, page_size: int = 20
    ) -> tuple[list[dict[str, Any]], int]:
        """
        获取人才池成员列表

        Args:
            pool_id: 人才池ID
            page: 页码
            page_size: 每页数量

        Returns:
            Tuple[List[dict], int]: 成员列表和总数
        """
        return await self.repo.list_pool_members(
            pool_id=pool_id,
            page=page,
            page_size=page_size,
        )

    async def get_talent_pool(self, pool_id: int) -> OSTalentPool | None:
        """Get a talent pool by ID."""
        return await self.repo.get_talent_pool(pool_id)
