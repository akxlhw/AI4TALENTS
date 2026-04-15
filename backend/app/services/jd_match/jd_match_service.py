"""
JD Match Service implementation.
岗位匹配服务实现 - v1.4.1

Features:
- JD parsing via LLM (simplified to research_areas only)
- Candidate matching (research direction + paper titles)
- Score calculation (simplified to research score only)
- Match reasons generation
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set

from sqlalchemy import select, and_, or_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.talent import Talent
from app.models.raw_data import RawWork
from app.models.standardized import StdAuthor
from app.services.llm.protocols import LLMGatewayProtocol, JDFeatures
from app.services.llm.errors import JDMatchError, EmptyJDError
from app.services.jd_match.match_scorer import MatchScorer
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class MatchConfig:
    """匹配配置

    v1.4.1: Simplified to research matching only

    权重配置统一在 settings.JD_MATCH_WEIGHTS 中管理
    """
    weights: Dict[str, float] = field(default_factory=lambda: settings.JD_MATCH_WEIGHTS.copy())
    filters: Dict[str, Any] = field(default_factory=dict)
    limit: int = 20


@dataclass
class MatchResultItem:
    """匹配结果项"""
    talent_id: int
    name: str
    title: str
    school_name: str
    overall_score: float
    research_score: float
    match_reasons: List[str]

    def to_dict(self) -> dict:
        return {
            "talent_id": self.talent_id,
            "name": self.name,
            "title": self.title,
            "school_name": self.school_name,
            "overall_score": self.overall_score,
            "research_score": self.research_score,
            "match_reasons": self.match_reasons,
        }


@dataclass
class MatchResult:
    """匹配结果"""
    session_id: int
    total: int
    items: List[MatchResultItem]
    took_ms: float

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "total": self.total,
            "items": [item.to_dict() for item in self.items],
            "took_ms": self.took_ms,
        }


class JDMatchService:
    """岗位匹配服务

    负责解析职位描述(JD)并匹配候选人。

    v1.4.1: Simplified to research direction matching only
    - Matches research_areas against openalex_topics (research direction)
    - Matches research_areas against paper titles (RawWork.title)
    """

    def __init__(
        self,
        session: AsyncSession,
        llm_gateway: LLMGatewayProtocol,
        embed_service: Any = None,
        cache: Any = None,
    ):
        """
        初始化岗位匹配服务

        Args:
            session: 数据库会话
            llm_gateway: LLM 网关
            embed_service: 嵌入服务（可选）
            cache: 缓存管理器（可选）
        """
        self.session = session
        self.llm_gateway = llm_gateway
        self.embed_service = embed_service
        self.cache = cache
        self._scorer = MatchScorer()
        self._session_counter = 0  # 简化的会话计数器

    async def parse_jd(self, jd_text: str) -> JDFeatures:
        """
        解析 JD 文本

        Args:
            jd_text: JD 文本内容

        Returns:
            JDFeatures: 解析出的特征
        """
        # 检查缓存
        if self.cache:
            cached = await self.cache.get_jd_features(jd_text)
            if cached:
                return cached

        # 调用 LLM 解析（带 fallback）
        features = await self.llm_gateway.parse_jd_with_fallback(jd_text)

        # 写入缓存
        if self.cache:
            await self.cache.set_jd_features(jd_text, features)

        return features

    async def match(
        self,
        jd_text: str,
        config: MatchConfig,
        user_id: int,
    ) -> MatchResult:
        """
        执行岗位匹配

        Args:
            jd_text: JD 文本
            config: 匹配配置
            user_id: 用户 ID

        Returns:
            MatchResult: 匹配结果

        Raises:
            EmptyJDError: JD 文本为空
        """
        start_time = time.time()

        # 验证 JD
        if not jd_text or not jd_text.strip():
            raise EmptyJDError()

        # 创建会话
        self._session_counter += 1
        session_id = self._session_counter

        try:
            # 解析 JD
            jd_features = await self.parse_jd(jd_text)

            # 获取候选人及其论文标题
            candidates = await self._get_candidates_with_papers(jd_features, config)

            # 计算分数
            items = await self._calculate_scores(jd_features, candidates, config)

            # 按分数排序并限制数量
            items.sort(key=lambda x: x.overall_score, reverse=True)
            items = items[:config.limit]

            took_ms = (time.time() - start_time) * 1000

            return MatchResult(
                session_id=session_id,
                total=len(items),
                items=items,
                took_ms=took_ms,
            )

        except Exception as e:
            logger.error(f"JD match failed: {e}")
            raise

    async def _get_candidates_with_papers(
        self,
        jd_features: JDFeatures,
        config: MatchConfig,
    ) -> List[Dict[str, Any]]:
        """获取候选人列表及其论文标题

        Returns:
            List of dicts with keys: talent, paper_titles, openalex_topics
        """
        # 基础查询：获取可见人才
        query = (
            select(Talent)
            .options(joinedload(Talent.school))
            .where(Talent.is_visible.is_(True))
        )

        # 应用过滤条件
        filters = config.filters
        if "school_ids" in filters:
            query = query.where(Talent.school_id.in_(filters["school_ids"]))

        if "min_citations" in filters:
            query = query.where(Talent.cited_by_count >= filters["min_citations"])

        result = await self.session.execute(query.limit(100))
        talents = list(result.scalars().all())

        # 获取每个人才的论文标题
        candidates = []
        for talent in talents:
            # 获取论文标题
            paper_titles = await self._get_paper_titles_for_talent(talent)

            candidates.append({
                "talent": talent,
                "paper_titles": paper_titles,
                "openalex_topics": talent.openalex_topics or [],
            })

        return candidates

    async def _get_paper_titles_for_talent(self, talent: Talent) -> List[str]:
        """获取人才的论文标题列表

        数据路径: Talent.std_author_id → StdAuthor.openalex_author_id → RawWork.author_ids
        """
        if not talent.std_author_id:
            return []

        try:
            # 获取 StdAuthor 的 openalex_author_id
            std_author_query = select(StdAuthor.openalex_author_id).where(
                StdAuthor.std_author_id == talent.std_author_id
            )
            result = await self.session.execute(std_author_query)
            openalex_author_id = result.scalar_one_or_none()

            if not openalex_author_id:
                return []

            # 查询 RawWork 中包含该作者的论文标题
            # author_ids 是 JSON 数组字符串，使用 LIKE 模式匹配
            paper_query = select(RawWork.title).where(
                RawWork.author_ids.ilike(f'%"{openalex_author_id}"%')
            ).limit(20)  # 限制论文数量

            result = await self.session.execute(paper_query)
            titles = [row[0] for row in result.all() if row[0]]

            return titles

        except Exception as e:
            logger.warning(f"Failed to get paper titles for talent {talent.talent_id}: {e}")
            return []

    async def _calculate_scores(
        self,
        jd_features: JDFeatures,
        candidates: List[Dict[str, Any]],
        config: MatchConfig,
    ) -> List[MatchResultItem]:
        """计算匹配分数

        v1.4.1: Only calculate research score
        - Match against openalex_topics (research direction)
        - Match against paper_titles (paper titles)
        """
        items = []

        for candidate in candidates:
            talent = candidate["talent"]
            paper_titles = candidate["paper_titles"]
            openalex_topics = candidate["openalex_topics"]

            # 合并研究方向和论文标题作为匹配范围
            # openalex_topics 是研究方向，paper_titles 是论文标题
            all_matchable = openalex_topics + paper_titles

            logger.debug(
                f"Candidate {talent.name}: "
                f"openalex_topics={openalex_topics[:3]}..., "
                f"paper_titles_count={len(paper_titles)}"
            )

            # 计算研究方向匹配分数
            research_score = self._scorer.calculate_research_score(
                jd_features.research_areas, all_matchable
            )

            # 调试日志
            logger.info(
                f"JD research_areas: {jd_features.research_areas}, "
                f"candidate matchable: {len(all_matchable)} items, "
                f"research_score: {research_score:.1f}"
            )

            # 综合分数 = 研究方向分数（v1.4.1 简化）
            overall_score = research_score

            # 生成匹配原因
            match_reasons = self._scorer.generate_match_reasons(
                jd_features,
                {
                    "research_topics": openalex_topics,
                    "paper_titles": paper_titles,
                    "h_index": talent.h_index,
                }
            )

            item = MatchResultItem(
                talent_id=talent.talent_id,
                name=talent.name,
                title=talent.current_title or "",
                school_name=talent.school.school_name if talent.school else "",
                overall_score=overall_score,
                research_score=research_score,
                match_reasons=match_reasons,
            )
            items.append(item)

        return items
