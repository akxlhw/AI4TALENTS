"""Shared retry/circuit-breaker helpers and client config for OpenAlex data fetchers.

Split from the original data_fetchers.py monolith; WorkFetcher / AuthorFetcher /
InstitutionFetcher live in sibling modules and the package __init__ re-exports
the original public interface unchanged.
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

import aiohttp
from tenacity import (
    RetryCallState,
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.core.metrics import record_upstream_request
from app.domains.academic.services.common.openalex_utils import OPENALEX_API_BASE
from app.domains.shared.services.common.circuit_breaker import CircuitBreaker

# Circuit breaker for OpenAlex data fetchers (shared across WorkFetcher/AuthorFetcher/InstitutionFetcher)
_openalex_fetcher_breaker = CircuitBreaker(
    name="openalex_data_fetcher",
    failure_threshold=settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
    recovery_timeout=settings.CIRCUIT_BREAKER_RECOVERY_TIMEOUT,
    window_size=settings.CIRCUIT_BREAKER_WINDOW_SIZE,
)

logger = logging.getLogger(__name__)

# Maximum records to fetch per venue (0 = no limit)
# Can be overridden via environment variable
MAX_WORKS_PER_VENUE = int(os.environ.get("MAX_WORKS_PER_VENUE", "0"))  # 0 means no limit

# API 请求超时配置
DEFAULT_TIMEOUT = aiohttp.ClientTimeout(
    total=120, connect=30, sock_read=60  # 总超时 120 秒  # 连接超时 30 秒  # 读取超时 60 秒
)


class RetryableError(Exception):
    """可重试的错误（如速率限制、临时网络问题）

    Attributes:
        retry_after: 上游 429 响应 Retry-After 头给出的等待秒数（无提示则为 None）
    """

    def __init__(self, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


# Retry-After 等待上限（秒），防止上游给出超大值堵死采集链路
RETRY_AFTER_MAX_WAIT = 300.0


def _parse_retry_after(value: str | None) -> float | None:
    """Parse a Retry-After header (delta-seconds or HTTP-date) into seconds."""
    if not value:
        return None
    try:
        return max(0.0, float(value.strip()))
    except ValueError:
        pass
    try:
        retry_at = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if retry_at.tzinfo is None:
        retry_at = retry_at.replace(tzinfo=timezone.utc)
    return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())


def _rate_limited_error(response: aiohttp.ClientResponse) -> RetryableError:
    """Build a RetryableError honoring the upstream Retry-After hint."""
    return RetryableError(
        "Rate limited (HTTP 429)",
        retry_after=_parse_retry_after(response.headers.get("Retry-After")),
    )


# Host label for upstream metrics on the aiohttp path (the httpx clients are
# instrumented centrally by HttpClientFactory event hooks).
_UPSTREAM_HOST = urlparse(OPENALEX_API_BASE).hostname or "api.openalex.org"


def _record_upstream(status: int, started: float) -> None:
    """Record one outbound OpenAlex call (request count / latency / 429s)."""
    record_upstream_request(_UPSTREAM_HOST, status, time.monotonic() - started)


def _wait_honoring_retry_after(min_wait: float, max_wait: float):
    """等待策略：429 时优先尊重上游 Retry-After（封顶 RETRY_AFTER_MAX_WAIT），否则指数退避。"""
    backoff = wait_exponential(multiplier=1, min=min_wait, max=max_wait)

    def wait(retry_state: RetryCallState) -> float:
        exc = retry_state.outcome.exception() if retry_state.outcome else None
        if isinstance(exc, RetryableError) and exc.retry_after is not None:
            return min(exc.retry_after, RETRY_AFTER_MAX_WAIT)
        return backoff(retry_state)

    return wait


def with_retry(max_attempts: int = 3, min_wait: float = 1.0, max_wait: float = 60.0):
    """创建重试装饰器

    Args:
        max_attempts: 最大重试次数
        min_wait: 最小等待时间（秒）
        max_wait: 最大等待时间（秒）

    Returns:
        重试装饰器
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=_wait_honoring_retry_after(min_wait, max_wait),
        retry=retry_if_exception_type(RetryableError),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


class OpenAlexClient:
    """OpenAlex API client configuration for fetchers.

    Note: This is a lightweight config holder. Actual HTTP requests are made
    directly by the Fetcher classes using aiohttp for better async control.
    Proxy configuration is managed by HttpClientFactory.
    """

    def __init__(self, email: str | None = None):
        self.email = email
        self.base_url = OPENALEX_API_BASE

    def create_session(self, timeout=None):
        """Create aiohttp session aligned with HttpClientFactory config."""
        from app.domains.shared.services.common.http_client import HttpClientFactory

        connector = aiohttp.TCPConnector(ssl=HttpClientFactory.get_ssl_verify())
        kwargs = {"trust_env": False, "connector": connector}
        if timeout:
            kwargs["timeout"] = timeout
        return aiohttp.ClientSession(**kwargs)

    def get_proxy_for_request(self, url: str) -> str | None:
        """
        Get proxy URL for a specific request using HttpClientFactory.

        Args:
            url: Target URL

        Returns:
            Proxy URL string or None for direct connection
        """
        from app.domains.shared.services.common.http_client import HttpClientFactory

        return HttpClientFactory.get_proxy_for_url(url)
