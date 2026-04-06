"""
Tests for metrics collection and /metrics endpoint.
"""
import os

os.environ["REDIS_ENABLED"] = "false"

import pytest
from httpx import AsyncClient

from app.core.metrics import (
    CounterMetric,
    GaugeMetric,
    HistogramMetric,
    MetricsRegistry,
    metrics,
    record_request,
)
from app.main import app


class TestMetricTypes:
    """Tests for metric type classes."""

    def test_counter_increment(self):
        """Test counter increment."""
        counter = CounterMetric("test_counter", "Test counter")
        assert counter.value == 0.0

        counter.inc()
        assert counter.value == 1.0

        counter.inc(5)
        assert counter.value == 6.0

    def test_counter_reset(self):
        """Test counter reset."""
        counter = CounterMetric("test_counter", "Test counter")
        counter.inc(10)
        assert counter.value == 10.0

        counter.reset()
        assert counter.value == 0.0

    def test_gauge_set(self):
        """Test gauge set."""
        gauge = GaugeMetric("test_gauge", "Test gauge")
        assert gauge.value == 0.0

        gauge.set(42)
        assert gauge.value == 42.0

    def test_gauge_increment_decrement(self):
        """Test gauge increment and decrement."""
        gauge = GaugeMetric("test_gauge", "Test gauge")
        gauge.set(10)

        gauge.inc(5)
        assert gauge.value == 15.0

        gauge.dec(3)
        assert gauge.value == 12.0

    def test_histogram_observe(self):
        """Test histogram observe."""
        histogram = HistogramMetric(
            "test_histogram",
            "Test histogram",
            buckets=[0.1, 0.5, 1.0, 5.0],
        )

        histogram.observe(0.05)
        histogram.observe(0.3)
        histogram.observe(0.8)
        histogram.observe(10.0)

        assert histogram.count == 4
        assert histogram.sum == 11.15

        # Check bucket counts
        assert histogram.counts[0.1] == 1  # 0.05 <= 0.1
        assert histogram.counts[0.5] == 2   # 0.05, 0.3 <= 0.5
        assert histogram.counts[1.0] == 3   # 0.05, 0.3, 0.8 <= 1.0
        assert histogram.counts[5.0] == 3   # 0.05, 0.3, 0.8 <= 5.0
        assert histogram.counts["+Inf"] == 4  # All values


class TestMetricsRegistry:
    """Tests for metrics registry."""

    def test_registry_counter(self):
        """Test registry counter creation."""
        registry = MetricsRegistry()
        counter = registry.counter("test_counter", "Test description")

        assert counter.name == "test_counter"
        assert counter.description == "Test description"

        # Get same counter again
        counter2 = registry.counter("test_counter")
        assert counter2 is counter

    def test_registry_counter_with_labels(self):
        """Test registry counter with labels."""
        registry = MetricsRegistry()

        counter1 = registry.counter("requests", labels={"method": "GET"})
        counter2 = registry.counter("requests", labels={"method": "POST"})

        # Different labels = different counters
        assert counter1 is not counter2

        counter1.inc(10)
        counter2.inc(5)

        assert counter1.value == 10
        assert counter2.value == 5

    def test_registry_gauge(self):
        """Test registry gauge creation."""
        registry = MetricsRegistry()
        gauge = registry.gauge("test_gauge", "Test gauge")

        gauge.set(100)
        assert gauge.value == 100

    def test_registry_histogram(self):
        """Test registry histogram creation."""
        registry = MetricsRegistry()
        histogram = registry.histogram("test_histogram", "Test histogram")

        histogram.observe(0.5)
        histogram.observe(1.5)

        assert histogram.count == 2

    def test_export_prometheus_format(self):
        """Test Prometheus format export."""
        registry = MetricsRegistry()

        counter = registry.counter("http_requests_total", "Total HTTP requests")
        counter.inc(100)

        gauge = registry.gauge("active_connections", "Active connections")
        gauge.set(5)

        histogram = registry.histogram(
            "request_duration_seconds",
            "Request duration",
            buckets=[0.1, 1.0],
        )
        histogram.observe(0.5)
        histogram.observe(1.5)

        output = registry.export_prometheus()

        # Check output format
        assert "# HELP http_requests_total Total HTTP requests" in output
        assert "# TYPE http_requests_total counter" in output
        assert "http_requests_total 100" in output

        assert "# HELP active_connections Active connections" in output
        assert "active_connections 5" in output

        assert "# TYPE request_duration_seconds histogram" in output
        assert "request_duration_seconds_sum" in output
        assert "request_duration_seconds_count 2" in output

    def test_reset_all(self):
        """Test reset all metrics."""
        registry = MetricsRegistry()

        counter = registry.counter("test_counter")
        counter.inc(100)

        gauge = registry.gauge("test_gauge")
        gauge.set(50)

        registry.reset_all()

        assert counter.value == 0
        assert gauge.value == 0


class TestMetricsMiddleware:
    """Tests for metrics middleware integration."""

    @pytest.mark.asyncio
    async def test_metrics_endpoint(self):
        """Test /metrics endpoint returns Prometheus format."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/metrics")

            assert response.status_code == 200
            assert "text/plain" in response.headers["content-type"]

            # Should contain default metrics
            content = response.text
            assert "http_requests_total" in content or "HELP" in content

    @pytest.mark.asyncio
    async def test_metrics_json_endpoint(self):
        """Test /metrics/json endpoint returns JSON format."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/metrics/json")

            assert response.status_code == 200
            data = response.json()

            assert "cache" in data
            assert "database" in data
            assert "http_requests" in data

    @pytest.mark.asyncio
    async def test_metrics_collected_on_request(self):
        """Test that metrics are collected when making requests."""
        # Reset metrics
        metrics.reset_all()

        async with AsyncClient(app=app, base_url="http://test") as client:
            # Make a request
            await client.get("/api/v1/health/live")

            # Check metrics
            metrics_response = await client.get("/api/v1/metrics")
            content = metrics_response.text

            # Should have recorded the request
            assert "http_requests_total" in content or "health" in content


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_record_request(self):
        """Test record_request function."""
        registry = MetricsRegistry()

        # Record some requests
        record_request("GET", "/api/v1/talents", 200, 0.1)
        record_request("GET", "/api/v1/talents", 200, 0.2)
        record_request("POST", "/api/v1/talents", 201, 0.3)
        record_request("GET", "/api/v1/talents/1", 404, 0.05)

        # Just verify it doesn't crash - the actual metrics are stored globally

    def test_normalize_path(self):
        """Test path normalization."""
        from app.core.metrics import _normalize_path

        assert _normalize_path("/api/v1/talents") == "/api/v1/talents"
        assert _normalize_path("/api/v1/talents/123") == "/api/v1/talents/{id}"
        assert _normalize_path("/api/v1/talents/123/works") == "/api/v1/talents/{id}/works"
        assert _normalize_path("/api/v1/schools/456") == "/api/v1/schools/{id}"
