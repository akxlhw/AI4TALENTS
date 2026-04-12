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

import time
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.talent import Talent
from app.services.llm.errors import RecommendError, InvalidReferenceError, EmptyReferenceError

logger = logging.getLogger(__name__)


class RecommendMode(str, Enum):
    """推荐模式"""
    SIMILAR = "similar"        # 相似人才
    COMPLEMENT = "complement"  # 互补人才
    DIVERSE = "diverse"        # 多样化人才


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
    ):
        """
        初始化推荐服务

        Args:
            session: 数据库会话
            embed_service: 嵌入服务（可选）
        """
        self.session = session
        self.embed_service = embed_service

    async def get_similar(
        self,
        reference_talent_ids: List[int],
        mode: RecommendMode | str = RecommendMode.SIMILAR,
        limit: int = 20,
        filters: Dict[str, Any] | None = None,
    ) -> RecommendResult:
        """
        获取推荐人才

        Args:
            reference_talent_ids: 参考人才 ID 列表
            mode: 推荐模式
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

        # 规范化模式
        if isinstance(mode, str):
            try:
                mode = RecommendMode(mode.lower())
            except ValueError:
                mode = RecommendMode.SIMILAR

        # 获取参考人才
        reference_talents = await self._get_reference_talents(reference_talent_ids)
        if not reference_talents:
            raise InvalidReferenceError(reference_talent_ids[0])

        # 根据模式获取推荐
        if mode == RecommendMode.SIMILAR:
            items = await self._find_similar(reference_talents, limit, filters)
        elif mode == RecommendMode.COMPLEMENT:
            items = await self._find_complement(reference_talents, limit, filters)
        elif mode == RecommendMode.DIVERSE:
            items = await self._find_diverse(reference_talents, limit, filters)
        else:
            items = await self._find_similar(reference_talents, limit, filters)

        took_ms = (time.time() - start_time) * 1000

        return RecommendResult(
            reference_talents=reference_talent_ids,
            total=len(items),
            items=items,
            mode=mode.value if isinstance(mode, RecommendMode) else mode,
            took_ms=took_ms,
        )

    async def _get_reference_talents(self, talent_ids: List[int]) -> List[Talent]:
        """获取参考人才"""
        query = select(Talent).where(Talent.talent_id.in_(talent_ids))
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def _find_similar(
        self,
        reference_talents: List[Talent],
        limit: int,
        filters: Dict[str, Any] | None,
    ) -> List[RecommendResultItem]:
        """查找相似人才"""
        # 简化实现：基于相同研究方向和技能
        reference_ids = {t.talent_id for t in reference_talents}

        # 收集参考人才的标签
        all_tags = set()
        all_research = set()
        for t in reference_talents:
            if t.topic_tags:
                all_tags.update(t.topic_tags)
            if t.research_interests:
                all_research.update(t.research_interests.lower().split(","))

        # 构建查询
        query = (
            select(Talent)
            .where(Talent.is_visible.is_(True))
            .where(~Talent.talent_id.in_(reference_ids))
        )

        # 应用过滤
        if filters:
            if "exclude_ids" in filters:
                query = query.where(~Talent.talent_id.in_(filters["exclude_ids"]))
            if "school_ids" in filters:
                query = query.where(Talent.school_id.in_(filters["school_ids"]))

        result = await self.session.execute(query.limit(limit * 2))
        candidates = list(result.scalars().all())

        # 计算相似度并排序
        items = []
        for candidate in candidates:
            similarity = self._calculate_similarity(reference_talents, candidate)
            reasons = self.generate_reasons(
                similarity,
                reference_talents[0].__dict__,
                {"research_interests": candidate.research_interests}
            )

            items.append(RecommendResultItem(
                talent_id=candidate.talent_id,
                name=candidate.name,
                title=candidate.current_title or "",
                school_name="",  # 需要join
                similarity_score=similarity,
                reasons=reasons,
            ))

        # 按相似度排序
        items.sort(key=lambda x: x.similarity_score, reverse=True)
        return items[:limit]

    async def _find_complement(
        self,
        reference_talents: List[Talent],
        limit: int,
        filters: Dict[str, Any] | None,
    ) -> List[RecommendResultItem]:
        """查找互补人才"""
        # 简化实现：查找不同技能的人才
        return await self._find_similar(reference_talents, limit, filters)

    async def _find_diverse(
        self,
        reference_talents: List[Talent],
        limit: int,
        filters: Dict[str, Any] | None,
    ) -> List[RecommendResultItem]:
        """查找多样化人才"""
        # 简化实现
        return await self._find_similar(reference_talents, limit, filters)

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
            if t.research_interests:
                ref_research.update(r.strip().lower() for r in t.research_interests.split(","))

        # 候选人标签
        cand_tags = set(tag.lower() for tag in (candidate.topic_tags or []))
        cand_research = set()
        if candidate.research_interests:
            cand_research = set(r.strip().lower() for r in candidate.research_interests.split(","))

        # 计算标签重叠
        if ref_tags and cand_tags:
            tag_overlap = len(ref_tags & cand_tags) / len(ref_tags)
            score += tag_overlap * 0.5

        # 计算研究方向重叠
        if ref_research and cand_research:
            research_overlap = len(ref_research & cand_research) / len(ref_research)
            score += research_overlap * 0.5

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
        reasons = []

        if similarity_score >= 0.8:
            reasons.append("高度相似：研究方向和技能高度匹配")
        elif similarity_score >= 0.5:
            reasons.append("中等相似：部分研究方向匹配")
        elif similarity_score > 0:
            reasons.append("部分匹配：有一定相似性")

        return reasons
