"""
Tests for health check endpoints.
"""
import pytest
from httpx import AsyncClient


class TestHealthEndpoints:
    """Tests for health check API endpoints."""

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test health check endpoint returns healthy status."""
        response = await client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert "timestamp" in data
        assert "service" in data
        assert "database" in data

        assert data["service"]["name"] == "智能人才库 API"
        assert data["service"]["version"] == "1.0.0"

    @pytest.mark.asyncio
    async def test_readiness_check(self, client: AsyncClient):
        """Test readiness check endpoint."""
        response = await client.get("/api/v1/health/ready")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "ready"

    @pytest.mark.asyncio
    async def test_liveness_check(self, client: AsyncClient):
        """Test liveness check endpoint."""
        response = await client.get("/api/v1/health/live")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "alive"

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client: AsyncClient):
        """Test root endpoint."""
        response = await client.get("/")

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "智能人才库 API"
        assert data["version"] == "1.0.0"
        assert data["docs"] == "/docs"
