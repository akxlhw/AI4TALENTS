"""
Tests for Search API endpoints.
搜索 API 测试
"""

import pytest
from httpx import AsyncClient


class TestSearchEndpoint:
    """Tests for /api/v1/search/talents endpoint."""

    @pytest.mark.asyncio
    async def test_search_with_keyword(self, client: AsyncClient, sample_talent: dict):
        """Test search with keyword returns results."""
        response = await client.get(
            "/api/v1/search/talents",
            params={"q": "Test"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_search_with_role_filter(self, client: AsyncClient, sample_talent: dict):
        """Test search with role type filter."""
        response = await client.get(
            "/api/v1/search/talents",
            params={
                "q": "Test",
                "role_type": "professor",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    @pytest.mark.asyncio
    async def test_search_pagination(self, client: AsyncClient, sample_talent: dict):
        """Test search pagination."""
        response = await client.get(
            "/api/v1/search/talents",
            params={"q": "Test", "page": 1, "page_size": 10},
        )

        assert response.status_code == 200
        data = response.json()
        assert "page" in data
        assert data["page"] == 1

    @pytest.mark.asyncio
    async def test_search_min_length_validation(self, client: AsyncClient):
        """Test search with keyword shorter than minimum length."""
        response = await client.get(
            "/api/v1/search/talents",
            params={"q": ""},
        )

        # Should return 422 for validation error
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_search_no_results(self, client: AsyncClient):
        """Test search with keyword that returns no results."""
        response = await client.get(
            "/api/v1/search/talents",
            params={"q": "NonExistentTalent12345"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["items"]) == 0

    @pytest.mark.asyncio
    async def test_search_page_size_limit(self, client: AsyncClient, sample_talent: dict):
        """Test search page size limit is enforced."""
        response = await client.get(
            "/api/v1/search/talents",
            params={"q": "Test", "page_size": 200},  # Over limit
        )

        # Should return 422 for validation error
        assert response.status_code == 422
