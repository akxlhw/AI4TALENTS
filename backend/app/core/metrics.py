"""
Application metrics collection and exposure.

Provides Prometheus-compatible metrics for monitoring:
- Request counts and latencies
- Error rates
- Database connection pool status
- Cache hit/miss rates
- Active collection tasks
"""
from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable

# Metrics storage (in-memory for simplicity)
# In production, use Prometheus client or similar


@dataclass
class CounterMetric:
    """A counter that only increases."""

    name: str
    description: str
    labels: dict[str, str] = field(default_factory=dict)
    value: float = 0.0

    def inc(self, amount: float = 1.0) -> None:
        """Increment counter by amount."""
        self.value += amount

    def reset(self) -> None:
        """Reset counter to zero."""
        self.value = 0.0


@dataclass
class GaugeMetric:
    """A gauge that can increase or decrease."""

    name: str
    description: str
    labels: dict[str, str] = field(default_factory=dict)
    value: float = 0.0

    def set(self, value: float) -> None:
        """Set gauge to value."""
        self.value = value

    def inc(self, amount: float = 1.0) -> None:
        """Increment gauge by amount."""
        self.value += amount

    def dec(self, amount: float = 1.0) -> None:
        """Decrement gauge by amount."""
        self.value -= amount


@dataclass
class HistogramMetric:
    """A histogram for tracking distributions."""

    name: str
    description: str
    labels: dict[str, str] = field(default_factory=dict)
    buckets: list[float] = field(
        default_factory=lambda: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
    )
    _counts: dict[float, int] = field(default_factory=dict, repr=False)
    sum: float = 0.0
    count: int = 0

    def __post_init__(self) -> None:
        if not self.buckets:
            self.buckets = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        self._counts = {b: 0 for b in self.buckets}
        self._counts["+Inf"] = 0

    @property
    def counts(self) -> dict[float, int]:
        return self._counts

    def observe(self, value: float) -> None:
        """Observe a value."""
        self.sum += value
        self.count += 1

        for bucket in self.buckets:
            if value <= bucket:
                self.counts[bucket] += 1
        self.counts["+Inf"] += 1


