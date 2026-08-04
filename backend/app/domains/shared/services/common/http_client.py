"""
HTTP Client Factory for enterprise intranet proxy support.

Provides a unified way to create HTTP clients with proxy configuration.
Supports no_proxy patterns for bypassing proxy for internal services.
"""

from __future__ import annotations

import fnmatch
import logging
import time
from typing import Any
from urllib.parse import urlparse, urlunparse

import httpx

from app.core.metrics import record_upstream_request

logger = logging.getLogger(__name__)


async def _metrics_on_request(request: httpx.Request) -> None:
    """httpx event hook: stamp the request start time for latency tracking."""
    request.extensions["upstream_metrics_start"] = time.perf_counter()


async def _metrics_on_response(response: httpx.Response) -> None:
    """httpx event hook: record upstream request count / latency / 429s."""
    start = response.request.extensions.get("upstream_metrics_start")
    duration = time.perf_counter() - start if isinstance(start, float) else 0.0
    record_upstream_request(response.request.url.host or "unknown", response.status_code, duration)


class HttpClientFactory:
    """
    Unified HTTP client factory with proxy support.

    This factory provides methods to create HTTP clients (httpx, aiohttp proxy URL)
    that are configured with the appropriate proxy settings for enterprise intranet access.

    Supports no_proxy patterns to bypass proxy for internal services:
    - Exact host match: localhost, 127.0.0.1
    - Wildcard patterns: *.internal.com, 10.*, 192.168.*
    """

    _proxy_url: str | None = None
    _proxy_username: str | None = None
    _proxy_password: str | None = None
    _no_proxy: str | None = None
    _ssl_verify: bool = True

    @classmethod
    def configure(
        cls,
        proxy_url: str | None = None,
        proxy_username: str | None = None,
        proxy_password: str | None = None,
        no_proxy: str | None = None,
        ssl_verify: bool = True,
    ) -> None:
        """Configure the factory with proxy settings."""
        cls._proxy_url = proxy_url
        cls._proxy_username = proxy_username
        cls._proxy_password = proxy_password
        cls._no_proxy = no_proxy
        cls._ssl_verify = ssl_verify

        if proxy_url:
            auth_info = f" (user: {proxy_username})" if proxy_username else ""
            no_proxy_info = f", no_proxy: {no_proxy}" if no_proxy else ""
            ssl_info = f", ssl_verify: {ssl_verify}" if not ssl_verify else ""
            logger.info(
                f"HTTP client factory configured with proxy: {proxy_url}{auth_info}{no_proxy_info}{ssl_info}"
            )
        else:
            logger.info("HTTP client factory configured without proxy")

    @classmethod
    def is_proxy_enabled(cls) -> bool:
        """Check if proxy is configured."""
        return bool(cls._proxy_url)

    @classmethod
    def should_use_proxy(cls, target_url: str) -> bool:
        """Determine if a target URL should use the proxy."""
        if not cls._proxy_url:
            return False

        if not cls._no_proxy:
            return True

        # Parse target URL to extract host
        try:
            parsed = urlparse(target_url)
            host = parsed.hostname or parsed.netloc.split(":")[0]
            if not host:
                return True
        except Exception:
            return True

        # Check against no_proxy patterns
        for pattern in cls._no_proxy.split(","):
            pattern = pattern.strip()
            if pattern and cls._matches_no_proxy(host, pattern):
                logger.debug(f"URL {target_url} matches no_proxy pattern '{pattern}'")
                return False

        return True

    @classmethod
    def _matches_no_proxy(cls, host: str, pattern: str) -> bool:
        """Check if a host matches a no_proxy pattern."""
        host_lower = host.lower()
        pattern_lower = pattern.lower()

        # Exact match
        if host_lower == pattern_lower:
            return True

        # Wildcard patterns
        if "*" in pattern_lower:
            if fnmatch.fnmatch(host_lower, pattern_lower):
                return True

            # *.domain.com also matches domain.com
            if pattern_lower.startswith("*."):
                domain = pattern_lower[2:]
                if host_lower == domain or host_lower.endswith("." + domain):
                    return True

        return False

    @classmethod
    def _build_authenticated_proxy_url(cls) -> str | None:
        """Build proxy URL with authentication if configured."""
        if not cls._proxy_url:
            return None

        if cls._proxy_username and cls._proxy_password:
            parsed = urlparse(cls._proxy_url)
            netloc = f"{cls._proxy_username}:{cls._proxy_password}@{parsed.hostname}"
            if parsed.port:
                netloc += f":{parsed.port}"
            return urlunparse(
                (parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment)
            )

        return cls._proxy_url

    @classmethod
    def _merge_metrics_hooks(cls, kwargs: dict[str, Any]) -> None:
        """Attach upstream-metrics event hooks, preserving caller-supplied hooks."""
        existing = kwargs.pop("event_hooks", None) or {}
        merged: dict[str, list[Any]] = {key: list(funcs) for key, funcs in existing.items()}
        merged.setdefault("request", []).append(_metrics_on_request)
        merged.setdefault("response", []).append(_metrics_on_response)
        kwargs["event_hooks"] = merged

    @classmethod
    def create_client_for_url(
        cls,
        target_url: str,
        timeout: float = 30.0,
        **kwargs,
    ) -> httpx.AsyncClient:
        """Create an HTTP client configured for a specific target URL.

        Note: trust_env=False is set to prevent httpx from reading system
        environment variables (HTTP_PROXY, HTTPS_PROXY, NO_PROXY), ensuring
        our own proxy/no_proxy configuration takes full control.

        Every client gets upstream-metrics event hooks (request count by
        host+status, latency histogram, 429 counter) so all outbound HTTP
        through the factory is observable at /api/v1/metrics.
        """
        # Disable httpx's automatic proxy detection from environment variables
        kwargs["trust_env"] = False

        if "verify" not in kwargs:
            kwargs["verify"] = cls._ssl_verify

        cls._merge_metrics_hooks(kwargs)

        if cls.should_use_proxy(target_url):
            proxy = cls._build_authenticated_proxy_url()
            if proxy:
                logger.debug(f"Creating httpx client with proxy for: {target_url}")
                return httpx.AsyncClient(proxy=proxy, timeout=timeout, **kwargs)

        logger.debug(f"Creating httpx client with direct connection for: {target_url}")
        return httpx.AsyncClient(timeout=timeout, **kwargs)

    @classmethod
    def get_proxy_for_url(cls, target_url: str) -> str | None:
        """Get proxy URL for aiohttp requests, considering no_proxy."""
        if not cls._proxy_url or not cls.should_use_proxy(target_url):
            return None
        return cls._build_authenticated_proxy_url()

    @classmethod
    def get_no_proxy(cls) -> str | None:
        """Get the current no_proxy configuration."""
        return cls._no_proxy

    @classmethod
    def get_ssl_verify(cls) -> bool:
        """Get the current SSL verify setting."""
        return cls._ssl_verify

    @classmethod
    def reset(cls) -> None:
        """Reset proxy configuration (mainly for testing)."""
        cls._proxy_url = None
        cls._proxy_username = None
        cls._proxy_password = None
        cls._no_proxy = None
        cls._ssl_verify = True
