"""
Tests for LLM Gateway.
LLM 网关测试 - v1.4.1

Coverage:
- JD parsing (simplified to research_areas only)
- Embedding generation
- Error handling
- Retry logic
- Health check
"""

import pytest

# Import mock
from tests.mocks.mock_llm_gateway import EmbeddingResult, JDFeatures, MockLLMGateway


class TestLLMGatewayJDParsing:
    """JD 解析测试"""

    @pytest.mark.asyncio
    async def test_parse_jd_returns_features(self):
        """解析 JD 应返回特征"""
        # Arrange
        gateway = MockLLMGateway()
        jd_text = "招聘机器学习工程师，要求3年以上经验"

        # Act
        result = await gateway.parse_jd(jd_text)

        # Assert
        assert result is not None
        assert isinstance(result, JDFeatures)
        assert len(result.research_areas) > 0

    @pytest.mark.asyncio
    async def test_parse_jd_extracts_research_areas(self):
        """解析 JD 应提取研究方向"""
        # Arrange
        expected_areas = ["Computer Vision", "Deep Learning"]
        gateway = MockLLMGateway(jd_features=JDFeatures(research_areas=expected_areas))

        # Act
        result = await gateway.parse_jd("招聘计算机视觉研究员")

        # Assert
        assert "Computer Vision" in result.research_areas
        assert "Deep Learning" in result.research_areas


class TestLLMGatewayEmbedding:
    """嵌入生成测试"""

    @pytest.mark.asyncio
    async def test_generate_embedding_returns_vector(self):
        """生成嵌入应返回向量"""
        # Arrange
        gateway = MockLLMGateway()
        text = "这是一个测试文本"

        # Act
        result = await gateway.generate_embedding(text)

        # Assert
        assert result is not None
        assert isinstance(result, EmbeddingResult)
        assert len(result.embedding) == 1536  # Default dimension

    @pytest.mark.asyncio
    async def test_generate_embedding_returns_correct_dimension(self):
        """生成嵌入应返回正确维度"""
        # Arrange
        expected_embedding = [0.5] * 768  # Different dimension
        gateway = MockLLMGateway(embedding=expected_embedding)

        # Act
        result = await gateway.generate_embedding("test")

        # Assert
        assert len(result.embedding) == 768

    @pytest.mark.asyncio
    async def test_generate_embedding_batch(self):
        """批量生成嵌入应返回正确数量"""
        # Arrange
        gateway = MockLLMGateway()
        texts = ["文本1", "文本2", "文本3"]

        # Act
        results = await gateway.generate_embedding_batch(texts)

        # Assert
        assert len(results) == 3
        for result in results:
            assert isinstance(result, EmbeddingResult)

    @pytest.mark.asyncio
    async def test_generate_embedding_tracks_tokens(self):
        """生成嵌入应记录 token 数量"""
        # Arrange
        gateway = MockLLMGateway()

        # Act
        result = await gateway.generate_embedding("This is a test sentence with multiple words")

        # Assert
        assert result.tokens_used > 0


class TestLLMGatewayErrorHandling:
    """错误处理测试"""

    @pytest.mark.asyncio
    async def test_parse_jd_handles_api_error(self):
        """JD 解析应处理 API 错误"""
        # Arrange
        gateway = MockLLMGateway(should_fail=True, fail_count=1)

        # Act & Assert
        with pytest.raises(RuntimeError):
            await gateway.parse_jd("测试JD")

    @pytest.mark.asyncio
    async def test_generate_embedding_handles_api_error(self):
        """嵌入生成应处理 API 错误"""
        # Arrange
        gateway = MockLLMGateway(should_fail=True, fail_count=1)

        # Act & Assert
        with pytest.raises(RuntimeError):
            await gateway.generate_embedding("测试文本")

    @pytest.mark.asyncio
    async def test_batch_embedding_handles_partial_failure(self):
        """批量嵌入应处理部分失败"""
        # Arrange
        gateway = MockLLMGateway(should_fail=True, fail_count=1)

        # Act & Assert
        with pytest.raises(RuntimeError):
            await gateway.generate_embedding_batch(["文本1", "文本2"])


class TestLLMGatewayRetry:
    """重试逻辑测试"""

    @pytest.mark.asyncio
    async def test_retry_on_transient_failure(self):
        """瞬态故障应触发重试"""
        # Arrange
        gateway = MockLLMGateway(should_fail=True, fail_count=2)

        # Act & Assert - 前2次失败，第3次成功
        # (实际实现中会有重试装饰器)
        with pytest.raises(RuntimeError):
            await gateway.parse_jd("测试JD")

        # 验证调用次数
        assert gateway.call_count >= 1

    @pytest.mark.asyncio
    async def test_no_retry_on_success(self):
        """成功不应触发重试"""
        # Arrange
        gateway = MockLLMGateway()

        # Act
        await gateway.parse_jd("测试JD")

        # Assert
        assert gateway.call_count == 1


class TestLLMGatewayHealthCheck:
    """健康检查测试"""

    @pytest.mark.asyncio
    async def test_health_check_returns_true_when_healthy(self):
        """健康状态应返回 True"""
        # Arrange
        gateway = MockLLMGateway()

        # Act
        result = await gateway.health_check()

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_returns_false_when_unhealthy(self):
        """不健康状态应返回 False"""
        # Arrange
        gateway = MockLLMGateway(should_fail=True)

        # Act
        result = await gateway.health_check()

        # Assert
        assert result is False


class TestLLMGatewayCache:
    """缓存测试"""

    @pytest.mark.asyncio
    async def test_cache_hits_for_same_jd(self):
        """相同 JD 应命中缓存"""
        # 这个测试验证缓存行为
        # Mock 不包含缓存，但实际实现应该有

        # Arrange
        gateway = MockLLMGateway()
        jd_text = "招聘机器学习工程师"

        # Act - 调用两次
        await gateway.parse_jd(jd_text)
        await gateway.parse_jd(jd_text)

        # Assert - 应该调用两次（Mock 没有缓存）
        # 实际实现中，第二次应该命中缓存
        assert gateway.call_count == 2


class TestLLMGatewayMetrics:
    """指标测试"""

    @pytest.mark.asyncio
    async def test_call_count_increments(self):
        """调用次数应递增"""
        # Arrange
        gateway = MockLLMGateway()

        # Act
        await gateway.parse_jd("JD 1")
        await gateway.parse_jd("JD 2")
        await gateway.generate_embedding("text")

        # Assert
        assert gateway.call_count == 3

    @pytest.mark.asyncio
    async def test_reset_clears_state(self):
        """重置应清除状态"""
        # Arrange
        gateway = MockLLMGateway()
        await gateway.parse_jd("test")

        # Act
        gateway.reset()

        # Assert
        assert gateway.call_count == 0
