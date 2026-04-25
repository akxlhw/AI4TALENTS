"""
Rate Limit Middleware

Simple in-memory rate limiting middleware.
For production, consider using Redis-backed rate limiting.
"""

import time
from collections import defaultdict
from collections.abc import Callable
from threading import Lock

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """
    Simple in-memory rate limiter using sliding window algorithm.

    Thread-safe implementation for single-process deployments.
    For multi-process/multi-server deployments, use Redis-backed rate limiting.
    """

    def __init__(self, requests_per_minute: int = 100):
        self.requests_per_minute = requests_per_minute
        self.requests: dict[str, list[float]] = defaultdict(list)
        self.lock = Lock()

    def is_allowed(self, key: str) -> tuple[bool, int, int]:
        """
        Check if a request is allowed.

        Args:
            key: Rate limit key (user ID or IP address).

        Returns:
            Tuple of (is_allowed, remaining_requests, retry_after_seconds).
        """
        current_time = time.time()
        window_start = current_time - 60  # 1 minute window

        with self.lock:
            # Clean up old requests
            self.requests[key] = [ts for ts in self.requests[key] if ts > window_start]

            # Check if under limit
            if len(self.requests[key]) < self.requests_per_minute:
                self.requests[key].append(current_time)
                remaining = self.requests_per_minute - len(self.requests[key])
                return True, remaining, 0
            else:
                # Calculate retry after
                oldest = min(self.requests[key])
                retry_after = int(oldest + 60 - current_time) + 1
                return False, 0, retry_after

    def cleanup(self) -> None:
        """Clean up old entries to prevent memory leaks."""
        current_time = time.time()
        window_start = current_time - 60

        with self.lock:
            for key in list(self.requests.keys()):
                self.requests[key] = [ts for ts in self.requests[key] if ts > window_start]
                if not self.requests[key]:
                    del self.requests[key]


# Global rate limiter instance
rate_limiter = RateLimiter(requests_per_minute=settings.RATE_LIMIT_PER_MINUTE)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces rate limiting on API endpoints.

    Uses IP address for unauthenticated requests.
    For authenticated requests, user ID should be set in request.state.user_id.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks and docs
        if request.url.path in ["/", "/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        # Skip if rate limiting is disabled
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        # Get rate limit key
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            key = f"user:{user_id}"
        else:
            # Use X-Forwarded-For header if behind a proxy, otherwise use client IP
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                client_ip = forwarded.split(",")[0].strip()
            else:
                client_ip = request.client.host if request.client else "unknown"
            key = f"ip:{client_ip}"

        # Check rate limit
        is_allowed, remaining, retry_after = rate_limiter.is_allowed(key)

        if not is_allowed:
            logger.warning(
                f"Rate limit exceeded for {key}",
                extra={"key": key, "path": request.url.path},
            )
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please try again later.",
                    "retry_after": retry_after,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(settings.RATE_LIMIT_PER_MINUTE),
                    "X-RateLimit-Remaining": "0",
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(settings.RATE_LIMIT_PER_MINUTE)
        response.headers["X-RateLimit-Remaining"] = str(remaining)

        return response