class MetricsRegistry:
    """Central registry for all metrics."""

    def __init__(self) -> None:
        self._counters: dict[str, CounterMetric] = {}
        self._gauges: dict[str, GaugeMetric] = {}
        self._histograms: dict[str, HistogramMetric] = {}

    def counter(self, name: str, description: str = "", labels: dict[str, str] | None = None) -> CounterMetric:
        """Get or create a counter metric."""
        key = self._make_key(name, labels or {})
        if key not in self._counters:
            self._counters[key] = CounterMetric(name, description, labels or {})
        return self._counters[key]

    def gauge(self, name: str, description: str = "", labels: dict[str, str] | None = None) -> GaugeMetric:
        """Get or create a gauge metric."""
        key = self._make_key(name, labels or {})
        if key not in self._gauges:
            self._gauges[key] = GaugeMetric(name, description, labels or {})
        return self._gauges[key]

    def histogram(
        self,
        name: str,
        description: str = "",
        labels: dict[str, str] | None = None,
        buckets: list[float] | None = None,
    ) -> HistogramMetric:
        """Get or create a histogram metric."""
        key = self._make_key(name, labels or {})
        if key not in self._histograms:
            self._histograms[key] = HistogramMetric(name, description, labels or {}, buckets)
        return self._histograms[key]

    def _make_key(self, name: str, labels: dict[str, str]) -> str:
        """Create a unique key for a metric."""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus text format."""
        lines = []

        # Export counters
        for metric in self._counters.values():
            lines.append(f"# HELP {metric.name} {metric.description}")
            lines.append(f"# TYPE {metric.name} counter")
            label_str = self._format_labels(metric.labels)
            lines.append(f"{metric.name}{label_str} {metric.value}")

        # Export gauges
        for metric in self._gauges.values():
            lines.append(f"# HELP {metric.name} {metric.description}")
            lines.append(f"# TYPE {metric.name} gauge")
            label_str = self._format_labels(metric.labels)
            lines.append(f"{metric.name}{label_str} {metric.value}")

        # Export histograms
        for metric in self._histograms.values():
            lines.append(f"# HELP {metric.name} {metric.description}")
            lines.append(f"# TYPE {metric.name} histogram")

            for bucket, count in metric.counts.items():
                bucket_label = "le" if bucket != "+Inf" else "le"
                bucket_value = str(bucket) if bucket != "+Inf" else "+Inf"
                labels = {**metric.labels, bucket_label: bucket_value}
                label_str = self._format_labels(labels)
                lines.append(f"{metric.name}_bucket{label_str} {count}")

            label_str = self._format_labels(metric.labels)
            lines.append(f"{metric.name}_sum{label_str} {metric.sum}")
            lines.append(f"{metric.name}_count{label_str} {metric.count}")

        return "\n".join(lines)

    def _format_labels(self, labels: dict[str, str]) -> str:
        """Format labels for Prometheus output."""
        if not labels:
            return ""
        return "{" + ", ".join(f'{k}="{v}"' for k, v in sorted(labels.items())) + "}"

    def reset_all(self) -> None:
        """Reset all metrics (useful for testing)."""
        for counter in self._counters.values():
            counter.reset()
        for gauge in self._gauges.values():
            gauge.set(0)


# Global metrics registry
metrics = MetricsRegistry()


# ============================================
# Predefined Application Metrics
# ============================================

# HTTP Request Metrics
REQUEST_COUNT = metrics.counter(
    "http_requests_total",
    "Total number of HTTP requests",
)

REQUEST_LATENCY = metrics.histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

REQUEST_IN_PROGRESS = metrics.gauge(
    "http_requests_in_progress",
    "Number of HTTP requests currently being processed",
)

# Error Metrics
ERROR_COUNT = metrics.counter(
    "app_errors_total",
    "Total number of application errors",
)

# Database Metrics
DB_CONNECTIONS_ACTIVE = metrics.gauge(
    "db_connections_active",
    "Number of active database connections",
)

DB_QUERY_LATENCY = metrics.histogram(
    "db_query_duration_seconds",
    "Database query latency in seconds",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)

# Cache Metrics
CACHE_REQUESTS_TOTAL = metrics.counter(
    "cache_requests_total",
    "Total number of cache requests",
)

CACHE_HITS = metrics.counter(
    "cache_hits_total",
    "Total number of cache hits",
)

CACHE_MISSES = metrics.counter(
    "cache_misses_total",
    "Total number of cache misses",
)

# Collection Task Metrics
COLLECTION_TASKS_ACTIVE = metrics.gauge(
    "collection_tasks_active",
    "Number of active collection tasks",
)

COLLECTION_TASKS_TOTAL = metrics.counter(
    "collection_tasks_total",
    "Total number of collection tasks started",
)

COLLECTION_ERRORS_TOTAL = metrics.counter(
    "collection_errors_total",
    "Total number of collection task errors",
)


# ============================================
# Helper Functions
# ============================================

def record_request(method: str, path: str, status: int, duration: float) -> None:
    """Record an HTTP request."""
    labels = {"method": method, "path": _normalize_path(path), "status": str(status)}
    metrics.counter("http_requests_total", labels=labels).inc()
    metrics.histogram("http_request_duration_seconds", labels={"method": method, "path": _normalize_path(path)}).observe(duration)


def record_cache_request(hit: bool, key: str | None = None) -> None:
    """Record a cache request."""
    metrics.counter("cache_requests_total").inc()
    if hit:
        metrics.counter("cache_hits_total").inc()
    else:
        metrics.counter("cache_misses_total").inc()


def record_db_query(duration: float, query_type: str = "select") -> None:
    """Record a database query."""
    metrics.histogram("db_query_duration_seconds", labels={"type": query_type}).observe(duration)


def _normalize_path(path: str) -> str:
    """Normalize path for metrics (replace IDs with placeholder)."""
    import re
    # Replace numeric IDs with {id}
    path = re.sub(r"/\d+", "/{id}", path)
    # Replace UUIDs with {uuid}
    path = re.sub(r"/[a-f0-9-]{36}", "/{uuid}", path)
    return path


class MetricsMiddleware:
    """
    ASGI middleware to collect HTTP metrics.

    Usage:
        app = FastAPI()
        app.add_middleware(MetricsMiddleware)
    """

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope["method"]
        path = scope["path"]

        # Skip metrics endpoint itself
        if path == "/metrics":
            await self.app(scope, receive, send)
            return

        # Track in-progress requests
        REQUEST_IN_PROGRESS.inc()
        start_time = time.perf_counter()

        # Capture status code
        status_code = 500

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration = time.perf_counter() - start_time
            REQUEST_IN_PROGRESS.dec()
            record_request(method, path, status_code, duration)
