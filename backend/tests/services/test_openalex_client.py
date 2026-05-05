"""
Tests for OpenAlex client.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.domains.academic.services.openalex_client import (
    OpenAlexClient,
    OpenAlexRateLimitError,
)


class TestOpenAlexClient:
    """Tests for OpenAlexClient."""

    def test_client_initialization(self):
        """Test client initialization."""
        client = OpenAlexClient(
            email="test@example.com",
            rate_limit=10,
        )

        assert client.email == "test@example.com"
        assert client.rate_limit == 10
        assert client.base_url == "https://api.openalex.org"

    def test_rate_limit_calculation(self):
        """Test rate limit interval calculation."""
        client = OpenAlexClient(rate_limit=10)
        assert client._min_interval == 0.1

        client2 = OpenAlexClient(rate_limit=5)
        assert client2._min_interval == 0.2

    @pytest.mark.asyncio
    async def test_get_institutions_success(self):
        """Test successful institutions fetch."""
        client = OpenAlexClient(email="test@example.com")

        mock_response = {
            "results": [
                {"id": "https://openalex.org/I123", "display_name": "MIT"},
                {"id": "https://openalex.org/I456", "display_name": "Stanford"},
            ],
            "meta": {"count": 2, "next_cursor": None},
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance

            mock_http_response = MagicMock()
            mock_http_response.json.return_value = mock_response
            mock_http_response.raise_for_status = MagicMock()
            mock_instance.get.return_value = mock_http_response

            result = await client.get_institutions(country_code="US")

            assert result == mock_response
            assert len(result["results"]) == 2

    @pytest.mark.asyncio
    async def test_get_authors_success(self):
        """Test successful authors fetch."""
        client = OpenAlexClient(email="test@example.com")

        mock_response = {
            "results": [
                {"id": "https://openalex.org/A123", "display_name": "John Doe"},
            ],
            "meta": {"count": 1, "next_cursor": None},
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance

            mock_http_response = MagicMock()
            mock_http_response.json.return_value = mock_response
            mock_http_response.raise_for_status = MagicMock()
            mock_instance.get.return_value = mock_http_response

            result = await client.get_authors(institution_id="I123")

            assert result == mock_response

    @pytest.mark.asyncio
    async def test_rate_limit_error(self):
        """Test rate limit error handling."""
        client = OpenAlexClient()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance

            mock_http_response = MagicMock()
            mock_http_response.status_code = 429
            mock_http_response.text = "Rate limit exceeded"

            mock_instance.get.side_effect = httpx.HTTPStatusError(
                "Rate limit",
                request=MagicMock(),
                response=mock_http_response,
            )

            with pytest.raises(OpenAlexRateLimitError):
                await client.get_institutions()

    @pytest.mark.asyncio
    async def test_iterate_institutions(self):
        """Test institution iteration with pagination."""
        client = OpenAlexClient()

        # Mock two pages of results
        page1 = {
            "results": [{"id": "I1"}, {"id": "I2"}],
            "meta": {"next_cursor": "cursor123"},
        }
        page2 = {
            "results": [{"id": "I3"}],
            "meta": {"next_cursor": None},
        }

        with patch.object(client, "get_institutions", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [page1, page2]

            institutions = []
            async for inst in client.iterate_institutions(max_records=10):
                institutions.append(inst)

            assert len(institutions) == 3
            assert mock_get.call_count == 2

    @pytest.mark.asyncio
    async def test_max_records_limit(self):
        """Test max_records limit in iteration."""
        client = OpenAlexClient()

        mock_response = {
            "results": [{"id": f"I{i}"} for i in range(10)],
            "meta": {"next_cursor": "more"},
        }

        with patch.object(client, "get_institutions", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            institutions = []
            async for inst in client.iterate_institutions(max_records=5):
                institutions.append(inst)

            assert len(institutions) == 5
