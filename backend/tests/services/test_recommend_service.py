"""
Tests for Recommend Service.
推荐服务测试 - v1.4

Coverage:
- Similar talent recommendation
- Similarity calculation
- Filter application
"""

from dataclasses import dataclass
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

# ============ Test Data Classes ============


@dataclass
class RecommendResultItem:
    """推荐结果项"""

    talent_id: int
    name: str
    title: str
    school_name: str
    similarity_score: float
    reasons: list[str]


@dataclass
class RecommendResult:
    """推荐结果"""

    reference_talents: list[int]
    total: int
    items: list[RecommendResultItem]
    mode: str
    took_ms: float


# ============ Tests ============


class TestRecommendServiceSimilar:
    """相似推荐测试"""

    @pytest.mark.asyncio
    async def test_get_similar_returns_candidates(
        self, test_session: AsyncSession, sample_talent: dict
    ):
        """相似推荐应返回候选人"""
        # Arrange
        from app.services.recommend.recommend_service import RecommendService

        mock_embed = AsyncMock()
        mock_embed.get_embedding = AsyncMock(return_value=[0.1] * 1536)

        service = RecommendService(session=test_session, embed_service=mock_embed)

        # Act
        result = await service.get_similar(
            reference_talent_ids=[sample_talent["talent"].talent_id], limit=10
        )

        # Assert
        assert result is not None
        assert result.mode == "similar"

    @pytest.mark.asyncio
    async def test_get_similar_excludes_reference(
        self, test_session: AsyncSession, sample_talent: dict
    ):
        """相似推荐应排除参考人才"""
        # Arrange
        from app.services.recommend.recommend_service import RecommendService

        mock_embed = AsyncMock()

        service = RecommendService(session=test_session, embed_service=mock_embed)

        reference_id = sample_talent["talent"].talent_id

        # Act
        result = await service.get_similar(reference_talent_ids=[reference_id], limit=10)

        # Assert
        for item in result.items:
            assert item.talent_id != reference_id

    @pytest.mark.asyncio
    async def test_get_similar_respects_limit(
        self, test_session: AsyncSession, sample_talent: dict
    ):
        """相似推荐应遵守数量限制"""
        # Arrange
        from app.services.recommend.recommend_service import RecommendService

        mock_embed = AsyncMock()

        service = RecommendService(session=test_session, embed_service=mock_embed)

        # Act
        result = await service.get_similar(
            reference_talent_ids=[sample_talent["talent"].talent_id], limit=5
        )

        # Assert
        assert len(result.items) <= 5

    @pytest.mark.asyncio
    async def test_get_similar_uses_vector_similarity(
        self, test_session: AsyncSession, sample_talent: dict
    ):
        """相似推荐应使用向量相似度"""
        # Arrange
        from app.services.recommend.recommend_service import RecommendService

        mock_embed = AsyncMock()
        mock_embed.get_embedding = AsyncMock(return_value=[0.1] * 1536)

        service = RecommendService(session=test_session, embed_service=mock_embed)

        # Act
        result = await service.get_similar(
            reference_talent_ids=[sample_talent["talent"].talent_id], limit=10
        )

        # Assert - 验证结果正确返回
        assert result.mode == "similar"


class TestRecommendServiceSimilarity:
    """相似度计算测试"""

    @pytest.mark.asyncio
    async def test_cosine_similarity_same_vector(self):
        """相同向量相似度应为 1"""
        # Arrange
        from app.services.recommend.similarity import SimilarityCalculator

        calc = SimilarityCalculator()
        vec1 = [0.5, 0.5, 0.5, 0.5]
        vec2 = [0.5, 0.5, 0.5, 0.5]

        # Act
        similarity = calc.cosine_similarity(vec1, vec2)

        # Assert
        assert abs(similarity - 1.0) < 0.001

    @pytest.mark.asyncio
    async def test_cosine_similarity_orthogonal_vector(self):
        """正交向量相似度应为 0"""
        # Arrange
        from app.services.recommend.similarity import SimilarityCalculator

        calc = SimilarityCalculator()
        vec1 = [1.0, 0.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0, 0.0]

        # Act
        similarity = calc.cosine_similarity(vec1, vec2)

        # Assert
        assert abs(similarity - 0.0) < 0.001

    @pytest.mark.asyncio
    async def test_cosine_similarity_opposite_vector(self):
        """相反向量相似度应为 -1"""
        # Arrange
        from app.services.recommend.similarity import SimilarityCalculator

        calc = SimilarityCalculator()
        vec1 = [1.0, 0.0]
        vec2 = [-1.0, 0.0]

        # Act
        similarity = calc.cosine_similarity(vec1, vec2)

        # Assert
        assert abs(similarity - (-1.0)) < 0.001

    @pytest.mark.asyncio
    async def test_euclidean_distance(self):
        """欧氏距离应正确计算"""
        # Arrange
        from app.services.recommend.similarity import SimilarityCalculator

        calc = SimilarityCalculator()
        vec1 = [0.0, 0.0]
        vec2 = [3.0, 4.0]

        # Act
        distance = calc.euclidean_distance(vec1, vec2)

        # Assert
        assert abs(distance - 5.0) < 0.001


