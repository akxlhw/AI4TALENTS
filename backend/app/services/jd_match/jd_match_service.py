"""
JD Match Service implementation.
岗位匹配服务实现 - v1.4

Features:
- JD parsing via LLM
- Candidate matching
- Score calculation
- Match reasons generation
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.talent import Talent
from app.services.llm.protocols import LLMGatewayProtocol, JDFeatures
from app.services.llm.errors import JDMatchError, EmptyJDError
from app.services.jd_match.match_scorer import MatchScorer

logger = logging.getLogger(__name__)


@dataclass
class MatchConfig:
    """匹配配置

    权重说明（v1.4 临时方案）：
    - skill: 技能匹配，基于 topic_tags
    - research: 研究方向匹配，基于 research_interests
    - experience: 经验匹配，暂无数据来源，固定 50 分
    - education: 学历匹配，暂无数据来源，固定 50 分

    TODO: 后续版本通过 ORCID API 补充教育背景，
          或从首篇论文年份推断学术年龄
    """
    weights: Dict[str, float] = field(default_factory=lambda: {
        "skill": 0.5,        # 提高：有可靠数据来源
        "research": 0.4,     # 提高：有可靠数据来源
        "experience": 0.05,  # 降低：暂无数据，固定 50 分
        "education": 0.05    # 降低：暂无数据，固定 50 分
    })
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
    skill_score: float
    research_score: float
    experience_score: float
    match_reasons: List[str]
    highlight_skills: List[str]

    def to_dict(self) -> dict:
        return {
            "talent_id": self.talent_id,
            "name": self.name,
            "title": self.title,
            "school_name": self.school_name,
            "overall_score": self.overall_score,
            "skill_score": self.skill_score,
            "research_score": self.research_score,
            "experience_score": self.experience_score,
            "match_reasons": self.match_reasons,
            "highlight_skills": self.highlight_skills,
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

        # 调用 LLM 解析
        features = await self.llm_gateway.parse_jd(jd_text)

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

            # 获取候选人
            candidates = await self._get_candidates(jd_features, config)

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

    async def _get_candidates(
        self,
        jd_features: JDFeatures,
        config: MatchConfig,
    ) -> List[Talent]:
        """获取候选人列表"""
        query = (
            select(Talent)
            .where(Talent.is_visible.is_(True))
        )

        # 应用过滤条件
        filters = config.filters
        if "school_ids" in filters:
            query = query.where(Talent.school_id.in_(filters["school_ids"]))

        if "min_citations" in filters:
            query = query.where(Talent.cited_by_count >= filters["min_citations"])

        result = await self.session.execute(query.limit(100))  # 限制候选数量
        return list(result.scalars().all())

    async def _calculate_scores(
        self,
        jd_features: JDFeatures,
        candidates: List[Talent],
        config: MatchConfig,
    ) -> List[MatchResultItem]:
        """计算匹配分数"""
        items = []

        for candidate in candidates:
            # 提取候选人技能
            candidate_skills = candidate.topic_tags or []
            candidate_research = []
            if candidate.research_interests:
                candidate_research = [s.strip() for s in candidate.research_interests.split(",")]

            # 计算各项分数
            skill_score = self._scorer.calculate_skill_score(
                jd_features.skills, candidate_skills
            )
            research_score = self._scorer.calculate_research_score(
                jd_features.research_areas, candidate_research
            )
            # v1.4 临时方案：experience 和 education 暂无数据来源
            # 后续版本可通过以下方式补充：
            # 1. ORCID API 获取教育背景
            # 2. 首篇论文年份推断学术年龄
            experience_score = 50.0
            education_score = 50.0

            # 计算综合分数
            overall_score = self._scorer.calculate_overall_score(
                skill_score=skill_score,
                research_score=research_score,
                experience_score=experience_score,
                education_score=education_score,
                weights=config.weights,
            )

            # 生成匹配原因
            match_reasons = self._scorer.generate_match_reasons(
                jd_features,
                {
                    "skills": candidate_skills,
                    "research_interests": candidate.research_interests,
                    "h_index": candidate.h_index,
                }
            )

            # 高亮技能
            highlight_skills = self._scorer.get_highlight_skills(
                jd_features.skills, candidate_skills
            )

            item = MatchResultItem(
                talent_id=candidate.talent_id,
                name=candidate.name,
                title=candidate.current_title or "",
                school_name="",  # 需要join获取
                overall_score=overall_score,
                skill_score=skill_score,
                research_score=research_score,
                experience_score=experience_score,
                match_reasons=match_reasons,
                highlight_skills=highlight_skills,
            )
            items.append(item)

        return items
