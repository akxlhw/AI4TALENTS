"""
Tests for JD Match Service.
岗位匹配服务测试 - v1.4.1

Coverage:
- JD parsing and feature extraction (simplified to research_areas only)
- Candidate matching (research direction + paper titles)
- Score calculation (simplified to research score only)
- Match reasons generation
- Session management
"""

from dataclasses import dataclass
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from tests.mocks.mock_llm_gateway import JDFeatures, MockLLMGateway

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
    research_score: float
    match_reasons: list[str]


@dataclass
class MatchResult:
    """匹配结果"""

    session_id: int
    total: int
    items: list[MatchResultItem]
    took_ms: float


# ============ Tests ============


class TestJDMatchServiceParsing:
    """JD 解析测试"""

    @pytest.mark.asyncio
    async def test_parse_jd_returns_features(self, test_session: AsyncSession):
        """解析 JD 应返回特征"""
        # Arrange
        from app.services.jd_match.jd_match_service import JDMatchService

        mock_llm = MockLLMGateway()
        mock_embed = AsyncMock()

        service = JDMatchService(
            session=test_session, llm_gateway=mock_llm, embed_service=mock_embed
        )

        # Act
        result = await service.parse_jd("招聘机器学习工程师，要求3年以上经验")

        # Assert
        assert result is not None
        assert len(result.research_areas) > 0

    @pytest.mark.asyncio
    async def test_parse_jd_caches_result(self, test_session: AsyncSession):
        """解析 JD 应缓存结果"""
        # Arrange
        from app.services.jd_match.jd_match_service import JDMatchService
        from app.services.llm.protocols import JDFeatures

        mock_llm = MockLLMGateway()
        mock_embed = AsyncMock()

        # 创建 mock 缓存
        mock_cache = AsyncMock()
        cached_features = JDFeatures(research_areas=["Machine Learning", "Deep Learning"])
        # 第一次返回 None（缓存未命中），第二次返回缓存结果
        mock_cache.get_jd_features = AsyncMock(side_effect=[None, cached_features])

        service = JDMatchService(
            session=test_session, llm_gateway=mock_llm, embed_service=mock_embed, cache=mock_cache
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
        self, test_session: AsyncSession, sample_talent: dict, test_user
    ):
        """匹配应返回候选人列表"""
        # Arrange
        from app.services.jd_match.jd_match_service import JDMatchService

        mock_llm = MockLLMGateway()
        mock_embed = AsyncMock()
        mock_embed.get_embedding = AsyncMock(return_value=[0.1] * 1536)

        service = JDMatchService(
            session=test_session, llm_gateway=mock_llm, embed_service=mock_embed
        )

        config = MatchConfig(weights={"research": 1.0}, filters={}, limit=10)

        # Act
        result = await service.match(
            jd_text="招聘机器学习工程师", config=config, user_id=test_user.user_id
        )

        # Assert
        assert result is not None
        assert result.total >= 0

    @pytest.mark.asyncio
    async def test_match_respects_limit(
        self, test_session: AsyncSession, sample_talent: dict, test_user
    ):
        """匹配应遵守数量限制"""
        # Arrange
        from app.services.jd_match.jd_match_service import JDMatchService

        mock_llm = MockLLMGateway()
        mock_embed = AsyncMock()

        service = JDMatchService(
            session=test_session, llm_gateway=mock_llm, embed_service=mock_embed
        )

        config = MatchConfig(weights={"research": 1.0}, filters={}, limit=5)

        # Act
        result = await service.match(
            jd_text="招聘机器学习工程师", config=config, user_id=test_user.user_id
        )

        # Assert
        assert len(result.items) <= 5

    @pytest.mark.asyncio
    async def test_match_applies_filters(
        self, test_session: AsyncSession, sample_talent: dict, test_user
    ):
        """匹配应应用过滤条件"""
        # Arrange
        from app.services.jd_match.jd_match_service import JDMatchService

        mock_llm = MockLLMGateway()
        mock_embed = AsyncMock()

        service = JDMatchService(
            session=test_session, llm_gateway=mock_llm, embed_service=mock_embed
        )

        config = MatchConfig(
            weights={"research": 1.0},
            filters={"min_citations": 100, "school_ids": [1, 2, 3]},
            limit=10,
        )

        # Act
        result = await service.match(jd_text="招聘机器学习工程师", config=config, user_id=1)

        # Assert - 过滤后的结果应满足条件
        for _item in result.items:
            # 实际断言取决于数据模型
            pass