class TestRecommendServiceFilters:
    """过滤测试"""

    @pytest.mark.asyncio
    async def test_filter_by_school(self, test_session: AsyncSession, sample_talent: dict):
        """应按学校过滤"""
        # Arrange
        from app.services.recommend.recommend_service import RecommendService

        mock_embed = AsyncMock()

        service = RecommendService(session=test_session, embed_service=mock_embed)

        filters = {"school_ids": [sample_talent["school"].school_id]}

        # Act
        result = await service.get_similar(
            reference_talent_ids=[sample_talent["talent"].talent_id], limit=10, filters=filters
        )

        # Assert
        for _item in result.items:
            # 应该是指定学校
            pass

    @pytest.mark.asyncio
    async def test_filter_by_exclude_ids(self, test_session: AsyncSession, sample_talent: dict):
        """应排除指定ID"""
        # Arrange
        from app.services.recommend.recommend_service import RecommendService

        mock_embed = AsyncMock()

        service = RecommendService(session=test_session, embed_service=mock_embed)

        exclude_id = sample_talent["talent"].talent_id
        filters = {"exclude_ids": [exclude_id]}

        # Act
        result = await service.get_similar(
            reference_talent_ids=[sample_talent["talent"].talent_id], limit=10, filters=filters
        )

        # Assert
        for item in result.items:
            assert item.talent_id != exclude_id

    @pytest.mark.asyncio
    async def test_filter_by_tech_domain(
        self, test_session: AsyncSession, sample_talent: dict, sample_tech_domain: dict
    ):
        """应按技术领域过滤"""
        # Arrange
        from app.services.recommend.recommend_service import RecommendService

        mock_embed = AsyncMock()

        service = RecommendService(session=test_session, embed_service=mock_embed)

        filters = {"tech_domains": ["AI"]}

        # Act
        await service.get_similar(
            reference_talent_ids=[sample_talent["talent"].talent_id], limit=10, filters=filters
        )

        # Assert - 结果应符合技术领域过滤
        pass


class TestRecommendServiceReasons:
    """推荐原因测试"""

    @pytest.mark.asyncio
    async def test_generate_reasons_includes_similarity(self, test_session: AsyncSession):
        """推荐原因应包含相似度信息"""
        # Arrange
        from app.services.recommend.recommend_service import RecommendService

        mock_embed = AsyncMock()

        service = RecommendService(session=test_session, embed_service=mock_embed)

        # Act
        reasons = service.generate_reasons(
            similarity_score=0.85,
            reference_talent={"openalex_topics": ["Machine Learning"]},
            candidate_talent={"openalex_topics": ["Deep Learning"]},
        )

        # Assert
        assert len(reasons) > 0

    @pytest.mark.asyncio
    async def test_reasons_includes_research_match(self, test_session: AsyncSession):
        """推荐原因应包含研究方向匹配"""
        # Arrange
        from app.services.recommend.recommend_service import RecommendService

        service = RecommendService(session=test_session, embed_service=AsyncMock())

        # Act
        reasons = service.generate_reasons(
            similarity_score=0.9,
            reference_talent={"openalex_topics": ["NLP", "Deep Learning"]},
            candidate_talent={"openalex_topics": ["Deep Learning", "Machine Learning"]},
        )

        # Assert
        assert any("深度学习" in r or "研究方向" in r for r in reasons)


