"""
Monitoring middleware for collecting HTTP metrics.

This middleware collects request latency, error rates, and other metrics
for Prometheus scraping via the /metrics endpoint.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.metrics import REQUEST_IN_PROGRESS, record_request


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to collect HTTP request metrics.

    Metrics collected:
    - Request count by method, path, status
    - Request latency histogram
    - In-progress request gauge
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip metrics endpoint to avoid recursion
        if request.url.path == "/metrics" or request.url.path == "/api/v1/metrics":
            return await call_next(request)

        # Track in-progress requests
        REQUEST_IN_PROGRESS.inc()
        start_time = time.perf_counter()
        status_code = 500  # Default to error status

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            # Re-raise exceptions to let error handlers deal with them
            raise
        finally:
            duration = time.perf_counter() - start_time
            REQUEST_IN_PROGRESS.dec()

            # Record metrics
            # Normalize path to avoid high cardinality
            path = self._normalize_path(request.url.path)
            record_request(
                method=request.method,
                path=path,
                status=status_code,
                duration=duration,
            )

    def _normalize_path(self, path: str) -> str:
        """
        Normalize path to reduce cardinality.

        Replaces numeric IDs and UUIDs with placeholders.
        """
        import re

        # Replace numeric IDs
        path = re.sub(r"/\d+(?=/|$)", "/{id}", path)

        # Replace UUIDs
        path = re.sub(
            r"/[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}(?=/|$)", "/{uuid}", path
        )

        return path
