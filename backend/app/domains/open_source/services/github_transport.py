"""GitHub HTTP transport - request execution, throttling, retry, breaker.

Owns the httpx client lifecycle (created via ``HttpClientFactory`` so proxy
configuration applies), paces requests from the configured per-token hourly
limit, wraps retryable failures with tenacity, and guards the endpoint with a
circuit breaker. Token selection state lives in
``github_token_pool.GitHubTokenPool``; business endpoints live in ``github_api``.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.domains.open_source.services.github_token_pool import GitHubTokenPool
from app.domains.shared.services.common.circuit_breaker import CircuitBreaker
from app.domains.shared.services.common.http_client import HttpClientFactory

_github_breaker = CircuitBreaker(
    name="github",
    failure_threshold=settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
    recovery_timeout=settings.CIRCUIT_BREAKER_RECOVERY_TIMEOUT,
    window_size=settings.CIRCUIT_BREAKER_WINDOW_SIZE,
)

logger = logging.getLogger(__name__)

# Re-exported so upper layers (github_api) can catch transport-level failures
# without importing httpx directly — httpx stays confined to this module.
HTTPStatusError = httpx.HTTPStatusError


class RateLimitExhaustedError(Exception):
    """All tokens in the pool are rate-limited; fail fast instead of sleeping.

    Carries ``retry_after`` (seconds until the earliest reset window) so the
    task layer can mark the task as retryable and surface the wait time,
    rather than blocking the request path for up to an hour.
    """

    def __init__(self, message: str, retry_after: int | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


def _is_retryable(exc: BaseException) -> bool:
    """Determine if an exception is worth retrying.

    - Network/timeout errors: always retry
    - 429 (rate limit): retry (token may refresh or reset window passes)
    - 5xx (server error): retry (transient)
    - 4xx client errors (401, 403, 404, etc.): do NOT retry
    """
    if isinstance(exc, (httpx.NetworkError, httpx.TimeoutException)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code == 429 or exc.response.status_code >= 500
    return False


class GitHubTransport:
    """Executes GitHub REST requests with throttling, rotation-aware auth,
    retry and circuit-breaking."""

    def __init__(
        self,
        base_url: str | None = None,
        token_pool: GitHubTokenPool | None = None,
    ) -> None:
        self.base_url = (base_url or settings.GITHUB_BASE_URL).rstrip("/")
        self.pool = token_pool or GitHubTokenPool()
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "AI4TALENTS/2.0.4",
        }
        self._client: httpx.AsyncClient | None = None
        self._last_request_time: float = 0.0
        # Pace requests from the configured per-token hourly limit
        # (GITHUB_RATE_LIMIT, default 5000/h); the token pool multiplies
        # aggregate throughput, so the interval shrinks with pool size.
        token_count = max(len(self.pool.tokens), 1)
        self._min_interval: float = 3600.0 / (max(settings.GITHUB_RATE_LIMIT, 1) * token_count)

    async def __aenter__(self) -> GitHubTransport:
        self._client = HttpClientFactory.create_client_for_url(
            target_url=self.base_url,
            timeout=settings.HTTP_TIMEOUT_DEFAULT,
            headers=self.headers,
            follow_redirects=True,
        )
        logger.info(
            f"GitHubClient initialized with {len(self.pool.tokens)} token(s), "
            f"base_url={self.base_url}"
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()

    async def _throttle(self) -> None:
        """Ensure minimum interval between requests."""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self._min_interval:
            await asyncio.sleep(self._min_interval - elapsed)

    async def do_get_request(
        self, path: str, params: dict[str, Any] | None = None
    ) -> httpx.Response:
        """Execute raw GET request with throttling."""
        await self._throttle()
        if not self._client:
            raise RuntimeError("Client not initialized. Use async with.")
        url = f"{self.base_url}{path}"
        # Auth goes on the request, not the client: httpx snapshots client
        # headers at creation, so rotating current_token_idx would otherwise
        # never change the token actually sent (the pool stayed unused).
        request_headers: dict[str, str] = {}
        token = self.pool.current_token()
        if token:
            request_headers["Authorization"] = f"Bearer {token}"
        response = await self._client.get(url, params=params, headers=request_headers)
        self._last_request_time = time.time()
        return response

    async def do_get_full(
        self, path: str, params: dict[str, Any] | None = None
    ) -> httpx.Response | None:
        """Core GET logic (rate-limit handling, token rotation); returns the
        raw response, or None for 404."""
        # Proactively pick the healthiest token before each request
        self.pool.pick_best()

        response = await self.do_get_request(path, params)

        # Record rate limit state from every response (not just errors)
        self.pool.record_rate_limit(response.headers)

        if response.status_code == 404:
            logger.warning(f"GitHub API 404: {path}")
            return None  # explicit None distinguishes "not found" from "success empty"

        if response.status_code in (401, 403, 429):
            reset_at = response.headers.get("X-RateLimit-Reset")
            remaining = response.headers.get("X-RateLimit-Remaining")
            logger.warning(
                f"GitHub auth/rate limit hit for {path} (HTTP {response.status_code}), "
                f"remaining={remaining}, reset_at={reset_at}, "
                f"token_idx={self.pool.current_token_idx}"
            )

            if response.status_code == 401:
                # Bad credentials: blacklist this token so neither
                # pick_best nor switch_to_best_alternative selects it again.
                self.pool.blacklist_current()

            # Try switching to the best alternative token (not round-robin)
            if self.pool.switch_to_best_alternative():
                logger.info(
                    f"Switched to token #{self.pool.current_token_idx + 1} "
                    f"(remaining={self.pool._token_remaining.get(self.pool.current_token_idx, '?')})"
                )
                # No client rebuild needed: auth is applied per request
                response = await self.do_get_request(path, params)
            elif reset_at and response.status_code != 401:
                # Rate-limited (403/429) with no tokens left. Fail fast and let
                # the task layer decide when to retry — never sleep inside the
                # request path (previously blocked up to 1h, deadlocking the
                # whole collection pipeline). Skipped for 401: bad credentials
                # won't heal by waiting.
                wait_seconds = max(0, int(reset_at) - int(time.time()) + 1)
                logger.warning(
                    f"All tokens exhausted for {path}; failing fast "
                    f"(retry_after={wait_seconds}s)"
                )
                raise RateLimitExhaustedError(
                    f"GitHub rate limit exhausted for all tokens, " f"retry after {wait_seconds}s",
                    retry_after=wait_seconds,
                )

        response.raise_for_status()
        return response

    async def get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Core GET logic returning parsed JSON; None means 404.

        See do_get_full for the raw response variant (needed when response
        headers carry data).
        """
        response = await self.do_get_full(path, params)
        return None if response is None else response.json()

    @retry(
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def get_with_retry(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Retry wrapper around the core request logic."""
        return await self.get_json(path, params)

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Generic GET with circuit breaker, rate-limit handling, token rotation, and retry."""
        if not settings.CIRCUIT_BREAKER_ENABLED:
            return await self.get_with_retry(path, params)
        return await _github_breaker.call(self.get_with_retry, path, params)
