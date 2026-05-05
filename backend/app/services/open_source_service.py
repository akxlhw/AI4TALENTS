"""
Open Source Service - 开源人才库业务逻辑层

封装开源人才库的业务逻辑，调用 OpenSourceRepository 进行数据操作。
遵循架构规范：Endpoint -> Service -> Repository
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.open_source import (
    OSCollectTask,
    OSDeveloper,
    OSFavourite,
    OSPoolMember,
    OSRepoConfig,
    OSTalentPool,
)
from app.repositories.open_source_repository import OpenSourceRepository
from app.schemas.open_source import (
    OSContributionItem,
    OSDeveloperCompareResponse,
    OSDeveloperDetail,
    OSDeveloperSummary,
    OSEmbeddingStatusResponse,
    OSJDMatchResponse,
    OSLanguageSkillItem,
    OSRepositoryItem,
    OSStatsResponse,
    OSSearchRequest,
)

logger = logging.getLogger(__name__)

VALID_TECH_ELEMENTS = {"ai", "robotics", "data_science", "networks", "systems", "security"}
REPO_FULL_NAME_PATTERN = re.compile(r"^[\w.-]+/[\w.-]+$")


class OpenSourceService:
    """
    开源人才服务 - 封装开源人才相关的业务逻辑

    职责：
    - 仓库配置管理
    - 采集任务管理
    - 开发者查询与详情组合
    - 收藏与人才池管理
    - 统计与 JD 匹配
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = OpenSourceRepository(session)

    # ============= Repo Config =============

    async def list_repo_configs(
        self,
        page: int = 1,
        page_size: int = 50,
        tech_element: str | None = None,
        is_active: bool | None = None,
        collect_enabled: bool | None = None,
        sort_by: str = "id_desc",
        collected_only: bool = False,
    ) -> tuple[list[OSRepoConfig], int]:
        """
        获取仓库配置列表（带筛选）

        Args:
            page: 页码
            page_size: 每页数量
            tech_element: 技术要素筛选
            is_active: 是否激活筛选
            collect_enabled: 是否启用采集筛选
            sort_by: 排序方式
            collected_only: 仅显示已完成采集的仓库

        Returns:
            Tuple[List[OSRepoConfig], int]: 配置列表和总数
        """
        filters = {}
        if tech_element is not None:
            filters["tech_element"] = tech_element
        if is_active is not None:
            filters["is_active"] = is_active
        if collect_enabled is not None:
            filters["collect_enabled"] = collect_enabled
        if collected_only:
            filters["collected_only"] = collected_only
        return await self.repo.list_repo_configs(
            filters=filters,
            sort_by=sort_by,
            page=page,
            page_size=page_size,
        )

    async def get_repo_config(self, repo_config_id: int) -> OSRepoConfig | None:
        """
        获取仓库配置详情

        Args:
            repo_config_id: 配置ID

        Returns:
            Optional[OSRepoConfig]: 配置详情或None
        """
        return await self.repo.get_repo_config(repo_config_id)

    async def create_repo_config(
        self,
        repo_full_name: str,
        tech_element: str,
        display_name: str | None = None,
        description: str | None = None,
        tech_direction_id: int | None = None,
        language: str | None = None,
        notes: str | None = None,
        created_by: int | None = None,
        stars_count: int = 0,
    ) -> OSRepoConfig:
        """
        创建仓库配置

        Args:
            repo_full_name: GitHub 仓库全名，如 'pytorch/pytorch'
            tech_element: 技术要素编码
            display_name: 显示名称
            description: 描述
            tech_direction_id: 技术方向ID
            language: 主要编程语言
            notes: 备注
            created_by: 创建者用户ID
            stars_count: Star 数量

        Returns:
            OSRepoConfig: 创建的配置

        Raises:
            ValueError: 参数校验失败
        """
        if not REPO_FULL_NAME_PATTERN.match(repo_full_name):
            raise ValueError("Invalid repo_full_name format. Expected 'owner/repo'")
        if tech_element not in VALID_TECH_ELEMENTS:
            raise ValueError(
                f"Invalid tech_element: {tech_element}. Must be one of: {', '.join(sorted(VALID_TECH_ELEMENTS))}"
            )

        existing = await self.repo.get_repo_config_by_full_name(repo_full_name)
        if existing:
            raise ValueError(f"Repository '{repo_full_name}' already exists")

        return await self.repo.create_repo_config({
            "repo_full_name": repo_full_name,
            "tech_element": tech_element,
            "display_name": display_name or repo_full_name.split("/")[-1],
            "description": description,
            "tech_direction_id": tech_direction_id,
            "language": language,
            "notes": notes,
            "created_by": created_by,
            "stars_count": stars_count,
        })

    async def update_repo_config(
        self, repo_config_id: int, update_data: dict[str, Any]
    ) -> OSRepoConfig | None:
        """
        更新仓库配置

        Args:
            repo_config_id: 配置ID
            update_data: 更新字段字典

        Returns:
            Optional[OSRepoConfig]: 更新后的配置或None

        Raises:
            ValueError: tech_element 不合法
        """
        if "tech_element" in update_data and update_data["tech_element"] not in VALID_TECH_ELEMENTS:
            raise ValueError("Invalid tech_element")

        return await self.repo.update_repo_config(repo_config_id, update_data)

    async def delete_repo_config(self, repo_config_id: int) -> bool:
        """
        删除仓库配置

        Args:
            repo_config_id: 配置ID

        Returns:
            bool: 是否删除成功
        """
        return await self.repo.delete_repo_config(repo_config_id)

    # ============= Collect Task =============

    async def list_collect_tasks(
        self, page: int = 1, page_size: int = 20
    ) -> tuple[list[OSCollectTask], int]:
        """
        获取采集任务列表

        Args:
            page: 页码
            page_size: 每页数量

        Returns:
            Tuple[List[OSCollectTask], int]: 任务列表和总数
        """
        return await self.repo.list_collect_tasks(page=page, page_size=page_size)

    async def get_collect_task(self, task_id: int) -> OSCollectTask | None:
        """
        获取采集任务详情

        Args:
            task_id: 任务ID

        Returns:
            Optional[OSCollectTask]: 任务详情或None
        """
        return await self.repo.get_collect_task(task_id)

    async def create_collect_task(
        self,
        task_name: str,
        config_json: dict[str, Any],
        created_by: int,
    ) -> OSCollectTask:
        """
        创建采集任务

        Args:
            task_name: 任务名称
            config_json: 任务配置JSON
            created_by: 创建者用户ID

        Returns:
            OSCollectTask: 创建的任务
        """
        return await self.repo.create_collect_task({
            "task_name": task_name,
            "config_json": config_json,
            "created_by": created_by,
        })

    async def cancel_collect_task(self, task_id: int) -> OSCollectTask | None:
        """
        取消采集任务

        Args:
            task_id: 任务ID

        Returns:
            Optional[OSCollectTask]: 取消后的任务或None

        Raises:
            ValueError: 任务状态不允许取消
        """
        task = await self.repo.get_collect_task(task_id)
        if not task:
            return None
        if task.status not in ("pending", "running"):
            raise ValueError(f"Cannot cancel task in status: {task.status}")

        return await self.repo.cancel_collect_task(task_id)

    async def collect_single_repo(
        self,
        repo_config_id: int,
        contributors_per_repo: int,
        created_by: int,
    ) -> tuple[OSCollectTask, str, str]:
        """
        为单个仓库创建采集任务

        Args:
            repo_config_id: 仓库配置ID
            contributors_per_repo: 每个仓库采集的contributor数量
            created_by: 创建者用户ID

        Returns:
            Tuple[OSCollectTask, str, str]: 任务、repo_full_name、tech_element

        Raises:
            ValueError: 配置不存在、采集未启用、或已有运行中任务
        """
        config = await self.repo.get_repo_config(repo_config_id)
        if not config:
            raise ValueError("Repo config not found")
        if not config.collect_enabled:
            raise ValueError("Repository collection is disabled")

        existing = await self.repo.get_active_collect_task(config.repo_full_name)
        if existing:
            raise ValueError("A collection task is already running for this repository")

        task = await self.repo.create_collect_task({
            "task_name": config.repo_full_name,
            "status": "pending",
            "config_json": {
                "repo_config_id": repo_config_id,
                "repo_full_name": config.repo_full_name,
                "tech_element": config.tech_element,
                "contributors_per_repo": contributors_per_repo,
            },
            "created_by": created_by,
        })
        return task, config.repo_full_name, config.tech_element

    # ============= Developer =============

    async def list_developers(
        self,
        q: str = "",
        tech_elements: list[str] | None = None,
        languages: list[str] | None = None,
        location: str | None = None,
        company: str | None = None,
        min_stars: int | None = None,
        sort_by: str = "stars_desc",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[OSDeveloper], int]:
        """
        获取开发者列表（带筛选）

        Args:
            q: 搜索关键词
            tech_elements: 技术要素筛选
            languages: 编程语言筛选
            location: 所在地筛选
            company: 公司筛选
            min_stars: 最小 Stars 数
            sort_by: 排序方式
            page: 页码
            page_size: 每页数量

        Returns:
            Tuple[List[OSDeveloper], int]: 开发者列表和总数
        """
        filters = {}
        if q:
            filters["q"] = q
        if tech_elements:
            filters["tech_elements"] = tech_elements
        if languages:
            filters["languages"] = languages
        if location:
            filters["location"] = location
        if company:
            filters["company"] = company
        if min_stars is not None:
            filters["min_stars"] = min_stars
        return await self.repo.list_developers(
            filters=filters,
            sort_by=sort_by,
            page=page,
            page_size=page_size,
        )

    async def get_developer(self, developer_id: int) -> OSDeveloper | None:
        """
        获取开发者详情

        Args:
            developer_id: 开发者ID

        Returns:
            Optional[OSDeveloper]: 开发者或None
        """
        return await self.repo.get_developer(developer_id)

    async def get_developer_detail(self, developer_id: int) -> OSDeveloperDetail:
        """
        获取开发者详情（组合 developer + repos + contributions + languages + similar）

        Args:
            developer_id: 开发者ID

        Returns:
            OSDeveloperDetail: 组合后的开发者详情

        Raises:
            ValueError: 开发者不存在或不可见
        """
        dev = await self.repo.get_developer(developer_id)
        if not dev or not dev.is_visible:
            raise ValueError("Developer not found")

        # 并行加载关联数据
        repos_task = self.repo.get_developer_repositories(developer_id)
        contributions_task = self.repo.get_developer_contributions(developer_id)
        languages_task = self.repo.get_developer_languages(developer_id)
        similar_task = self.repo.get_similar_developers(developer_id, limit=5)

        repos_result, contributions_result, languages_result, similar_result = await asyncio.gather(
            repos_task, contributions_task, languages_task, similar_task
        )

        repositories = [OSRepositoryItem.model_validate(r) for r in repos_result]
        contributions = [
            OSContributionItem(
                contribution_id=c.contribution_id,
                repo_id=c.repo_id,
                repo_full_name=full_name,
                commits_count=c.commits_count,
                prs_count=c.prs_count,
                issues_count=c.issues_count,
                code_reviews_count=c.code_reviews_count,
                is_owner=c.is_owner,
                is_maintainer=c.is_maintainer,
            )
            for c, full_name in contributions_result
        ]
        language_skills = [OSLanguageSkillItem.model_validate(l) for l in languages_result]
        similar_developers = [OSDeveloperSummary.model_validate(s) for s in similar_result]

        return OSDeveloperDetail(
            **OSDeveloperSummary.model_validate(dev).model_dump(),
            github_id=dev.github_id,
            blog_url=dev.blog_url,
            email=dev.email,
            followers_count=dev.followers_count,
            following_count=dev.following_count,
            public_repos_count=dev.public_repos_count,
            total_forks_received=dev.total_forks_received,
            repositories=repositories,
            contributions=contributions,
            language_skills=language_skills,
            similar_developers=similar_developers,
        )

    async def search_developers(
        self, req: OSSearchRequest
    ) -> tuple[list[OSDeveloper], int]:
        """
        搜索开发者（支持关键词/语义/混合模式）

        Args:
            req: 搜索请求对象

        Returns:
            Tuple[List[OSDeveloper], int]: 开发者列表和总数
        """
        return await self.repo.search_developers(req)

    async def compare_developers(self, developer_ids: list[int]) -> OSDeveloperCompareResponse:
        """
        对比多个开发者

        Args:
            developer_ids: 开发者ID列表（2-5个）

        Returns:
            OSDeveloperCompareResponse: 对比结果

        Raises:
            ValueError: 开发者数量不合法或部分开发者不存在
        """
        if len(developer_ids) < 2 or len(developer_ids) > 5:
            raise ValueError("developer_ids must contain 2 to 5 items")

        developers = await self.repo.get_developers_by_ids(developer_ids)
        if len(developers) != len(developer_ids):
            raise ValueError("Some developers not found")

        dimensions = {
            "stars": "Total Stars Received",
            "forks": "Total Forks Received",
            "repos": "Public Repositories",
            "followers": "Followers",
            "languages": "Language Diversity",
        }

        def _metric(dev: OSDeveloper, key: str) -> float:
            return {
                "stars": dev.total_stars_received,
                "forks": dev.total_forks_received,
                "repos": dev.public_repos_count,
                "followers": dev.followers_count,
                "languages": len(dev.primary_languages or []),
            }.get(key, 0)

        radar: dict[str, Any] = {}
        for dim_key, dim_label in dimensions.items():
            values = [_metric(dev, dim_key) for dev in developers]
            max_val = max(values) if max(values) > 0 else 1
            radar[dim_key] = {
                "label": dim_label,
                "values": [v / max_val * 100 for v in values],
                "raw_values": values,
            }

        developer_details = [
            await self.get_developer_detail(dev.developer_id) for dev in developers
        ]

        return OSDeveloperCompareResponse(
            developers=developer_details,
            radar=radar,
        )

    async def recommend_similar(
        self, developer_id: int, limit: int = 10
    ) -> list[OSDeveloper]:
        """
        推荐相似开发者

        Args:
            developer_id: 开发者ID
            limit: 返回数量

        Returns:
            List[OSDeveloper]: 相似开发者列表
        """
        return await self.repo.get_similar_developers(developer_id, limit=limit)

    # ============= Favourite =============

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
            raise ValueError("Already favorited")

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
            raise ValueError("Already in pool")

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

    # ============= Stats =============

    async def get_stats(self) -> OSStatsResponse:
        """
        获取开源人才统计信息

        Returns:
            OSStatsResponse: 统计信息
        """
        return await self.repo.get_stats()

    async def jd_match(
        self,
        jd_text: str,
        filters: Any | None = None,
        top_k: int = 20,
    ) -> OSJDMatchResponse:
        """
        JD 岗位匹配

        Args:
            jd_text: JD 文本
            filters: 筛选条件
            top_k: 返回数量

        Returns:
            OSJDMatchResponse: 匹配结果
        """
        return await self.repo.jd_match(
            jd_text=jd_text,
            filters=filters,
            top_k=top_k,
        )

    async def get_embedding_status(self) -> dict[str, int]:
        """
        获取嵌入向量状态

        Returns:
            dict: 包含 total_developers, embedded_count, pending_count
        """
        return await self.repo.get_embedding_status()

    async def generate_embeddings(self, batch_size: int = 50) -> dict[str, Any]:
        """
        生成嵌入向量

        Args:
            batch_size: 批次大小

        Returns:
            dict: 操作结果
        """
        return await self.repo.generate_embeddings(batch_size=batch_size)