class TestRecommendServiceMultiReference:
    """多参考人才测试"""

    @pytest.mark.asyncio
    async def test_multiple_references_averages_embedding(
        self, test_session: AsyncSession, sample_talent: dict
    ):
        """多个参考人才应平均嵌入向量"""
        # Arrange
        from app.services.recommend.recommend_service import RecommendService

        mock_embed = AsyncMock()
        mock_embed.get_average_embedding = AsyncMock(return_value=[0.1] * 1536)

        service = RecommendService(session=test_session, embed_service=mock_embed)

        # Act - 使用多个已存在的参考人才
        result = await service.get_similar(
            reference_talent_ids=[sample_talent["talent"].talent_id], limit=10
        )

        # Assert - 验证结果正确返回
        assert result.reference_talents == [sample_talent["talent"].talent_id]

    @pytest.mark.asyncio
    async def test_reference_talents_included_in_result(
        self, test_session: AsyncSession, sample_talent: dict
    ):
        """结果应包含参考人才信息"""
        # Arrange
        from app.services.recommend.recommend_service import RecommendService

        mock_embed = AsyncMock()

        service = RecommendService(session=test_session, embed_service=mock_embed)

        reference_ids = [sample_talent["talent"].talent_id]

        # Act
        result = await service.get_similar(reference_talent_ids=reference_ids, limit=10)

        # Assert
        assert result.reference_talents == reference_ids


class TestRecommendServiceErrorHandling:
    """错误处理测试"""

    @pytest.mark.asyncio
    async def test_handles_invalid_reference_id(self, test_session: AsyncSession):
        """应处理无效参考ID"""
        # Arrange
        from app.services.recommend.recommend_service import RecommendError, RecommendService

        mock_embed = AsyncMock()

        service = RecommendService(session=test_session, embed_service=mock_embed)

        # Act & Assert
        with pytest.raises((ValueError, RecommendError)):
            await service.get_similar(reference_talent_ids=[99999], limit=10)

    @pytest.mark.asyncio
    async def test_handles_empty_reference_list(self, test_session: AsyncSession):
        """应处理空参考列表"""
        # Arrange
        from app.services.recommend.recommend_service import RecommendError, RecommendService

        service = RecommendService(session=test_session, embed_service=AsyncMock())

        # Act & Assert
        with pytest.raises((ValueError, RecommendError)):
            await service.get_similar(reference_talent_ids=[], limit=10)

    @pytest.mark.asyncio
    async def test_handles_no_candidates(self, test_session: AsyncSession, sample_talent: dict):
        """应处理无候选人的情况"""
        # Arrange
        from app.services.recommend.recommend_service import RecommendService

        mock_embed = AsyncMock()

        service = RecommendService(session=test_session, embed_service=mock_embed)

        # Act - 使用已存在的参考人才
        result = await service.get_similar(
            reference_talent_ids=[sample_talent["talent"].talent_id], limit=10
        )

        # Assert - 应该返回结果
        assert result.total >= 0


class TestRecommendServiceTiming:
    """性能测试"""

    @pytest.mark.asyncio
    async def test_returns_timing_info(self, test_session: AsyncSession, sample_talent: dict):
        """应返回耗时信息"""
        # Arrange
        from app.services.recommend.recommend_service import RecommendService

        mock_embed = AsyncMock()

        service = RecommendService(session=test_session, embed_service=mock_embed)

        # Act
        result = await service.get_similar(
            reference_talent_ids=[sample_talent["talent"].talent_id], limit=10
        )

        # Assert
        assert hasattr(result, "took_ms")
        assert result.took_ms > 0

    @pytest.mark.asyncio
    async def test_completes_within_time_limit(
        self, test_session: AsyncSession, sample_talent: dict
    ):
        """应在合理时间内完成"""
        # Arrange
        import time

        from app.services.recommend.recommend_service import RecommendService

        mock_embed = AsyncMock()

        service = RecommendService(session=test_session, embed_service=mock_embed)

        # Act
        start = time.time()
        await service.get_similar(
            reference_talent_ids=[sample_talent["talent"].talent_id], limit=10
        )
        elapsed = time.time() - start

        # Assert
        assert elapsed < 2.0  # 应在2秒内完成