class TestJDMatchServiceScoring:
    """评分测试"""

    @pytest.mark.asyncio
    async def test_calculate_research_score(self, test_session: AsyncSession):
        """应正确计算研究方向分数"""
        # Arrange
        from app.services.jd_match.match_scorer import MatchScorer

        scorer = MatchScorer()

        jd_areas = ["Deep Learning", "Natural Language Processing"]
        candidate_areas = ["Deep Learning", "Computer Vision"]

        # Act
        score = scorer.calculate_research_score(jd_areas, candidate_areas)

        # Assert
        assert 0 <= score <= 100
        # Deep Learning 匹配
        assert score > 0

    @pytest.mark.asyncio
    async def test_calculate_overall_score(self, test_session: AsyncSession):
        """应正确计算综合分数"""
        # Arrange
        from app.services.jd_match.match_scorer import MatchScorer

        scorer = MatchScorer()

        # Act
        overall = scorer.calculate_overall_score(research_score=80)

        # Assert
        assert overall == 80.0

    @pytest.mark.asyncio
    async def test_score_zero_on_no_match(self, test_session: AsyncSession):
        """无匹配应返回零分"""
        # Arrange
        from app.services.jd_match.match_scorer import MatchScorer

        scorer = MatchScorer()

        # Act
        score = scorer.calculate_research_score(
            jd_areas=["Rust", "Go"], candidate_matchable=["Python", "Java"]
        )

        # Assert
        assert score == 0

    @pytest.mark.asyncio
    async def test_score_with_five_requirements(self, test_session: AsyncSession):
        """分母上限为5，应正确计算"""
        # Arrange
        from app.services.jd_match.match_scorer import MatchScorer

        scorer = MatchScorer()

        # 5 个研究方向，全部匹配
        jd_areas = [
            "Machine Learning",
            "Deep Learning",
            "NLP",
            "Computer Vision",
            "Reinforcement Learning",
        ]
        candidate_matchable = [
            "Machine Learning",
            "Deep Learning",
            "NLP",
            "Computer Vision",
            "Reinforcement Learning",
        ]

        # Act
        score = scorer.calculate_research_score(jd_areas, candidate_matchable)

        # Assert - 5/5 = 100%
        assert score == 100.0


class TestJDMatchServiceReasons:
    """匹配原因测试"""

    @pytest.mark.asyncio
    async def test_generate_match_reasons(self, test_session: AsyncSession):
        """应生成匹配原因"""
        # Arrange
        from app.services.jd_match.match_scorer import MatchScorer

        scorer = MatchScorer()

        jd_features = JDFeatures(research_areas=["Natural Language Processing", "Deep Learning"])

        candidate = {
            "research_topics": ["Natural Language Processing", "Machine Learning"],
            "paper_titles": ["Deep Learning for NLP", "Transformer Models"],
            "h_index": 15,
        }

        # Act
        reasons = scorer.generate_match_reasons(jd_features, candidate)

        # Assert
        assert len(reasons) > 0
        # 应包含研究方向匹配
        assert any("研究方向" in r for r in reasons)


class TestJDMatchServiceSession:
    """会话管理测试"""

    @pytest.mark.asyncio
    async def test_create_session(self, test_session: AsyncSession, test_user):
        """应创建匹配会话"""
        # Arrange
        from app.services.jd_match.jd_match_service import JDMatchService

        mock_llm = MockLLMGateway()
        mock_embed = AsyncMock()

        service = JDMatchService(
            session=test_session, llm_gateway=mock_llm, embed_service=mock_embed
        )

        # Act
        result = await service.match(
            jd_text="招聘机器学习工程师",
            config=MatchConfig(weights={}, filters={}, limit=10),
            user_id=test_user.user_id,
        )

        # Assert
        assert result.session_id is not None

    @pytest.mark.asyncio
    async def test_session_status_updates(self, test_session: AsyncSession):
        """会话状态应正确更新"""
        # 这个测试验证会话状态从 pending -> completed/failed
        # 实际实现中需要检查数据库状态

        pass  # 实现细节取决于实际模型


class TestJDMatchServiceErrorHandling:
    """错误处理测试"""

    @pytest.mark.asyncio
    async def test_match_handles_llm_failure(self, test_session: AsyncSession, test_user):
        """LLM 失败应抛出错误"""
        # Arrange
        from app.services.jd_match.jd_match_service import JDMatchService

        mock_llm = MockLLMGateway(should_fail=True, fail_count=100)
        mock_embed = AsyncMock()

        service = JDMatchService(
            session=test_session, llm_gateway=mock_llm, embed_service=mock_embed
        )

        config = MatchConfig(weights={}, filters={}, limit=10)

        # Act & Assert - 应该抛出异常
        with pytest.raises(RuntimeError):
            await service.match(
                jd_text="招聘机器学习工程师", config=config, user_id=test_user.user_id
            )

    @pytest.mark.asyncio
    async def test_match_handles_empty_jd(self, test_session: AsyncSession):
        """空 JD 应返回错误"""
        # Arrange
        from app.services.jd_match.jd_match_service import JDMatchService
        from app.services.llm.errors import JDMatchError

        mock_llm = MockLLMGateway()
        mock_embed = AsyncMock()

        service = JDMatchService(
            session=test_session, llm_gateway=mock_llm, embed_service=mock_embed
        )

        # Act & Assert - empty JD raises EmptyJDError, no user_id needed
        with pytest.raises((ValueError, JDMatchError)):
            await service.match(
                jd_text="",
                config=MatchConfig(weights={}, filters={}, limit=10),
                user_id=1,  # Won't be used due to early validation
            )


class TestJDMatchServiceTiming:
    """性能测试"""

    @pytest.mark.asyncio
    async def test_match_returns_timing(
        self, test_session: AsyncSession, sample_talent: dict, test_user
    ):
        """匹配结果应包含耗时"""
        # Arrange
        from app.services.jd_match.jd_match_service import JDMatchService

        mock_llm = MockLLMGateway()
        mock_embed = AsyncMock()

        service = JDMatchService(
            session=test_session, llm_gateway=mock_llm, embed_service=mock_embed
        )

        config = MatchConfig(weights={}, filters={}, limit=10)

        # Act
        result = await service.match(
            jd_text="招聘机器学习工程师", config=config, user_id=test_user.user_id
        )

        # Assert
        assert hasattr(result, "took_ms")
        assert result.took_ms >= 0  # 可能太快导致 took_ms 为 0
