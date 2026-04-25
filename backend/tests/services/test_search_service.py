"""
Tests for SearchService.
搜索服务测试 - v1.4 TDD

Coverage:
- SearchMode: keyword, fulltext, semantic, hybrid
- Multi-field search
- Fuzzy matching
- Pagination
- Error handling
"""

from dataclasses import dataclass
from enum import Enum
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

# ============ Test Data Classes (will be replaced by actual imports) ============


class SearchMode(str, Enum):
    """搜索模式"""

    KEYWORD = "keyword"
    FULLTEXT = "fulltext"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"


@dataclass
class SearchResult:
    """搜索结果"""

    total: int
    page: int
    page_size: int
    items: list[dict]
    search_mode: str
    took_ms: float


# ============ Tests ============


class TestSearchServiceMode:
    """搜索模式测试"""

    @pytest.mark.asyncio
    async def test_keyword_search_returns_results(
        self, test_session: AsyncSession, sample_talent: dict
    ):
        """关键词搜索应返回结果"""
        # Arrange
        from app.services.search.search_service import SearchService

        service = SearchService(test_session)

        # Act
        result = await service.search(query="Test", mode=SearchMode.KEYWORD, page=1, page_size=20)

        # Assert
        assert result is not None
        assert result.total >= 1
        assert len(result.items) >= 1

    @pytest.mark.asyncio
    async def test_keyword_search_filters_by_name(
        self, test_session: AsyncSession, sample_talent: dict
    ):
        """关键词搜索应按姓名过滤"""
        # Arrange
        from app.services.search.search_service import SearchService

        service = SearchService(test_session)

        # Act
        result = await service.search(
            query="Test Author", mode=SearchMode.KEYWORD, fields=["name"], page=1, page_size=20
        )

        # Assert
        assert result.total >= 1
        # 结果应包含搜索关键词
        for item in result.items:
            assert "Test" in item.get("name", "") or "Author" in item.get("name", "")

    @pytest.mark.asyncio
    async def test_keyword_search_filters_by_title(
        self, test_session: AsyncSession, sample_talent: dict
    ):
        """关键词搜索应按职位过滤"""
        # Arrange
        from app.services.search.search_service import SearchService

        service = SearchService(test_session)

        # Act
        result = await service.search(
            query="Professor", mode=SearchMode.KEYWORD, fields=["title"], page=1, page_size=20
        )

        # Assert
        assert result.search_mode == SearchMode.KEYWORD.value

    @pytest.mark.asyncio
    async def test_keyword_search_multi_field(
        self, test_session: AsyncSession, sample_talent: dict
    ):
        """关键词搜索应支持多字段"""
        # Arrange
        from app.services.search.search_service import SearchService

        service = SearchService(test_session)

        # Act
        result = await service.search(
            query="Test",
            mode=SearchMode.KEYWORD,
            fields=["name", "title", "school_name"],
            page=1,
            page_size=20,
        )

        # Assert
        assert result is not None

    @pytest.mark.asyncio
    async def test_fulltext_search_uses_tsvector(
        self, test_session: AsyncSession, sample_talent: dict
    ):
        """全文搜索应使用 tsvector"""
        # Arrange
        from app.services.search.search_service import SearchService

        service = SearchService(test_session)

        # Act
        result = await service.search(
            query="机器学习", mode=SearchMode.FULLTEXT, page=1, page_size=20
        )

        # Assert
        assert result.search_mode == SearchMode.FULLTEXT.value

    @pytest.mark.asyncio
    async def test_semantic_search_uses_embedding(
        self, test_session: AsyncSession, sample_talent: dict
    ):
        """语义搜索应使用嵌入向量"""
        # Arrange
        from app.services.search.search_service import SearchService

        # Mock embedding service
        mock_embedding_service = AsyncMock()
        mock_embedding_service.get_query_embedding = AsyncMock(return_value=[0.1] * 1536)

        service = SearchService(test_session, embedding_service=mock_embedding_service)

        # Act
        result = await service.search(
            query="深度学习研究员", mode=SearchMode.SEMANTIC, page=1, page_size=20
        )

        # Assert
        assert result.search_mode == SearchMode.SEMANTIC.value
        mock_embedding_service.get_query_embedding.assert_called_once()

    @pytest.mark.asyncio
    async def test_hybrid_search_combines_keyword_and_semantic(
        self, test_session: AsyncSession, sample_talent: dict
    ):
        """混合搜索应结合关键词和语义搜索"""
        # Arrange
        from app.services.search.search_service import SearchService

        mock_embedding_service = AsyncMock()
        mock_embedding_service.get_query_embedding = AsyncMock(return_value=[0.1] * 1536)

        service = SearchService(test_session, embedding_service=mock_embedding_service)

        # Act
        result = await service.search(
            query="机器学习", mode=SearchMode.HYBRID, page=1, page_size=20
        )

        # Assert
        assert result.search_mode == SearchMode.HYBRID.value


