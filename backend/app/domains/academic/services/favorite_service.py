"""
Favorite Service - 收藏服务层

封装 FavoriteRepository 调用，遵循架构规范：Endpoint -> Service -> Repository
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.academic.repositories.favorite_repository import FavoriteRepository
from app.domains.shared.models.iam import FavoriteTalent


class FavoriteService:
    """
    收藏服务 - 封装人才收藏相关的业务逻辑

    职责：
    - 添加/移除收藏
    - 收藏列表查询
    - 收藏状态检查
    - 收藏备注更新
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = FavoriteRepository(session)

    async def get_by_user_and_talent(
        self, user_id: int, talent_id: int
    ) -> FavoriteTalent | None:
        """
        根据用户ID和人才ID获取收藏记录

        Args:
            user_id: 用户ID
            talent_id: 人才ID

        Returns:
            Optional[FavoriteTalent]: 收藏记录或None
        """
        return await self.repo.get_by_user_and_talent(user_id, talent_id)

    async def add_favorite_and_commit(
        self, user_id: int, talent_id: int, notes: str | None = None
    ) -> FavoriteTalent:
        """
        添加收藏并提交

        Args:
            user_id: 用户ID
            talent_id: 人才ID
            notes: 备注

        Returns:
            FavoriteTalent: 创建的收藏记录
        """
        return await self.repo.add_favorite_and_commit(user_id, talent_id, notes)

    async def get_with_relationships(self, favorite_id: int) -> FavoriteTalent | None:
        """
        获取收藏记录（含关联数据）

        Args:
            favorite_id: 收藏ID

        Returns:
            Optional[FavoriteTalent]: 收藏记录（含人才关联）或None
        """
        return await self.repo.get_with_relationships(favorite_id)

    async def list_user_favorites(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        role_type: str | None = None,
        keyword: str | None = None,
    ) -> tuple[list[FavoriteTalent], int]:
        """
        获取用户收藏列表（分页）

        Args:
            user_id: 用户ID
            page: 页码
            page_size: 每页数量
            role_type: 按角色类型筛选
            keyword: 搜索关键词

        Returns:
            Tuple[List[FavoriteTalent], int]: 收藏列表和总数
        """
        return await self.repo.list_user_favorites(
            user_id=user_id,
            page=page,
            page_size=page_size,
            role_type=role_type,
            keyword=keyword,
        )

    async def get_user_favorite_ids(self, user_id: int) -> list[int]:
        """
        获取用户所有收藏的人才ID列表

        Args:
            user_id: 用户ID

        Returns:
            List[int]: 人才ID列表
        """
        return await self.repo.get_user_favorite_ids(user_id)

    async def update_favorite_and_commit(
        self, favorite_id: int, notes: str | None = None
    ) -> FavoriteTalent | None:
        """
        更新收藏备注并提交

        Args:
            favorite_id: 收藏ID
            notes: 新的备注

        Returns:
            Optional[FavoriteTalent]: 更新后的收藏记录或None
        """
        return await self.repo.update_favorite_and_commit(favorite_id, notes)

    async def remove_favorite_and_commit(self, user_id: int, talent_id: int) -> bool:
        """
        移除收藏并提交

        Args:
            user_id: 用户ID
            talent_id: 人才ID

        Returns:
            bool: 是否成功移除
        """
        return await self.repo.remove_favorite_and_commit(user_id, talent_id)

    async def update_followup_status_and_commit(
        self, user_id: int, talent_id: int, status: str
    ) -> FavoriteTalent | None:
        """
        更新收藏人才的跟进状态并提交

        Args:
            user_id: 用户ID
            talent_id: 人才ID
            status: 跟进状态

        Returns:
            Optional[FavoriteTalent]: 更新后的收藏记录或None
        """
        return await self.repo.update_followup_status_and_commit(user_id, talent_id, status)
