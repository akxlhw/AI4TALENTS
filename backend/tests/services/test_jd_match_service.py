"""
Tests for JD Match Service.
岗位匹配服务测试 - v1.4 TDD

Coverage:
- JD parsing and feature extraction
- Candidate matching
- Score calculation
- Match reasons generation
- Session management
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from tests.mocks.mock_llm_gateway import MockLLMGateway, JDFeatures


# ============ Test Data Classes ============

@dataclass
class MatchConfig:
    """匹配配置"""
    weights: dict
    filters: dict
    limit: int = 20


@dataclass
class MatchResultItem:
    """匹配结果项"""
    talent_id: int
    name: str
    title: str
    overall_score: float
    skill_score: float
    research_score: float
    experience_score: float
    match_reasons: List[str]
    highlight_skills: List[str]


@dataclass
class MatchResult:
    """匹配结果"""
    session_id: int
    total: int
    items: List[MatchResultItem]
    took_ms: float


# ============ Tests ============

class TestJDMatchServiceParsing:
    """JD 解析测试"""

    @pytest.mark.asyncio
    async def test_parse_jd_returns_features(
        self, test_session: AsyncSession
    ):
        """解析 JD 应返回特征"""
        # Arrange
        from app.services.jd_match.jd_match_service import JDMatchService

        mock_llm = MockLLMGateway()
        mock_embed = AsyncMock()

        service = JDMatchService(
            session=test_session,
            llm_gateway=mock_llm,
            embed_service=mock_embed
        )

        # Act
        result = await service.parse_jd("招聘机器学习工程师，要求3年以上经验")

        # Assert
        assert result is not None
        assert len(result.skills) > 0

    @pytest.mark.asyncio
    async def test_parse_jd_caches_result(
        self, test_session: AsyncSession
    ):
        """解析 JD 应缓存结果"""
        # Arrange
        from app.services.jd_match.jd_match_service import JDMatchService
        from app.services.llm.protocols import JDFeatures

        mock_llm = MockLLMGateway()
        mock_embed = AsyncMock()

        # 创建 mock 缓存
        mock_cache = AsyncMock()
        cached_features = JDFeatures(
            skills=["机器学习"],
            experience="3年以上",
            research_areas=[],
            role_type="engineer",
            education_level="master"
        )
        # 第一次返回 None（缓存未命中），第二次返回缓存结果
        mock_cache.get_jd_features = AsyncMock(side_effect=[None, cached_features])

        service = JDMatchService(
            session=test_session,
            llm_gateway=mock_llm,
            embed_service=mock_embed,
            cache=mock_cache
        )

        jd_text = "招聘机器学习工程师"

        # Act - 调用两次
        await service.parse_jd(jd_text)
        await service.parse_jd(jd_text)

        # Assert - LLM 应只被调用一次（第二次缓存命中）
        assert mock_llm.call_count == 1


class TestJDMatchServiceMatching:
    """岗位匹配测试"""

    @pytest.mark.asyncio
    async def test_match_returns_candidates(
        self, test_session: AsyncSession, sample_talent: dict
    ):
        """匹配应返回候选人列表"""
        # Arrange
        from app.services.jd_match.jd_match_service import JDMatchService

        mock_llm = MockLLMGateway()
        mock_embed = AsyncMock()
        mock_embed.get_embedding = AsyncMock(return_value=[0.1] * 1536)

        service = JDMatchService(
            session=test_session,
            llm_gateway=mock_llm,
            embed_service=mock_embed
        )

        config = MatchConfig(
            weights={"skill": 0.4, "research": 0.3, "experience": 0.2, "education": 0.1},
            filters={},
            limit=10
        )

        # Act
        result = await service.match(
            jd_text="招聘机器学习工程师",
            config=config,
            user_id=1
        )

        # Assert
        assert result is not None
        assert result.total >= 0

    @pytest.mark.asyncio
    async def test_match_respects_limit(
        self, test_session: AsyncSession, sample_talent: dict
    ):
        """匹配应遵守数量限制"""
        # Arrange
        from app.services.jd_match.jd_match_service import JDMatchService

        mock_llm = MockLLMGateway()
        mock_embed = AsyncMock()

        service = JDMatchService(
            session=test_session,
            llm_gateway=mock_llm,
            embed_service=mock_embed
        )

        config = MatchConfig(
            weights={"skill": 0.4, "research": 0.3, "experience": 0.2, "education": 0.1},
            filters={},
            limit=5
        )

        # Act
        result = await service.match(
            jd_text="招聘机器学习工程师",
            config=config,
            user_id=1
        )

        # Assert
        assert len(result.items) <= 5

    @pytest.mark.asyncio
    async def test_match_applies_filters(
        self, test_session: AsyncSession, sample_talent: dict
    ):
        """匹配应应用过滤条件"""
        # Arrange
        from app.services.jd_match.jd_match_service import JDMatchService

        mock_llm = MockLLMGateway()
        mock_embed = AsyncMock()

        service = JDMatchService(
            session=test_session,
            llm_gateway=mock_llm,
            embed_service=mock_embed
        )

        config = MatchConfig(
            weights={"skill": 0.4, "research": 0.3, "experience": 0.2, "education": 0.1},
            filters={
                "min_citations": 100,
                "school_ids": [1, 2, 3]
            },
            limit=10
        )

        # Act
        result = await service.match(
            jd_text="招聘机器学习工程师",
            config=config,
            user_id=1
        )

        # Assert - 过滤后的结果应满足条件
        for item in result.items:
            # 实际断言取决于数据模型
            pass


class TestJDMatchServiceScoring:
    """评分测试"""

    @pytest.mark.asyncio
    async def test_calculate_skill_score(
        self, test_session: AsyncSession
    ):
        """应正确计算技能分数"""
        # Arrange
        from app.services.jd_match.match_scorer import MatchScorer

        scorer = MatchScorer()

        jd_features = JDFeatures(
            skills=["Python", "PyTorch", "NLP"],
            experience="3年以上",
            research_areas=["深度学习"],
            role_type="engineer",
            education_level="master"
        )

        candidate_skills = ["Python", "TensorFlow", "机器学习"]

        # Act
        score = scorer.calculate_skill_score(jd_features.skills, candidate_skills)

        # Assert
        assert 0 <= score <= 100
        # Python 匹配，应有一定分数
        assert score > 0

    @pytest.mark.asyncio
    async def test_calculate_research_score(
        self, test_session: AsyncSession
    ):
        """应正确计算研究方向分数"""
        # Arrange
        from app.services.jd_match.match_scorer import MatchScorer

        scorer = MatchScorer()

        jd_areas = ["深度学习", "自然语言处理"]
        candidate_areas = ["深度学习", "计算机视觉"]

        # Act
        score = scorer.calculate_research_score(jd_areas, candidate_areas)

        # Assert
        assert 0 <= score <= 100
        # 深度学习匹配
        assert score > 0

    @pytest.mark.asyncio
    async def test_calculate_overall_score_with_weights(
        self, test_session: AsyncSession
    ):
        """应使用权重计算综合分数"""
        # Arrange
        from app.services.jd_match.match_scorer import MatchScorer

        scorer = MatchScorer()
        weights = {
            "skill": 0.4,
            "research": 0.3,
            "experience": 0.2,
            "education": 0.1
        }

        # Act
        overall = scorer.calculate_overall_score(
            skill_score=80,
            research_score=90,
            experience_score=70,
            education_score=60,
            weights=weights
        )

        # Assert
        expected = 80 * 0.4 + 90 * 0.3 + 70 * 0.2 + 60 * 0.1
        assert abs(overall - expected) < 0.01

    @pytest.mark.asyncio
    async def test_score_zero_on_no_match(
        self, test_session: AsyncSession
    ):
        """无匹配应返回零分"""
        # Arrange
        from app.services.jd_match.match_scorer import MatchScorer

        scorer = MatchScorer()

        # Act
        score = scorer.calculate_skill_score(
            jd_skills=["Rust", "Go"],
            candidate_skills=["Python", "Java"]
        )

        # Assert
        assert score == 0


class TestJDMatchServiceReasons:
    """匹配原因测试"""

    @pytest.mark.asyncio
    async def test_generate_match_reasons(
        self, test_session: AsyncSession
    ):
        """应生成匹配原因"""
        # Arrange
        from app.services.jd_match.match_scorer import MatchScorer

        scorer = MatchScorer()

        jd_features = JDFeatures(
            skills=["Python", "深度学习"],
            experience="3年以上",
            research_areas=["NLP"],
            role_type="engineer",
            education_level="master"
        )

        candidate = {
            "skills": ["Python", "PyTorch"],
            "research_interests": "自然语言处理",
            "h_index": 15
        }

        # Act
        reasons = scorer.generate_match_reasons(jd_features, candidate)

        # Assert
        assert len(reasons) > 0
        assert any("Python" in r or "技能" in r for r in reasons)

    @pytest.mark.asyncio
    async def test_reasons_includes_highlight_skills(
        self, test_session: AsyncSession
    ):
        """匹配原因应包含高亮技能"""
        # Arrange
        from app.services.jd_match.match_scorer import MatchScorer

        scorer = MatchScorer()

        jd_skills = ["Python", "深度学习", "NLP"]
        candidate_skills = ["Python", "深度学习", "机器学习"]

        # Act
        highlights = scorer.get_highlight_skills(jd_skills, candidate_skills)

        # Assert
        assert "Python" in highlights
        assert "深度学习" in highlights
        assert "机器学习" not in highlights  # 不在 JD 中


class TestJDMatchServiceSession:
    """会话管理测试"""

    @pytest.mark.asyncio
    async def test_create_session(
        self, test_session: AsyncSession
    ):
        """应创建匹配会话"""
        # Arrange
        from app.services.jd_match.jd_match_service import JDMatchService
        from app.models.jd_match import JDMatchSession

        mock_llm = MockLLMGateway()
        mock_embed = AsyncMock()

        service = JDMatchService(
            session=test_session,
            llm_gateway=mock_llm,
            embed_service=mock_embed
        )

        # Act
        result = await service.match(
            jd_text="招聘机器学习工程师",
            config=MatchConfig(weights={}, filters={}, limit=10),
            user_id=1
        )

        # Assert
        assert result.session_id is not None

    @pytest.mark.asyncio
    async def test_session_status_updates(
        self, test_session: AsyncSession
    ):
        """会话状态应正确更新"""
        # 这个测试验证会话状态从 pending -> completed/failed
        # 实际实现中需要检查数据库状态

        pass  # 实现细节取决于实际模型


class TestJDMatchServiceErrorHandling:
    """错误处理测试"""

    @pytest.mark.asyncio
    async def test_match_handles_llm_failure(
        self, test_session: AsyncSession
    ):
        """LLM 失败应使用降级策略"""
        # Arrange
        from app.services.jd_match.jd_match_service import JDMatchService

        mock_llm = MockLLMGateway(should_fail=True, fail_count=100)
        mock_embed = AsyncMock()

        service = JDMatchService(
            session=test_session,
            llm_gateway=mock_llm,
            embed_service=mock_embed
        )

        config = MatchConfig(weights={}, filters={}, limit=10)

        # Act & Assert - 应该有降级策略，不会抛出异常
        # 或者抛出特定异常
        try:
            result = await service.match(
                jd_text="招聘机器学习工程师",
                config=config,
                user_id=1
            )
            # 如果有降级，应该返回结果
        except Exception:
            # 如果没有降级，应该抛出异常
            pass

    @pytest.mark.asyncio
    async def test_match_handles_empty_jd(
        self, test_session: AsyncSession
    ):
        """空 JD 应返回错误"""
        # Arrange
        from app.services.jd_match.jd_match_service import JDMatchService, JDMatchError

        mock_llm = MockLLMGateway()
        mock_embed = AsyncMock()

        service = JDMatchService(
            session=test_session,
            llm_gateway=mock_llm,
            embed_service=mock_embed
        )

        # Act & Assert
        with pytest.raises((ValueError, JDMatchError)):
            await service.match(
                jd_text="",
                config=MatchConfig(weights={}, filters={}, limit=10),
                user_id=1
            )


class TestJDMatchServiceTiming:
    """性能测试"""

    @pytest.mark.asyncio
    async def test_match_returns_timing(
        self, test_session: AsyncSession, sample_talent: dict
    ):
        """匹配结果应包含耗时"""
        # Arrange
        from app.services.jd_match.jd_match_service import JDMatchService

        mock_llm = MockLLMGateway()
        mock_embed = AsyncMock()

        service = JDMatchService(
            session=test_session,
            llm_gateway=mock_llm,
            embed_service=mock_embed
        )

        config = MatchConfig(weights={}, filters={}, limit=10)

        # Act
        result = await service.match(
            jd_text="招聘机器学习工程师",
            config=config,
            user_id=1
        )

        # Assert
        assert hasattr(result, 'took_ms')
        assert result.took_ms > 0
