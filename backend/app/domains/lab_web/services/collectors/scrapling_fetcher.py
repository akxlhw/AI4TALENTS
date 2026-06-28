"""Fetch + parse layer for lab People pages.

Architecture (spec §5.3, alternative path chosen in Task 8):
HTTP fetching goes through AI4TALENT's HttpClientFactory (httpx.AsyncClient),
which keeps corporate proxy / SSL / timeout config uniform and complies with
the project's HTTP-client-unity rule (no direct httpx import here). Scrapling
is used ONLY for its Selector (HTML parsing) — its Fetcher/DynamicFetcher are
not used because they require the heavy `scrapling[fetchers]` extra and pull
in curl_cffi/playwright. Static pages (SAIL v1) are fully covered by httpx.

The `robots_disallows` attribute is populated by check_robots_txt() so
BaseLabCollector._guard_robots_txt can enforce compliance.
"""

from __future__ import annotations

import logging
import urllib.robotparser
from typing import Any
from urllib.parse import urlparse

from app.core.config import settings
from app.domains.shared.services.common.http_client import HttpClientFactory

logger = logging.getLogger(__name__)

USER_AGENT = "AI4TALENT-LabWebCollector/1.0"
FETCH_TIMEOUT = float(getattr(settings, "HTTP_TIMEOUT_DEFAULT", 30.0))


class ScraplingFetcher:
    """Async fetcher: httpx transport (via HttpClientFactory) + Scrapling Selector.

    fetch(url) -> scrapling Selector for the page.
    check_robots_txt(url) -> bool : True if the URL path is allowed; caches
    disallowed people URLs in self.robots_disallows.
    """

    def __init__(self, fetch_mode: str = "static") -> None:
        self.fetch_mode = fetch_mode
        # URLs disallowed by robots.txt, populated by check_robots_txt.
        self.robots_disallows: set[str] = set()

    async def is_allowed_by_robots(self, url: str) -> bool:
        """Fetch and evaluate /robots.txt for the given URL. Caches disallow.

        Network errors or a missing robots.txt are treated as allow (open site).
        """
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        try:
            async with HttpClientFactory.create_client_for_url(
                robots_url, timeout=FETCH_TIMEOUT
            ) as client:
                resp = await client.get(robots_url, headers={"User-Agent": USER_AGENT})
            if resp.status_code >= 400:
                # No robots.txt (404) or unreachable => treat as allow.
                return True
            rp = urllib.robotparser.RobotFileParser()
            rp.parse(resp.text.splitlines())
            allowed = rp.can_fetch(USER_AGENT, url)
            if not allowed:
                self.robots_disallows.add(url)
            return allowed
        except Exception:
            logger.warning("robots.txt check failed for %s; allowing", url, exc_info=True)
            return True

    async def fetch(self, url: str) -> Any:
        """Fetch HTML via httpx (HttpClientFactory) and return a Scrapling Selector."""
        from scrapling.parser import Selector  # deferred: keep base install light

        async with HttpClientFactory.create_client_for_url(url, timeout=FETCH_TIMEOUT) as client:
            resp = await client.get(url, headers={"User-Agent": USER_AGENT})
            resp.raise_for_status()

        return Selector(resp.text)
