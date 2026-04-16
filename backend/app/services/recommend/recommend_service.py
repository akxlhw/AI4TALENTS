"""
Recommend Service implementation.
推荐服务实现 - v1.4

Features:
- Similar talent recommendation
- Complement recommendation
- Diverse recommendation
- Vector similarity calculation
"""

from __future__ import annotations

import json
import time
import logging
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.talent import Talent
from app.models.embedding import TalentEmbedding
from app.repositories.talent_repository import TalentRepository
from app.services.llm.errors import RecommendError, InvalidReferenceError, EmptyReferenceError
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class RecommendResultItem:
    """推荐结果项"""
    talent_id: int
    name: str
    title: str
    school_name: str
    similarity_score: float
    reasons: List[str]

    def to_dict(self) -> dict:
        return {
            "talent_id": self.talent_id,
            "name": self.name,
            "title": self.title,
            "school_name": self.school_name,
            "similarity_score": self.similarity_score,
            "reasons": self.reasons,
        }


@dataclass
class RecommendResult:
    """推荐结果"""
    reference_talents: List[int]
    total: int
    items: List[RecommendResultItem]
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

    async def get_similar(
        self,
        reference_talent_ids: List[int],
        limit: int = 20,
        filters: Dict[str, Any] | None = None,
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

    async def _get_reference_talents(self, talent_ids: List[int]) -> List[Talent]:
        """获取参考人才"""
        if not talent_ids:
            return []

        # 使用 Repository 的批量查询方法
        return await self.talent_repo.get_by_ids(talent_ids, include_relations=True)

    async def _find_similar(
        self,
        reference_talents: List[Talent],
        limit: int,
        filters: Dict[str, Any] | None,
    ) -> List[RecommendResultItem]:
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
            items = await self._find_similar_by_vector(
                reference_talents, limit, search_filters
            )
            if items:
                return items

        # 降级到标签匹配
        return await self._find_similar_by_tags(reference_talents, limit, search_filters)

    async def _find_similar_by_vector(
        self,
        reference_talents: List[Talent],
        limit: int,
        filters: Dict[str, Any],
    ) -> List[RecommendResultItem]:
        """使用向量相似度查找相似人才"""
        try:
            # 获取参考人才的嵌入向量
            reference_ids = [t.talent_id for t in reference_talents]
            query = (
                select(TalentEmbedding.talent_id, TalentEmbedding.embedding)
                .where(TalentEmbedding.talent_id.in_(reference_ids))
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
                    logger.warning(f"Failed to parse embedding as JSON, trying comma-separated format")
                    try:
                        # 移除可能的方括号
                        clean_str = emb_str.strip('[]')
                        vec = [float(x) for x in clean_str.split(',') if x.strip()]
                        vectors.append(vec)
                    except ValueError as e:
                        logger.error(f"Failed to parse embedding: {e}")
                        continue

            if not vectors:
                logger.warning("No valid embeddings found for reference talents")
                return []

            query_vector = np.mean(vectors, axis=0).tolist()

            # 使用 Repository 进行向量搜索
            items, _ = await self.talent_repo.search_by_vector_similarity(
                query_embedding=query_vector,
                similarity_threshold=settings.RECOMMEND_SIMILARITY_THRESHOLD,
                filters=filters,
                limit=limit,
            )

            # 转换为 RecommendResultItem
            results = []
            for item in items:
                results.append(RecommendResultItem(
                    talent_id=item["talent_id"],
                    name=item["name"],
                    title=item.get("title") or "",
                    school_name=item.get("school_name") or "",
                    similarity_score=item.get("similarity_score", 0),
                    reasons=self._generate_reasons_for_similarity(item.get("similarity_score", 0)),
                ))

            return results

        except Exception as e:
            logger.warning(f"Vector similarity search failed: {e}")
            return []

    async def _find_similar_by_tags(
        self,
        reference_talents: List[Talent],
        limit: int,
        filters: Dict[str, Any],
    ) -> List[RecommendResultItem]:
        """使用标签重叠查找相似人才（降级方案）"""
        # 收集参考人才的标签
        all_tags = set()
        all_research = set()
        for t in reference_talents:
            if t.topic_tags:
                all_tags.update(t.topic_tags)
            if t.openalex_topics:
                all_research.update(topic.lower() for topic in t.openalex_topics)

        # 构建查询
        query = (
            select(Talent)
            .where(Talent.is_visible.is_(True))
            .where(~Talent.talent_id.in_(filters.get("exclude_ids", [])))
        )

        if "school_ids" in filters:
            query = query.where(Talent.school_id.in_(filters["school_ids"]))

        result = await self.session.execute(query.limit(limit * 3))
        candidates = list(result.scalars().all())

        # 计算相似度并排序
        items = []
        for candidate in candidates:
            similarity = self._calculate_similarity(reference_talents, candidate)
            if similarity > 0:
                items.append(RecommendResultItem(
                    talent_id=candidate.talent_id,
                    name=candidate.name,
                    title=candidate.current_title or "",
                    school_name=candidate.school.school_name if candidate.school else "",
                    similarity_score=similarity,
                    reasons=self._generate_reasons_for_similarity(similarity),
                ))

        # 按相似度排序
        items.sort(key=lambda x: x.similarity_score, reverse=True)
        return items[:limit]

    def _generate_reasons_for_similarity(self, similarity_score: float) -> List[str]:
        """根据相似度生成推荐原因"""
        if similarity_score >= 0.8:
            return ["高度相似：研究方向和技能高度匹配"]
        elif similarity_score >= 0.6:
            return ["中等相似：部分研究方向匹配"]
        elif similarity_score > 0:
            return ["部分匹配：有一定相似性"]
        return []


    def _calculate_similarity(
        self,
        reference_talents: List[Talent],
        candidate: Talent,
    ) -> float:
        """
        计算相似度

        Args:
            reference_talents: 参考人才列表
            candidate: 候选人才

        Returns:
            float: 0-1 的相似度分数
        """
        score = 0.0

        # 收集参考人才的标签
        ref_tags = set()
        ref_research = set()
        for t in reference_talents:
            if t.topic_tags:
                ref_tags.update(tag.lower() for tag in t.topic_tags)
            if t.openalex_topics:
                ref_research.update(topic.lower() for topic in t.openalex_topics)

        # 候选人标签
        cand_tags = set(tag.lower() for tag in (candidate.topic_tags or []))
        cand_research = set()
        if candidate.openalex_topics:
            cand_research = set(topic.lower() for topic in candidate.openalex_topics)

        # 计算标签重叠
        if ref_tags and cand_tags:
            tag_overlap = len(ref_tags & cand_tags) / len(ref_tags)
            score += tag_overlap * settings.RECOMMEND_TAG_WEIGHT

        # 计算研究方向重叠
        if ref_research and cand_research:
            research_overlap = len(ref_research & cand_research) / len(ref_research)
            score += research_overlap * settings.RECOMMEND_RESEARCH_WEIGHT

        return score

    def generate_reasons(
        self,
        similarity_score: float,
        reference_talent: Dict[str, Any],
        candidate_talent: Dict[str, Any],
    ) -> List[str]:
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
