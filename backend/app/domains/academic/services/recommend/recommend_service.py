"""
Recommend Service implementation.
推荐服务实现 - v1.4

Features:
- Similar talent recommendation
- Complement recommendation
- Diverse recommendation
- Vector similarity calculation

Security Note (S608):
This module uses raw SQL with f-strings for complex queries. All such queries are safe because:
- User inputs use parameterized placeholders (:param_name)
- Field names in clauses are from whitelisted sources
"""

# ruff: noqa: S608

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domains.academic.models.embedding import TalentEmbedding
from app.domains.academic.models.talent import Talent
from app.domains.academic.repositories.talent_repository import TalentRepository
from app.domains.shared.services.llm.errors import EmptyReferenceError, InvalidReferenceError

logger = logging.getLogger(__name__)


@dataclass
class RecommendResultItem:
    """推荐结果项"""

    talent_id: int
    name: str
    title: str
    school_name: str
    education_school_name: str | None = None
    company_school_name: str | None = None
    similarity_score: float = 0.0
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "talent_id": self.talent_id,
            "name": self.name,
            "title": self.title,
            "school_name": self.school_name,
            "education_school_name": self.education_school_name,
            "company_school_name": self.company_school_name,
            "similarity_score": self.similarity_score,
            "reasons": self.reasons,
        }


@dataclass
class RecommendResult:
    """推荐结果"""

    reference_talents: list[int]
    total: int
    items: list[RecommendResultItem]
    mode: str
    took_ms: float

    def to_dict(self) -> dict:
        return {
            "reference_talents": self.reference_talents,
            "total": self.total,
            "items": [item.to_dict() for item in self.items],
            "mode": self.mode,
            "took_ms": self.took_ms,
        }


