"""Per-API-key rate limiter (in-memory sliding window).

Enforces `shared_api_key.rate_limit_per_minute` when set. Single-process only
— multi-instance deployments need a Redis-backed implementation (same
limitation as the global middleware limiter).
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock


class ApiKeyRateLimiter:
    """Sliding-window limiter keyed by api_key_id."""

    def __init__(self) -> None:
        self._hits: dict[int, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, api_key_id: int, limit_per_minute: int) -> int:
        """Record a hit; return 0 when allowed, else retry-after seconds."""
        now = time.monotonic()
        window_start = now - 60.0
        with self._lock:
            hits = self._hits[api_key_id]
            while hits and hits[0] <= window_start:
                hits.popleft()
            if len(hits) >= limit_per_minute:
                return int(hits[0] + 60.0 - now) + 1
            hits.append(now)
            return 0

    def reset(self) -> None:
        """Clear all buckets (test isolation)."""
        with self._lock:
            self._hits.clear()


api_key_rate_limiter = ApiKeyRateLimiter()
