"""
JD Match Service implementation.
岗位匹配服务实现 - v1.4.1

Features:
- JD parsing via LLM (simplified to research_areas only)
- Candidate matching (research direction + paper titles)
- Score calculation (simplified to research score only)
- Match reasons generation
- Session persistence to database
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.jd_match import JDMatchResult, JDMatchSession
from app.repositories.talent_repository import TalentRepository
from app.services.jd_match.match_scorer import MatchScorer
from app.services.llm.errors import EmptyJDError
from app.services.llm.protocols import JDFeatures, LLMGatewayProtocol

logger = logging.getLogger(__name__)


@dataclass
class MatchConfig:
    """匹配配置

    v1.4.1: Simplified to research matching only

    权重配置统一在 settings.JD_MATCH_WEIGHTS 中管理
    """

    weights: dict[str, float] = field(default_factory=lambda: settings.JD_MATCH_WEIGHTS.copy())
    filters: dict[str, Any] = field(default_factory=dict)
    limit: int = 50


@dataclass
class MatchResultItem:
    """匹配结果项"""

    talent_id: int
    name: str
    title: str
    school_name: str
    overall_score: float
    research_score: float
    match_reasons: list[str]

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
    items: list[MatchResultItem]
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
        talent_repository: TalentRepository | None = None,
    ):
        """
        初始化岗位匹配服务

        Args:
            session: 数据库会话
            llm_gateway: LLM 网关
            embed_service: 嵌入服务（可选）
            cache: 缓存管理器（可选）
            talent_repository: 人才数据仓储（可选，默认自动创建）
        """
        self.session = session
        self.llm_gateway = llm_gateway
        self.embed_service = embed_service
        self.cache = cache
        self._scorer = MatchScorer()
        self._session_counter = 0  # 简化的会话计数器
        self.talent_repo = talent_repository or TalentRepository(session)

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

        # 创建数据库会话记录
        db_session = JDMatchSession(
            user_id=user_id,
            jd_text=jd_text,
            status="pending",
            created_at=datetime.utcnow(),
        )
        self.session.add(db_session)
        await self.session.flush()  # 获取 session_id
        session_id = db_session.session_id

        try:
            # 解析 JD
            jd_features = await self.parse_jd(jd_text)

            # 更新会话特征
            db_session.jd_features = (
                jd_features.to_dict()
                if hasattr(jd_features, "to_dict")
                else {
                    "research_areas": jd_features.research_areas,
                }
            )

            # 获取候选人及其论文标题
            candidates = await self._get_candidates_with_papers(jd_features, config)

            # 计算分数
            items = await self._calculate_scores(jd_features, candidates, config)

            # 按分数排序并限制数量
            items.sort(key=lambda x: x.overall_score, reverse=True)
            items = items[: config.limit]

            # 持久化匹配结果
            for item in items:
                result = JDMatchResult(
                    session_id=session_id,
                    talent_id=item.talent_id,
                    overall_score=item.overall_score,
                    research_score=item.research_score,
                    skill_score=None,
                    experience_score=None,
                    match_reasons=item.match_reasons,
                    highlight_skills=[],
                    created_at=datetime.utcnow(),
                )
                self.session.add(result)

            # 更新会话状态
            db_session.status = "completed"
            db_session.completed_at = datetime.utcnow()

            took_ms = (time.time() - start_time) * 1000

            # 提交事务
            await self.session.commit()

            return MatchResult(
                session_id=session_id,
                total=len(items),
                items=items,
                took_ms=took_ms,
            )

        except Exception as e:
            logger.error(f"JD match failed: {e}")
            # 更新会话状态为失败
            db_session.status = "failed"
            db_session.completed_at = datetime.utcnow()
            await self.session.commit()  # 保存失败状态
            raise

    async def _get_candidates_with_papers(
        self,
        jd_features: JDFeatures,
        config: MatchConfig,
    ) -> list[dict[str, Any]]:
        """根据 JD 关键词搜索匹配的候选人

        搜索范围：
        1. openalex_topics (研究方向)
        2. RawWork.title (论文标题)

        Returns:
            List of dicts with keys: talent, paper_titles, openalex_topics, matched_keywords
        """
        research_areas = jd_features.research_areas
        if not research_areas:
            logger.warning("No research areas extracted from JD, returning empty candidates")
            return []

        # 使用 Repository 进行综合搜索
        candidates = await self.talent_repo.search_by_research_keywords(
            keywords=research_areas,
            search_scope=["openalex_topics", "paper_titles"],
            filters=config.filters,
            limit=config.limit * 2,
        )

        logger.info(f"Found {len(candidates)} candidates matching JD keywords: {research_areas}")

        return candidates

    async def _calculate_scores(
        self,
        jd_features: JDFeatures,
        candidates: list[dict[str, Any]],
        config: MatchConfig,
    ) -> list[MatchResultItem]:
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
                },
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

    async def get_session(self, session_id: int) -> dict | None:
        """
        获取匹配会话详情

        Args:
            session_id: 会话 ID

        Returns:
            会话信息字典，包含结果列表
        """
        # 查询会话
        result = await self.session.execute(
            select(JDMatchSession).where(JDMatchSession.session_id == session_id)
        )
        db_session = result.scalar_one_or_none()

        if not db_session:
            return None

        # 查询结果
        results_result = await self.session.execute(
            select(JDMatchResult)
            .where(JDMatchResult.session_id == session_id)
            .order_by(JDMatchResult.overall_score.desc())
        )
        results = results_result.scalars().all()

        return {
            **db_session.to_dict(),
            "results": [r.to_dict() for r in results],
        }
