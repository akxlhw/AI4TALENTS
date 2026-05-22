"""
School Service - 院校服务层

封装 SchoolRepository 调用，遵循架构规范：Endpoint -> Service -> Repository
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.academic.models.school import School
from app.domains.academic.repositories.school_repository import SchoolRepository


class SchoolService:
    """
    院校服务 - 封装院校相关的业务逻辑

    职责：
    - 院校列表查询与筛选
    - 院校详情获取
    - 院校统计信息
    - Top院校管理
    - 国家维度统计
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = SchoolRepository(session)

    async def get_list(
        self,
        country_code: str | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
        visible_only: bool = True,
        is_top_school: bool | None = None,
    ) -> tuple[list[School], int]:
        """
        获取院校列表（带筛选和分页）

        Args:
            country_code: 按国家代码筛选
            keyword: 搜索关键词
            page: 页码
            page_size: 每页数量
            visible_only: 是否仅返回可见院校
            is_top_school: 按Top院校筛选

        Returns:
            Tuple[List[School], int]: 院校列表和总数
        """
        return await self.repo.get_list(
            country_code=country_code,
            keyword=keyword,
            page=page,
            page_size=page_size,
            visible_only=visible_only,
            is_top_school=is_top_school,
        )

    async def get_by_id(self, school_id: int) -> School | None:
        """
        根据ID获取院校

        Args:
            school_id: 院校ID

        Returns:
            Optional[School]: 院校实例或None
        """
        return await self.repo.get_by_id(school_id)

    async def get_talent_counts(self, school_id: int) -> dict[str, int]:
        """
        获取院校的人才统计（按角色类型）

        Args:
            school_id: 院校ID

        Returns:
            Dict[str, int]: 各角色类型人才数量
        """
        return await self.repo.get_talent_counts(school_id)

    async def get_country_stats(self) -> list[tuple]:
        """
        获取按国家分组的院校和教授数量统计

        Returns:
            List[tuple]: 国家统计数据列表
        """
        return await self.repo.get_country_stats()

    async def get_mv_stats_for_schools(self, school_ids: list[int]) -> dict[int, dict]:
        """
        批量获取院校的物化视图统计（affiliation口径）

        Args:
            school_ids: 院校ID列表

        Returns:
            Dict[int, dict]: school_id -> {"talent_count", "professor_count", "student_count"}
        """
        return await self.repo.get_mv_stats_batch(school_ids)

    async def set_top_school_and_commit(self, school_id: int) -> bool:
        """
        设置院校为Top院校

        Args:
            school_id: 院校ID

        Returns:
            bool: 是否成功
        """
        return await self.repo.set_top_school_and_commit(school_id)

    async def unset_top_school_and_commit(self, school_id: int) -> bool:
        """
        取消院校的Top院校标记

        Args:
            school_id: 院校ID

        Returns:
            bool: 是否成功
        """
        return await self.repo.unset_top_school_and_commit(school_id)

    async def batch_set_top_schools_and_commit(self, school_ids: list[int]) -> int:
        """
        批量设置Top院校

        Args:
            school_ids: 院校ID列表

        Returns:
            int: 更新的数量
        """
        return await self.repo.batch_set_top_schools_and_commit(school_ids)

    async def batch_unset_top_schools_and_commit(self, school_ids: list[int]) -> int:
        """
        批量取消Top院校

        Args:
            school_ids: 院校ID列表

        Returns:
            int: 更新的数量
        """
        return await self.repo.batch_unset_top_schools_and_commit(school_ids)