class RecommendService:
    """推荐服务

    提供相似人才推荐功能。
    """

    def __init__(
        self,
        session: AsyncSession,
        embed_service: Any = None,
        talent_repository: TalentRepository | None = None,
    ):
        """
        初始化推荐服务

        Args:
            session: 数据库会话
            embed_service: 嵌入服务（可选）
            talent_repository: 人才数据仓储（可选，默认自动创建）
        """
        self.session = session
        self.embed_service = embed_service
        self.talent_repo = talent_repository or TalentRepository(session)

    @classmethod
    async def create_from_session(cls, session: AsyncSession) -> RecommendService:
        """
        从数据库配置创建 RecommendService 实例。

        内部处理 EmbeddingService 的构建，
        使 API 层无需直接接触 EmbeddingService。

        Args:
            session: 数据库会话

        Returns:
            RecommendService: 配置好的服务实例
        """
        from app.domains.academic.services.embedding.embedding_service import EmbeddingService
        from app.domains.shared.services.config_service import ConfigService

        config_service = ConfigService(session)
        llm_config = await config_service.get_llm_config()
        embed_service = EmbeddingService(
            session=session,
            dimension=llm_config.embedding_dimension,
        )

        return cls(session=session, embed_service=embed_service)

    async def get_similar(
        self,
        reference_talent_ids: list[int],
        limit: int = 20,
        filters: dict[str, Any] | None = None,
    ) -> RecommendResult:
        """
        获取相似人才推荐

        Args:
            reference_talent_ids: 参考人才 ID 列表
            limit: 数量限制
            filters: 过滤条件

        Returns:
            RecommendResult: 推荐结果

        Raises:
            EmptyReferenceError: 参考列表为空
            InvalidReferenceError: 参考人才不存在
        """
        start_time = time.time()

        # 验证参考列表
        if not reference_talent_ids:
            raise EmptyReferenceError()

        # 获取参考人才
        reference_talents = await self._get_reference_talents(reference_talent_ids)
        if not reference_talents:
            raise InvalidReferenceError(reference_talent_ids[0])

        # 获取相似人才
        items = await self._find_similar(reference_talents, limit, filters)

        took_ms = (time.time() - start_time) * 1000

        return RecommendResult(
            reference_talents=reference_talent_ids,
            total=len(items),
            items=items,
            mode="similar",
            took_ms=took_ms,
        )

    async def _get_reference_talents(self, talent_ids: list[int]) -> list[Talent]:
        """获取参考人才"""
        if not talent_ids:
            return []

        # 使用 Repository 的批量查询方法
        return await self.talent_repo.get_by_ids(talent_ids, include_relations=True)

    async def _find_similar(
        self,
        reference_talents: list[Talent],
        limit: int,
        filters: dict[str, Any] | None,
    ) -> list[RecommendResultItem]:
        """查找相似人才

        使用向量相似度搜索（如果有嵌入服务）或降级到标签匹配。
        """
        reference_ids = {t.talent_id for t in reference_talents}

        # 构建排除条件
        exclude_ids = list(reference_ids)
        if filters and "exclude_ids" in filters:
            exclude_ids.extend(filters["exclude_ids"])

        search_filters = {
            "exclude_ids": exclude_ids,
        }
        if filters:
            if "school_ids" in filters:
                search_filters["school_ids"] = filters["school_ids"]

        # 优先使用向量相似度搜索
        if self.embed_service is not None:
            items = await self._find_similar_by_vector(reference_talents, limit, search_filters)
            if items:
                return items

        # 降级到标签匹配
        return await self._find_similar_by_tags(reference_talents, limit, search_filters)

    async def _find_similar_by_vector(
        self,
        reference_talents: list[Talent],
        limit: int,
        filters: dict[str, Any],
    ) -> list[RecommendResultItem]:
        """使用向量相似度查找相似人才"""
        try:
            # 获取参考人才的嵌入向量（使用 research 类型）
            reference_ids = [t.talent_id for t in reference_talents]
            query = (
                select(TalentEmbedding.talent_id, TalentEmbedding.embedding)
                .where(TalentEmbedding.talent_id.in_(reference_ids))
                .where(TalentEmbedding.vector_type == "research")
            )
            result = await self.session.execute(query)
            embeddings = result.all()

            if not embeddings:
                logger.warning("No embeddings found for reference talents")
                return []

            # 计算平均向量作为查询向量
            import numpy as np

            vectors = []
            for row in embeddings:
                # embedding 是字符串格式的向量，使用 JSON 解析
                emb_str = row.embedding
                try:
                    # 尝试 JSON 解析（标准格式）
                    vec = json.loads(emb_str)
                    if not isinstance(vec, list):
                        raise ValueError(f"Embedding is not a list: {type(vec)}")
                    vectors.append(vec)
                except json.JSONDecodeError:
                    # 降级：尝试逗号分隔格式
                    logger.warning(
                        "Failed to parse embedding as JSON, trying comma-separated format"
                    )
                    try:
                        # 移除可能的方括号
                        clean_str = emb_str.strip("[]")
                        vec = [float(x) for x in clean_str.split(",") if x.strip()]
                        vectors.append(vec)
                    except ValueError as e:
                        logger.error(f"Failed to parse embedding: {e}")
                        continue

            if not vectors:
                logger.warning("No valid embeddings found for reference talents")
                return []

            query_vector = np.mean(vectors, axis=0).tolist()

            # 使用 Repository 进行向量搜索（使用 research 类型）
            items, _ = await self.talent_repo.search_by_vector_similarity(
                query_embedding=query_vector,
                similarity_threshold=settings.RECOMMEND_SIMILARITY_THRESHOLD,
                filters=filters,
                limit=limit,
                vector_type="research",
            )

            # 转换为 RecommendResultItem
            results = []
            for item in items:
                results.append(
                    RecommendResultItem(
                        talent_id=item["talent_id"],
                        name=item["name"],
                        title=item.get("title") or "",
                        school_name=item.get("school_name") or "",
                        education_school_name=item.get("education_school_name"),
                        company_school_name=item.get("company_school_name"),
                        similarity_score=item.get("similarity_score", 0),
                        reasons=self._generate_reasons_for_similarity(
                            item.get("similarity_score", 0)
                        ),
                    )
                )

            return results

        except Exception as e:
            logger.warning(f"Vector similarity search failed: {e}")
            return []

    async def _find_similar_by_tags(
        self,
        reference_talents: list[Talent],
        limit: int,
        filters: dict[str, Any],
    ) -> list[RecommendResultItem]:
        """
        使用标签重叠查找相似人才（降级方案，使用 GIN 索引优化）

        优化策略：
        1. 收集参考人才的研究方向关键词
        2. 使用 pg_trgm GIN 索引在数据库层面预筛选有重叠的候选人
        3. 只对预筛选后的候选人计算精确相似度
        """
        # 收集参考人才的标签和研究方向
        ref_tags = set()
        ref_topics = set()
        for t in reference_talents:
            if t.topic_tags:
                ref_tags.update(tag.lower() for tag in t.topic_tags)
            if t.openalex_topics:
                ref_topics.update(topic.lower() for topic in t.openalex_topics)

        if not ref_tags and not ref_topics:
            logger.warning("No tags or topics found in reference talents")
            return []

        # 使用 GIN 索引在数据库层面预筛选候选人
        exclude_ids = filters.get("exclude_ids", [])

        # 构建参数字典
        params: dict[str, Any] = {}
        param_idx = 0

        # 排除参考人才 - 使用 ANY 数组语法
        exclude_clause = ""
        if exclude_ids:
            exclude_clause = "AND t.talent_id != ALL(:exclude_ids)"
            params["exclude_ids"] = list(exclude_ids)

        # 学校筛选
        school_clause = ""
        if "school_ids" in filters:
            school_clause = "AND t.school_id = ANY(:school_ids)"
            params["school_ids"] = list(filters["school_ids"])

        # 研究方向匹配条件（使用 pg_trgm GIN 索引）
        topic_conditions = []
        for topic in ref_topics:
            param_name = f"topic_{param_idx}"
            topic_conditions.append(f"t.openalex_topics::text ILIKE :{param_name}")
            params[param_name] = f"%{topic}%"
            param_idx += 1

        if not topic_conditions:
            return []

        topics_sql = " OR ".join(topic_conditions)

        # Safe: topics_sql uses parameterized placeholders, exclude/school_clauses use whitelisted fields
        query_str = f"""
            SELECT DISTINCT ON (t.talent_id) t.talent_id, t.name, t.current_title,
                   t.openalex_topics, t.topic_tags, t.cited_by_count,
                   s.school_name,
                   es.school_name AS education_school_name,
                   cs.school_name AS company_school_name
            FROM core_talent t
            LEFT JOIN core_school s ON t.school_id = s.school_id
            LEFT JOIN core_school es ON t.education_school_id = es.school_id
            LEFT JOIN core_school cs ON t.company_school_id = cs.school_id
            WHERE t.is_visible = TRUE
            {exclude_clause}
            {school_clause}
            AND ({topics_sql})
            ORDER BY t.talent_id, t.cited_by_count DESC
            LIMIT :limit
        """
        params["limit"] = limit * 5

        result = await self.session.execute(text(query_str), params)
        candidates = result.fetchall()

        if not candidates:
            return []

        # 计算精确相似度并排序
        items = []
        for row in candidates:
            # 计算 Jaccard 相似度
            cand_topics = set()
            if row.openalex_topics:
                try:
                    topics_list = (
                        json.loads(row.openalex_topics)
                        if isinstance(row.openalex_topics, str)
                        else row.openalex_topics
                    )
                    cand_topics = {t.lower() for t in topics_list}
                except (json.JSONDecodeError, TypeError):
                    pass

            cand_tags = set()
            if row.topic_tags:
                try:
                    tags_list = (
                        json.loads(row.topic_tags)
                        if isinstance(row.topic_tags, str)
                        else row.topic_tags
                    )
                    cand_tags = {t.lower() for t in tags_list}
                except (json.JSONDecodeError, TypeError):
                    pass

            # 计算相似度
            score = 0.0
            if ref_topics and cand_topics:
                topic_overlap = len(ref_topics & cand_topics) / len(ref_topics)
                score += topic_overlap * settings.RECOMMEND_RESEARCH_WEIGHT

            if ref_tags and cand_tags:
                tag_overlap = len(ref_tags & cand_tags) / len(ref_tags)
                score += tag_overlap * settings.RECOMMEND_TAG_WEIGHT

            if score > 0:
                items.append(
                    RecommendResultItem(
                        talent_id=row.talent_id,
                        name=row.name,
                        title=row.current_title or "",
                        school_name=row.school_name or "",
                        education_school_name=row.education_school_name,
                        company_school_name=row.company_school_name,
                        similarity_score=score,
                        reasons=self._generate_reasons_for_similarity(score),
                    )
                )

        # 按相似度排序
        items.sort(key=lambda x: x.similarity_score, reverse=True)
        return items[:limit]

    def _generate_reasons_for_similarity(self, similarity_score: float) -> list[str]:
        """根据相似度生成推荐原因"""
        if similarity_score >= 0.8:
            return ["高度相似：研究方向和技能高度匹配"]
        elif similarity_score >= 0.6:
            return ["中等相似：部分研究方向匹配"]
        elif similarity_score > 0:
            return ["部分匹配：有一定相似性"]
        return []

    def generate_reasons(
        self,
        similarity_score: float,
        reference_talent: dict[str, Any],
        candidate_talent: dict[str, Any],
    ) -> list[str]:
        """
        生成推荐原因

        Args:
            similarity_score: 相似度分数
            reference_talent: 参考人才
            candidate_talent: 候选人才

        Returns:
            List[str]: 推荐原因列表
        """
        return self._generate_reasons_for_similarity(similarity_score)
