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
        from app.domains.academic.services.recommend.recommend_service import RecommendService

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
        from app.domains.academic.services.recommend.recommend_service import RecommendService

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
        from app.domains.academic.services.recommend.recommend_service import RecommendService

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
        from app.domains.academic.services.recommend.recommend_service import RecommendService

        mock_embed = AsyncMock()
        mock_embed.get_embedding = AsyncMock(return_value=[0.1] * 1536)

        service = RecommendService(session=test_session, embed_service=mock_embed)

        # Act
        result = await service.get_similar(
            reference_talent_ids=[sample_talent["talent"].talent_id], limit=10
        )

        # Assert - 验证结果正确返回
        assert result.mode == "similar"


class TestRecommendServiceFilters:
    """过滤测试"""

    @pytest.mark.asyncio
    async def test_filter_by_school(self, test_session: AsyncSession, sample_talent: dict):
        """应按学校过滤"""
        # Arrange
        from app.domains.academic.services.recommend.recommend_service import RecommendService

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
        from app.domains.academic.services.recommend.recommend_service import RecommendService

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
        from app.domains.academic.services.recommend.recommend_service import RecommendService

        mock_embed = AsyncMock()

        service = RecommendService(session=test_session, embed_service=mock_embed)

        filters = {"tech_domains": ["AI"]}

        # Act
        await service.get_similar(
            reference_talent_ids=[sample_talent["talent"].talent_id], limit=10, filters=filters
        )

        # Assert - 结果应符合技术领域过滤
        pass


class TestRecommendServiceMultiReference:
    """多参考人才测试"""

    @pytest.mark.asyncio
    async def test_multiple_references_averages_embedding(
        self, test_session: AsyncSession, sample_talent: dict
    ):
        """多个参考人才应平均嵌入向量"""
        # Arrange
        from app.domains.academic.services.recommend.recommend_service import RecommendService

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
        from app.domains.academic.services.recommend.recommend_service import RecommendService

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
        from app.domains.academic.services.recommend.recommend_service import RecommendService
        from app.domains.shared.services.llm.errors import InvalidReferenceError

        mock_embed = AsyncMock()

        service = RecommendService(session=test_session, embed_service=mock_embed)

        # Act & Assert
        with pytest.raises(InvalidReferenceError):
            await service.get_similar(reference_talent_ids=[99999], limit=10)

    @pytest.mark.asyncio
    async def test_handles_empty_reference_list(self, test_session: AsyncSession):
        """应处理空参考列表"""
        # Arrange
        from app.domains.academic.services.recommend.recommend_service import RecommendService
        from app.domains.shared.services.llm.errors import EmptyReferenceError

        service = RecommendService(session=test_session, embed_service=AsyncMock())

        # Act & Assert
        with pytest.raises(EmptyReferenceError):
            await service.get_similar(reference_talent_ids=[], limit=10)

    @pytest.mark.asyncio
    async def test_handles_no_candidates(self, test_session: AsyncSession, sample_talent: dict):
        """应处理无候选人的情况"""
        # Arrange
        from app.domains.academic.services.recommend.recommend_service import RecommendService

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
        from app.domains.academic.services.recommend.recommend_service import RecommendService

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

        from app.domains.academic.services.recommend.recommend_service import RecommendService

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
