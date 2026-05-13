"""
OS Developer Service - 开源人才开发者查询与详情业务逻辑层

从 OpenSourceService 中拆分出的开发者相关方法，包括：
- 开发者列表查询与筛选
- 开发者详情组合
- 仓库详情与贡献者
- 搜索（关键词/语义/混合）
- 开发者对比与相似推荐
- 统计与 JD 匹配
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, NotFoundError

from app.domains.open_source.models.open_source import (
    OSDeveloper,
    OSRepoConfig,
)
from app.domains.open_source.repositories.open_source import OpenSourceRepository
from app.domains.open_source.schemas.open_source import (
    OSContributionItem,
    OSDeveloperCompareResponse,
    OSDeveloperDetail,
    OSDeveloperSummary,
    OSJDMatchResponse,
    OSLanguageSkillItem,
    OSRepositoryContributor,
    OSRepositoryItem,
    OSSearchRequest,
    OSStatsResponse,
)

logger = logging.getLogger(__name__)


class OSDeveloperService:
    """
    开源开发者服务 - 封装开发者查询、搜索、对比、推荐等业务逻辑

    职责：
    - 开发者列表查询与筛选
    - 开发者详情组合（developer + repos + contributions + languages + similar）
    - 仓库详情与贡献者列表
    - 搜索（关键词 / 语义 / 混合模式）
    - 开发者对比与相似推荐
    - 统计与 JD 匹配
    """

    def __init__(self, session: AsyncSession):
        self.repo = OpenSourceRepository(session)
        self.session = session

    # ============= Developer =============

    async def list_developers(
        self,
        q: str = "",
        tech_elements: list[str] | None = None,
        languages: list[str] | None = None,
        location: str | None = None,
        company: str | None = None,
        min_stars: int | None = None,
        is_committer: bool | None = None,
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
        if is_committer is not None:
            filters["is_committer"] = is_committer
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
            raise NotFoundError("Developer")

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
                is_committer=c.is_committer,
            )
            for c, full_name in contributions_result
        ]
        language_skills = [OSLanguageSkillItem.model_validate(lang) for lang in languages_result]
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

    async def get_repository_detail(self, repo_full_name: str) -> dict[str, Any]:
        """
        获取仓库详情（含贡献者统计）

        Args:
            repo_full_name: 仓库全名，如 "deepspeedai/DeepSpeed"

        Returns:
            dict: 仓库详情字典
        """
        repo = await self.repo.get_repository_by_full_name(repo_full_name)
        if not repo:
            raise NotFoundError("Repository")

        contributor_count = await self.repo.count_repository_contributors(repo.repo_id)

        # Fetch description and tech_element from OSRepoConfig (OSRepository doesn't have these fields)
        from sqlalchemy import select
        config_result = await self.session.execute(
            select(OSRepoConfig).where(OSRepoConfig.repo_full_name == repo_full_name)
        )
        config = config_result.scalar_one_or_none()

        return {
            "repo_id": repo.repo_id,
            "full_name": repo.full_name,
            "display_name": repo.name,
            "description": config.description if config else None,
            "language": repo.language,
            "stars_count": repo.stars_count,
            "forks_count": repo.forks_count,
            "topics": repo.topics or [],
            "tech_element": config.tech_element if config else "",
            "contributor_count": contributor_count,
        }

    async def get_repository_contributors(
        self,
        repo_full_name: str,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[OSRepositoryContributor], int]:
        """
        获取仓库贡献者列表

        Args:
            repo_full_name: 仓库全名
            page: 页码
            page_size: 每页数量

        Returns:
            Tuple[List[OSRepositoryContributor], int]: 贡献者列表和总数
        """
        repo = await self.repo.get_repository_by_full_name(repo_full_name)
        if not repo:
            raise NotFoundError("Repository")
        items, total = await self.repo.get_repository_contributors(repo.repo_id, page, page_size)
        contributors: list[OSRepositoryContributor] = []
        for dev, contrib in items:
            roles: list[str] = []
            if contrib.is_owner:
                roles.append("Owner")
            if contrib.is_committer:
                roles.append("Committer")
            contributors.append(
                OSRepositoryContributor(
                    developer_id=dev.developer_id,
                    github_login=dev.github_login,
                    name=dev.name,
                    avatar_url=dev.avatar_url,
                    company=dev.company,
                    location=dev.location,
                    commits_count=contrib.commits_count,
                    prs_count=contrib.prs_count,
                    issues_count=contrib.issues_count,
                    is_owner=contrib.is_owner,
                    is_committer=contrib.is_committer,
                    roles=roles,
                )
            )
        return contributors, total

    async def search_developers(
        self, req: OSSearchRequest
    ) -> tuple[list[OSDeveloper], int]:
        """搜索开发者（支持关键词/语义/混合模式）

        所有搜索逻辑统一在 Service 层处理，Endpoint 只负责调用此接口。
        """
        if req.mode == "keyword" or not req.q:
            return await self.repo.search_developers(req)
        return await self._semantic_or_hybrid_search(req)

    async def _semantic_or_hybrid_search(
        self, req: OSSearchRequest
    ) -> tuple[list[OSDeveloper], int]:
        """Internal: semantic / hybrid search with LLM embedding."""
        from app.domains.open_source.services.open_source_embedding_service import (
            OpenSourceEmbeddingService,
        )
        from app.domains.shared.services.config_service import ConfigService
        from app.domains.shared.services.llm import LLMGateway

        config_service = ConfigService(self.session)
        llm_config = await config_service.get_llm_config()

        if not llm_config.embedding_enabled or not llm_config.embedding_model:
            logger.warning("Embedding not configured, falling back to keyword")
            return await self.repo.search_developers(req)

        llm_gateway = LLMGateway(
            api_key=llm_config.api_key,
            api_base=llm_config.api_base,
            model=llm_config.model,
            embedding_model=llm_config.embedding_model,
            embedding_api_base=llm_config.embedding_api_base,
            embedding_api_key=llm_config.embedding_api_key,
            timeout=llm_config.timeout or 60,
            api_format=llm_config.api_format,
            embedding_api_format=llm_config.embedding_api_format,
        )

        embed_service = OpenSourceEmbeddingService(
            session=self.session,
            llm_gateway=llm_gateway,
            dimension=llm_config.embedding_dimension,
            model_name=llm_config.embedding_model,
        )

        try:
            query_embedding = await embed_service.get_query_embedding(req.q)
        except Exception as e:
            logger.warning(f"Failed to generate query embedding, falling back to keyword: {e}")
            return await self.repo.search_developers(req)

        filters = {}
        if req.filters:
            if req.filters.tech_elements:
                filters["tech_elements"] = req.filters.tech_elements
            if req.filters.languages:
                filters["languages"] = req.filters.languages
            if req.filters.location:
                filters["location"] = req.filters.location
            if req.filters.company:
                filters["company"] = req.filters.company
            if req.filters.min_stars is not None:
                filters["min_stars"] = req.filters.min_stars

        if req.mode == "semantic":
            semantic_items, total = await self.repo.search_by_vector_similarity(
                query_embedding=query_embedding,
                similarity_threshold=0.7,
                filters=filters,
                limit=req.page_size,
                offset=(req.page - 1) * req.page_size,
            )
            return semantic_items, total

        # Hybrid mode: keyword + semantic merge
        keyword_items, _keyword_total = await self.list_developers(
            q=req.q,
            tech_elements=req.filters.tech_elements if req.filters else None,
            languages=req.filters.languages if req.filters else None,
            location=req.filters.location if req.filters else None,
            company=req.filters.company if req.filters else None,
            min_stars=req.filters.min_stars if req.filters else None,
            page=1,
            page_size=req.page_size * 2,
        )

        semantic_items, _semantic_total = await self.repo.search_by_vector_similarity(
            query_embedding=query_embedding,
            similarity_threshold=0.7,
            filters=filters,
            limit=req.page_size * 2,
            offset=0,
        )

        # Deduplicate and merge: semantic results first, then keyword results not already included
        seen_ids = set()
        merged = []
        for dev in semantic_items:
            if dev.developer_id not in seen_ids:
                seen_ids.add(dev.developer_id)
                merged.append(dev)
        for dev in keyword_items:
            if dev.developer_id not in seen_ids:
                seen_ids.add(dev.developer_id)
                merged.append(dev)

        total = len(merged)
        start = (req.page - 1) * req.page_size
        end = start + req.page_size
        return merged[start:end], total

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
            raise BadRequestError("developer_ids must contain 2 to 5 items")

        developers = await self.repo.get_developers_by_ids(developer_ids)
        if len(developers) != len(developer_ids):
            raise NotFoundError("Some developers")

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

    # ============= Repository passthroughs (eliminate Endpoint -> Repository穿透) =============

    async def get_developer_repositories(self, developer_id: int) -> list[Any]:
        """Get repositories for a developer."""
        return await self.repo.get_developer_repositories(developer_id)

    async def get_developer_contributions(self, developer_id: int) -> list[Any]:
        """Get contributions for a developer."""
        return await self.repo.get_developer_contributions(developer_id)

    async def get_developer_languages(self, developer_id: int) -> list[Any]:
        """Get language skills for a developer."""
        return await self.repo.get_developer_languages(developer_id)

    async def get_developers_by_ids(self, developer_ids: list[int]) -> list[OSDeveloper]:
        """Get multiple developers by IDs."""
        return await self.repo.get_developers_by_ids(developer_ids)

    async def get_visible_developer_ids(self) -> list[int]:
        """Get IDs of all visible developers."""
        return await self.repo.get_visible_developer_ids()

    # ============= Stats & JD Match =============

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
