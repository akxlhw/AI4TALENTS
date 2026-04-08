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

        # Check service info exists (exact name may vary by environment)
        assert "name" in data["service"]
        assert "version" in data["service"]

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

        assert "name" in data
        assert "version" in data
        assert data["docs"] == "/docs"


class TestHealthCheckDetails:
    """Tests for detailed health check responses."""

    @pytest.mark.asyncio
    async def test_health_check_database_status(self, client: AsyncClient):
        """Test health check includes database connection status."""
        response = await client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()

        assert "database" in data
        assert "status" in data["database"]
        # Database should be connected in test environment
        assert data["database"]["status"] == "connected"

    @pytest.mark.asyncio
    async def test_health_check_cache_status(self, client: AsyncClient):
        """Test health check includes cache status."""
        response = await client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()

        assert "cache" in data
        assert "enabled" in data["cache"]
        # Cache is disabled in test environment by default
        assert data["cache"]["enabled"] is False

    @pytest.mark.asyncio
    async def test_health_check_pool_status(self, client: AsyncClient):
        """Test health check includes database pool status when available."""
        response = await client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()

        # Pool status fields should exist
        assert "pool_size" in data["database"]
        assert "pool_overflow" in data["database"]

    @pytest.mark.asyncio
    async def test_readiness_check_database_required(self, client: AsyncClient):
        """Test readiness check requires database."""
        response = await client.get("/api/v1/health/ready")

        assert response.status_code == 200
        data = response.json()

        assert "checks" in data
        assert data["checks"]["database"] is True

    @pytest.mark.asyncio
    async def test_readiness_check_cache_optional(self, client: AsyncClient):
        """Test readiness check treats cache as optional."""
        response = await client.get("/api/v1/health/ready")

        assert response.status_code == 200
        data = response.json()

        assert "checks" in data
        # Cache check exists but service can be ready without it
        assert "cache" in data["checks"]

    @pytest.mark.asyncio
    async def test_liveness_check_minimal(self, client: AsyncClient):
        """Test liveness check returns minimal response."""
        response = await client.get("/api/v1/health/live")

        assert response.status_code == 200
        data = response.json()

        # Liveness should be minimal - just confirm service is alive
        assert data["status"] == "alive"
        assert len(data) == 1  # Only status field

    @pytest.mark.asyncio
    async def test_health_check_timestamp_format(self, client: AsyncClient):
        """Test health check timestamp is ISO format."""
        import re
        from datetime import datetime

        response = await client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()

        assert "timestamp" in data
        # Verify ISO format
        timestamp = data["timestamp"]
        # Should be parseable as ISO format
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

    @pytest.mark.asyncio
    async def test_health_check_service_info(self, client: AsyncClient):
        """Test health check includes service information."""
        response = await client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()

        assert "service" in data
        service = data["service"]

        assert "name" in service
        assert "version" in service
        assert "environment" in service


class TestMetricsEndpoint:
    """Tests for metrics endpoints."""

    @pytest.mark.asyncio
    async def test_metrics_prometheus_format(self, client: AsyncClient):
        """Test metrics endpoint returns Prometheus format."""
        response = await client.get("/api/v1/metrics")

        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]

    @pytest.mark.asyncio
    async def test_metrics_json_format(self, client: AsyncClient):
        """Test metrics JSON endpoint returns JSON."""
        response = await client.get("/api/v1/metrics/json")

        assert response.status_code == 200
        data = response.json()

        assert "cache" in data
        assert "database" in data
        assert "http_requests" in data

    @pytest.mark.asyncio
    async def test_metrics_json_cache_status(self, client: AsyncClient):
        """Test metrics JSON includes cache status."""
        response = await client.get("/api/v1/metrics/json")

        assert response.status_code == 200
        data = response.json()

        assert "available" in data["cache"]
        assert "hits" in data["cache"]
        assert "misses" in data["cache"]

    @pytest.mark.asyncio
    async def test_metrics_json_database_status(self, client: AsyncClient):
        """Test metrics JSON includes database status."""
        response = await client.get("/api/v1/metrics/json")

        assert response.status_code == 200
        data = response.json()

        assert "connections_active" in data["database"]
