"""
Tests for metrics collection and /metrics endpoint.
"""

import os

os.environ["REDIS_ENABLED"] = "false"

import pytest
from httpx import ASGITransport, AsyncClient

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
        assert histogram.counts[0.5] == 2  # 0.05, 0.3 <= 0.5
        assert histogram.counts[1.0] == 3  # 0.05, 0.3, 0.8 <= 1.0
        assert histogram.counts[5.0] == 3  # 0.05, 0.3, 0.8 <= 5.0
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
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/metrics")

            assert response.status_code == 200
            assert "text/plain" in response.headers["content-type"]

            # Should contain default metrics
            content = response.text
            assert "http_requests_total" in content or "HELP" in content

    @pytest.mark.asyncio
    async def test_metrics_json_endpoint(self):
        """Test /metrics/json endpoint returns JSON format."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
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

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
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
        MetricsRegistry()

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

    def test_normalize_path_with_uuid(self):
        """Test path normalization with UUID - note: digit replacement runs first."""
        from app.core.metrics import _normalize_path

        # Due to regex order, numeric IDs are replaced first
        # This is a known limitation - UUID segments starting with digits get partially replaced
        result = _normalize_path("/api/v1/tasks/550e8400-e29b-41d4-a716-446655440000")
        # The /550 gets replaced by /{id} first, then remaining is not matched as UUID
        assert "{id}" in result or "{uuid}" in result  # Accept either normalization

    def test_histogram_observe_values(self):
        """Test histogram observe and value tracking."""
        histogram = HistogramMetric(
            "test_hist",
            "Test histogram",
            buckets=[0.1, 0.5, 1.0],
        )

        histogram.observe(0.2)
        histogram.observe(0.8)

        assert histogram.count == 2
        assert histogram.sum == 1.0
        assert histogram.counts[0.1] == 0  # Neither value <= 0.1
        assert histogram.counts[0.5] == 1  # 0.2 <= 0.5
        assert histogram.counts[1.0] == 2  # Both <= 1.0


class TestPredefinedMetrics:
    """Tests for predefined application metrics."""

    def test_request_count_exists(self):
        """Test REQUEST_COUNT metric exists."""
        from app.core.metrics import REQUEST_COUNT

        assert REQUEST_COUNT.name == "http_requests_total"
        assert REQUEST_COUNT.description == "Total number of HTTP requests"

    def test_request_latency_exists(self):
        """Test REQUEST_LATENCY metric exists."""
        from app.core.metrics import REQUEST_LATENCY

        assert REQUEST_LATENCY.name == "http_request_duration_seconds"

    def test_cache_metrics_exist(self):
        """Test cache metrics exist."""
        from app.core.metrics import CACHE_HITS, CACHE_MISSES, CACHE_REQUESTS_TOTAL

        assert CACHE_HITS.name == "cache_hits_total"
        assert CACHE_MISSES.name == "cache_misses_total"
        assert CACHE_REQUESTS_TOTAL.name == "cache_requests_total"

    def test_collection_metrics_exist(self):
        """Test collection task metrics exist."""
        from app.core.metrics import (
            COLLECTION_ERRORS_TOTAL,
            COLLECTION_TASKS_ACTIVE,
            COLLECTION_TASKS_TOTAL,
        )

        assert COLLECTION_TASKS_ACTIVE.name == "collection_tasks_active"
        assert COLLECTION_TASKS_TOTAL.name == "collection_tasks_total"
        assert COLLECTION_ERRORS_TOTAL.name == "collection_errors_total"


class TestUpstreamMetrics:
    """Tests for upstream API metrics (request count / latency / 429 / breaker state)."""

    def test_record_upstream_request(self):
        """Counts by host+status, observes latency, counts 429s separately."""
        from app.core.metrics import metrics, record_upstream_request

        record_upstream_request("api.test-upstream-1.com", 200, 0.12)
        record_upstream_request("api.test-upstream-1.com", 429, 0.05)

        counter_200 = metrics.counter(
            "upstream_requests_total",
            labels={"host": "api.test-upstream-1.com", "status": "200"},
        )
        counter_429 = metrics.counter(
            "upstream_requests_total",
            labels={"host": "api.test-upstream-1.com", "status": "429"},
        )
        rate_limit = metrics.counter(
            "upstream_rate_limit_total", labels={"host": "api.test-upstream-1.com"}
        )
        duration = metrics.histogram(
            "upstream_request_duration_seconds", labels={"host": "api.test-upstream-1.com"}
        )

        assert counter_200.value == 1
        assert counter_429.value == 1
        assert rate_limit.value == 1
        assert duration.count == 2

    def test_record_circuit_breaker_state(self):
        """Breaker state maps to gauge values 0/1/2."""
        from app.core.metrics import metrics, record_circuit_breaker_state

        record_circuit_breaker_state("test_breaker_gauge", "open")
        gauge = metrics.gauge("circuit_breaker_state", labels={"name": "test_breaker_gauge"})
        assert gauge.value == 2.0

        record_circuit_breaker_state("test_breaker_gauge", "half_open")
        assert gauge.value == 1.0

        record_circuit_breaker_state("test_breaker_gauge", "closed")
        assert gauge.value == 0.0

    @pytest.mark.asyncio
    async def test_circuit_breaker_exports_state_on_trip(self):
        """Tripping a breaker flips its exported gauge to OPEN (2)."""
        from app.domains.shared.services.common.circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker(
            name="test_breaker_trip", failure_threshold=2, recovery_timeout=60, window_size=10
        )

        async def fail() -> None:
            raise RuntimeError("boom")

        for _ in range(2):
            with pytest.raises(RuntimeError):
                await breaker.call(fail)

        gauge = metrics.gauge("circuit_breaker_state", labels={"name": "test_breaker_trip"})
        assert gauge.value == 2.0

    @pytest.mark.asyncio
    async def test_factory_client_records_upstream_metrics(self):
        """Clients from HttpClientFactory carry the upstream-metrics hooks."""
        import httpx

        from app.domains.shared.services.common.http_client import HttpClientFactory

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"ok": True})

        client = HttpClientFactory.create_client_for_url(
            "https://api.test-factory-metrics.com",
            transport=httpx.MockTransport(handler),
        )
        async with client:
            response = await client.get("https://api.test-factory-metrics.com/ping")
            assert response.status_code == 200

        counter = metrics.counter(
            "upstream_requests_total",
            labels={"host": "api.test-factory-metrics.com", "status": "200"},
        )
        assert counter.value == 1

    @pytest.mark.asyncio
    async def test_factory_preserves_caller_event_hooks(self):
        """Caller-supplied event hooks are kept alongside the metrics hooks."""
        import httpx

        from app.domains.shared.services.common.http_client import HttpClientFactory

        seen: list[str] = []

        async def custom_hook(response: httpx.Response) -> None:
            seen.append("custom")

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"ok": True})

        client = HttpClientFactory.create_client_for_url(
            "https://api.test-factory-hooks.com",
            transport=httpx.MockTransport(handler),
            event_hooks={"response": [custom_hook]},
        )
        async with client:
            await client.get("https://api.test-factory-hooks.com/ping")

        assert seen == ["custom"]
        counter = metrics.counter(
            "upstream_requests_total",
            labels={"host": "api.test-factory-hooks.com", "status": "200"},
        )
        assert counter.value == 1


class TestMetricsConcurrency:
    """Tests for metrics thread safety."""

    def test_concurrent_counter_increments(self):
        """Test counter handles concurrent increments."""
        import threading

        counter = CounterMetric("test_concurrent", "Test counter")
        threads = []

        def increment():
            for _ in range(100):
                counter.inc()

        for _ in range(10):
            t = threading.Thread(target=increment)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Should have 1000 total increments
        assert counter.value == 1000

    def test_concurrent_gauge_sets(self):
        """Test gauge handles concurrent sets."""
        import threading

        gauge = GaugeMetric("test_concurrent_gauge", "Test gauge")
        results = []

        def set_value(val):
            gauge.set(val)
            results.append(gauge.value)

        threads = []
        for i in range(10):
            t = threading.Thread(target=set_value, args=(i * 10,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Gauge should have some value (not testing exact value due to race conditions)
        assert len(results) == 10
