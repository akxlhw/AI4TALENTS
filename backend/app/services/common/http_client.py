"""
HTTP Client Factory for enterprise intranet proxy support.

Provides a unified way to create HTTP clients with proxy configuration.
Supports no_proxy patterns for bypassing proxy for internal services.
"""
from __future__ import annotations

import fnmatch
import logging
from typing import Optional
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)


class HttpClientFactory:
    """
    Unified HTTP client factory with proxy support.

    This factory provides methods to create HTTP clients (httpx, aiohttp proxy URL)
    that are configured with the appropriate proxy settings for enterprise intranet access.

    Supports no_proxy patterns to bypass proxy for internal services:
    - Exact host match: localhost, 127.0.0.1
    - Wildcard patterns: *.internal.com, 10.*, 192.168.*

    Usage:
        # At application startup, configure the factory
        HttpClientFactory.configure(
            proxy_url="http://proxy.company.com:8080",
            no_proxy="localhost,127.0.0.1,*.internal.com"
        )

        # Create clients as needed
        async_client = HttpClientFactory.create_async_client()
        proxy_url = HttpClientFactory.get_aiohttp_proxy()  # For aiohttp

        # Check if a URL should use proxy
        if HttpClientFactory.should_use_proxy("http://llm.internal.com"):
            # Use proxy
        else:
            # Direct connection
    """

    _proxy_url: Optional[str] = None
    _proxy_username: Optional[str] = None
    _proxy_password: Optional[str] = None
    _no_proxy: Optional[str] = None  # 不走代理的地址列表

    @classmethod
    def configure(
        cls,
        proxy_url: Optional[str] = None,
        proxy_username: Optional[str] = None,
        proxy_password: Optional[str] = None,
        no_proxy: Optional[str] = None,
    ) -> None:
        """
        Configure the factory with proxy settings.

        Args:
            proxy_url: Proxy server URL (e.g., "http://proxy.company.com:8080")
            proxy_username: Proxy username (optional)
            proxy_password: Proxy password (optional)
            no_proxy: Comma-separated list of addresses to bypass proxy
                      (e.g., "localhost,127.0.0.1,*.internal.com,10.*,192.168.*")
        """
        cls._proxy_url = proxy_url
        cls._proxy_username = proxy_username
        cls._proxy_password = proxy_password
        cls._no_proxy = no_proxy

        if proxy_url:
            auth_info = ""
            if proxy_username:
                auth_info = f" (user: {proxy_username})"
            no_proxy_info = f", no_proxy: {no_proxy}" if no_proxy else ""
            logger.info(f"HTTP client factory configured with proxy: {proxy_url}{auth_info}{no_proxy_info}")
        else:
            logger.info("HTTP client factory configured without proxy")

    @classmethod
    def is_proxy_enabled(cls) -> bool:
        """Check if proxy is configured."""
        return cls._proxy_url is not None and cls._proxy_url != ""

    @classmethod
    def should_use_proxy(cls, target_url: str) -> bool:
        """
        Determine if a target URL should use the proxy.

        Args:
            target_url: The URL to check

        Returns:
            True if the URL should use proxy, False if it should bypass
        """
        # No proxy configured
        if not cls._proxy_url:
            return False

        # No no_proxy patterns defined
        if not cls._no_proxy:
            return True

        # Parse the target URL to extract host
        try:
            parsed = urlparse(target_url)
            host = parsed.hostname or parsed.netloc.split(':')[0]
            if not host:
                return True  # Can't parse, use proxy by default
        except Exception:
            return True  # Can't parse, use proxy by default

        # Check against no_proxy patterns
        no_proxy_list = [p.strip() for p in cls._no_proxy.split(',') if p.strip()]

        for pattern in no_proxy_list:
            if cls._matches_no_proxy(host, pattern):
                logger.debug(f"URL {target_url} matches no_proxy pattern '{pattern}', bypassing proxy")
                return False

        return True

    @classmethod
    def _matches_no_proxy(cls, host: str, pattern: str) -> bool:
        """
        Check if a host matches a no_proxy pattern.

        Supports:
        - Exact match: localhost, 127.0.0.1
        - Wildcard prefix: *.internal.com
        - Wildcard suffix: 10.*, 192.168.*
        - Wildcard both: *.internal.*

        Args:
            host: The hostname to check
            pattern: The no_proxy pattern

        Returns:
            True if the host matches the pattern
        """
        # Case-insensitive comparison
        host_lower = host.lower()
        pattern_lower = pattern.lower()

        # Exact match
        if host_lower == pattern_lower:
            return True

        # Wildcard patterns using fnmatch-style matching
        # *.internal.com -> matches llm.internal.com, api.internal.com
        # 10.* -> matches 10.0.0.1, 10.20.30.40
        # 192.168.* -> matches 192.168.1.1, 192.168.100.50
        if '*' in pattern_lower:
            # fnmatch handles wildcards: * matches any sequence
            if fnmatch.fnmatch(host_lower, pattern_lower):
                return True

            # Also check if pattern is *.domain.com and host is domain.com
            if pattern_lower.startswith('*.'):
                domain = pattern_lower[2:]  # Remove *.
                if host_lower == domain or host_lower.endswith('.' + domain):
                    return True

        return False

    @classmethod
    def get_no_proxy(cls) -> Optional[str]:
        """Get the current no_proxy configuration."""
        return cls._no_proxy

    @classmethod
    def create_async_client(
        cls,
        timeout: float = 30.0,
        **kwargs,
    ) -> httpx.AsyncClient:
        """
        Create an async HTTP client with proxy configuration.

        Args:
            timeout: Request timeout in seconds
            **kwargs: Additional arguments passed to httpx.AsyncClient

        Returns:
            Configured httpx.AsyncClient instance
        """
        proxy = None
        if cls._proxy_url:
            if cls._proxy_username and cls._proxy_password:
                # Build proxy URL with authentication
                # Parse the URL and inject credentials
                from urllib.parse import urlparse, urlunparse

                parsed = urlparse(cls._proxy_url)
                netloc = f"{cls._proxy_username}:{cls._proxy_password}@{parsed.hostname}"
                if parsed.port:
                    netloc += f":{parsed.port}"
                proxy = urlunparse((
                    parsed.scheme,
                    netloc,
                    parsed.path,
                    parsed.params,
                    parsed.query,
                    parsed.fragment,
                ))
            else:
                proxy = cls._proxy_url

        if proxy:
            logger.debug(f"Creating httpx.AsyncClient with proxy: {cls._proxy_url}")
            return httpx.AsyncClient(
                proxy=proxy,
                timeout=timeout,
                **kwargs,
            )
        else:
            return httpx.AsyncClient(
                timeout=timeout,
                **kwargs,
            )

    @classmethod
    def get_aiohttp_proxy(cls) -> Optional[str]:
        """
        Get proxy URL for aiohttp requests.

        aiohttp uses a different proxy mechanism - it accepts the proxy URL
        directly in the request method, not in the session.

        For authenticated proxy, returns the URL with credentials embedded.

        Returns:
            Proxy URL string or None if no proxy configured
        """
        if not cls._proxy_url:
            return None

        if cls._proxy_username and cls._proxy_password:
            # Build proxy URL with authentication
            from urllib.parse import urlparse, urlunparse

            parsed = urlparse(cls._proxy_url)
            netloc = f"{cls._proxy_username}:{cls._proxy_password}@{parsed.hostname}"
            if parsed.port:
                netloc += f":{parsed.port}"
            return urlunparse((
                parsed.scheme,
                netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment,
            ))

        return cls._proxy_url

    @classmethod
    def get_proxy_url_for_openai(cls) -> Optional[str]:
        """
        Get proxy URL for OpenAI client.

        OpenAI Python SDK accepts proxy URL directly via http_client parameter.
        We create a custom httpx client with the proxy.

        Returns:
            Proxy URL string or None if no proxy configured
        """
        return cls._proxy_url

    @classmethod
    def get_proxy_for_url(cls, target_url: str) -> Optional[str]:
        """
        Get the proxy URL to use for a specific target URL.

        This method considers no_proxy patterns to determine if the target
        should bypass the proxy.

        Args:
            target_url: The URL to be requested

        Returns:
            Proxy URL string if proxy should be used, None for direct connection
        """
        if not cls._proxy_url:
            return None

        if cls.should_use_proxy(target_url):
            return cls.get_aiohttp_proxy()

        return None

    @classmethod
    def create_client_for_url(
        cls,
        target_url: str,
        timeout: float = 30.0,
        **kwargs,
    ) -> httpx.AsyncClient:
        """
        Create an HTTP client configured for a specific target URL.

        This method automatically determines whether to use proxy based on
        the target URL and no_proxy configuration.

        Args:
            target_url: The URL to be requested
            timeout: Request timeout in seconds
            **kwargs: Additional arguments passed to httpx.AsyncClient

        Returns:
            Configured httpx.AsyncClient instance
        """
        if cls.should_use_proxy(target_url):
            # Use proxy - create client with proxy
            proxy = cls.get_aiohttp_proxy()
            if proxy:
                logger.debug(f"Creating httpx.AsyncClient with proxy for URL: {target_url}")
                return httpx.AsyncClient(proxy=proxy, timeout=timeout, **kwargs)

        # Direct connection
        logger.debug(f"Creating httpx.AsyncClient with direct connection for URL: {target_url}")
        return httpx.AsyncClient(timeout=timeout, **kwargs)

    @classmethod
    def reset(cls) -> None:
        """Reset proxy configuration (mainly for testing)."""
        cls._proxy_url = None
        cls._proxy_username = None
        cls._proxy_password = None
        cls._no_proxy = None