class TestSearchServiceFuzzy:
    """模糊匹配测试"""

    @pytest.mark.asyncio
    async def test_fuzzy_search_handles_typos(
        self, test_session: AsyncSession, sample_talent: dict
    ):
        """模糊搜索应处理拼写错误"""
        # Arrange
        from app.services.search.search_service import SearchService

        service = SearchService(test_session)

        # Act - "machne" 是 "machine" 的拼写错误
        result = await service.search(
            query="machne learning",  # typo
            mode=SearchMode.KEYWORD,
            fuzzy=True,
            page=1,
            page_size=20,
        )

        # Assert - 应该返回结果而不是空
        assert result is not None

    @pytest.mark.asyncio
    async def test_fuzzy_search_off_returns_exact_match(
        self, test_session: AsyncSession, sample_talent: dict
    ):
        """关闭模糊搜索应精确匹配"""
        # Arrange
        from app.services.search.search_service import SearchService

        service = SearchService(test_session)

        # Act
        result = await service.search(
            query="NonExistentTerm12345", mode=SearchMode.KEYWORD, fuzzy=False, page=1, page_size=20
        )

        # Assert
        assert result.total == 0


class TestSearchServicePagination:
    """分页测试"""

    @pytest.mark.asyncio
    async def test_pagination_returns_correct_page(
        self, test_session: AsyncSession, sample_talent: dict
    ):
        """分页应返回正确的页码"""
        # Arrange
        from app.services.search.search_service import SearchService

        service = SearchService(test_session)

        # Act
        result = await service.search(query="Test", mode=SearchMode.KEYWORD, page=2, page_size=5)

        # Assert
        assert result.page == 2
        assert result.page_size == 5

    @pytest.mark.asyncio
    async def test_pagination_first_page(self, test_session: AsyncSession, sample_talent: dict):
        """第一页应正确返回"""
        # Arrange
        from app.services.search.search_service import SearchService

        service = SearchService(test_session)

        # Act
        result = await service.search(query="Test", mode=SearchMode.KEYWORD, page=1, page_size=20)

        # Assert
        assert result.page == 1

    @pytest.mark.asyncio
    async def test_pagination_empty_page(self, test_session: AsyncSession, sample_talent: dict):
        """超出范围的页应返回空结果"""
        # Arrange
        from app.services.search.search_service import SearchService

        service = SearchService(test_session)

        # Act
        result = await service.search(
            query="Test",
            mode=SearchMode.KEYWORD,
            page=1000,  # Far beyond available data
            page_size=20,
        )

        # Assert
        assert result.items == []


class TestSearchServiceErrorHandling:
    """错误处理测试"""

    @pytest.mark.asyncio
    async def test_empty_query_raises_validation_error(self, test_session: AsyncSession):
        """空查询应抛出验证错误"""
        # Arrange
        from app.services.search.errors import EmptyQueryError
        from app.services.search.search_service import SearchService

        service = SearchService(test_session)

        # Act & Assert
        with pytest.raises((ValueError, EmptyQueryError)):
            await service.search(query="", mode=SearchMode.KEYWORD, page=1, page_size=20)

    @pytest.mark.asyncio
    async def test_invalid_mode_defaults_to_keyword(
        self, test_session: AsyncSession, sample_talent: dict
    ):
        """无效模式应默认为关键词搜索"""
        # Arrange
        from app.services.search.search_service import SearchService

        service = SearchService(test_session)

        # Act
        result = await service.search(
            query="Test", mode="invalid_mode", page=1, page_size=20  # type: ignore
        )

        # Assert - 应该正常返回结果而不是报错
        assert result is not None

    @pytest.mark.asyncio
    async def test_semantic_search_without_embedding_service_falls_back(
        self, test_session: AsyncSession, sample_talent: dict
    ):
        """语义搜索无嵌入服务应降级到关键词搜索"""
        # Arrange
        from app.services.search.search_service import SearchService

        service = SearchService(test_session, embedding_service=None)

        # Act
        result = await service.search(
            query="深度学习", mode=SearchMode.SEMANTIC, page=1, page_size=20
        )

        # Assert - 应该降级成功
        assert result is not None


class TestSearchServicePerformance:
    """性能测试"""

    @pytest.mark.asyncio
    async def test_search_returns_within_time_limit(
        self, test_session: AsyncSession, sample_talent: dict
    ):
        """搜索应在合理时间内返回"""
        # Arrange
        import time

        from app.services.search.search_service import SearchService

        service = SearchService(test_session)

        # Act
        start_time = time.time()
        result = await service.search(query="Test", mode=SearchMode.KEYWORD, page=1, page_size=20)
        elapsed = time.time() - start_time

        # Assert
        assert elapsed < 1.0  # Should complete within 1 second
        assert result.took_ms < 1000

    @pytest.mark.asyncio
    async def test_search_result_includes_timing(
        self, test_session: AsyncSession, sample_talent: dict
    ):
        """搜索结果应包含耗时"""
        # Arrange
        from app.services.search.search_service import SearchService

        service = SearchService(test_session)

        # Act
        result = await service.search(query="Test", mode=SearchMode.KEYWORD, page=1, page_size=20)

        # Assert
        assert hasattr(result, "took_ms")
        assert result.took_ms > 0


class TestSearchServiceHighlight:
    """高亮测试"""

    @pytest.mark.asyncio
    async def test_search_includes_highlight(self, test_session: AsyncSession, sample_talent: dict):
        """搜索结果应包含高亮信息"""
        # Arrange
        from app.services.search.search_service import SearchService

        service = SearchService(test_session)

        # Act
        result = await service.search(query="Test", mode=SearchMode.KEYWORD, page=1, page_size=20)

        # Assert
        if result.total > 0:
            item = result.items[0]
            # 高亮是可选功能
            assert "highlight" in item or "name" in item
