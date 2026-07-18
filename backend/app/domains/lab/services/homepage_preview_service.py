"""Homepage preview service — fetch and clean external personal homepage HTML.

Fetches a talent's homepage URL via HttpClientFactory, cleans the HTML
(remove scripts/styles/nav, fix relative URLs), and returns a safe HTML
fragment for inline display in the detail page.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.domains.lab.models.lab_talent import LabTalent
from app.domains.shared.services.common.http_client import HttpClientFactory

logger = logging.getLogger(__name__)

# Tags to remove during cleaning
_STRIP_TAGS = (
    "script",
    "style",
    "nav",
    "footer",
    "header",
    "noscript",
    "iframe",
    "form",
    "svg",
)

# Maximum content size to return (avoid huge pages)
_MAX_HTML_LENGTH = 100_000

# Maximum response body to download before giving up
_MAX_CONTENT_LENGTH = 2 * 1024 * 1024

# Concurrent fetch limit for batch prefetch
_MAX_CONCURRENT_FETCHES = 5

# Minimum interval between requests to the same hostname (politeness)
_DOMAIN_MIN_INTERVAL_SECONDS = 0.5

# Number of retries for transient failures
_MAX_RETRIES = 3

# How long a cached homepage preview remains valid
_HOMEPAGE_CACHE_TTL_SECONDS = 7 * 24 * 3600

_USER_AGENT = "Mozilla/5.0 (compatible; AI4TalentBot/1.0)"


class _RetryableHttpError(Exception):
    """Raised when an HTTP response status indicates a transient failure."""

    def __init__(self, status_code: int):
        self.status_code = status_code
        super().__init__(f"Retryable HTTP {status_code}")


class _RetryableNetworkError(Exception):
    """Raised when a network-level error may be transient."""


class HomepagePreviewService:
    """Fetch and clean a personal homepage for inline preview."""

    # Global concurrency limit across all prefetch calls.
    _semaphore = asyncio.Semaphore(_MAX_CONCURRENT_FETCHES)

    # Per-hostname last fetch timestamp + lock for politeness scheduling.
    _domain_last_fetch: dict[str, float] = {}
    _domain_lock = asyncio.Lock()

    async def fetch_preview(self, homepage_url: str) -> dict:
        """Fetch homepage URL and return cleaned HTML + metadata.

        Returns:
            dict with keys: html, base_url, title, status
        """
        parsed = urlparse(homepage_url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            logger.warning("[HomepagePreview] Invalid URL scheme for %s", homepage_url)
            return {
                "html": "",
                "base_url": homepage_url,
                "title": "",
                "status": "invalid_url",
            }

        try:
            raw = await self._fetch_raw_with_retry(homepage_url)
        except Exception as e:
            logger.warning("[HomepagePreview] Fetch failed for %s: %s", homepage_url, str(e)[:200])
            return {
                "html": "",
                "base_url": homepage_url,
                "title": "",
                "status": "fetch_error",
            }

        if raw.get("too_large"):
            logger.warning("[HomepagePreview] Response too large for %s", homepage_url)
            return {
                "html": "",
                "base_url": homepage_url,
                "title": "",
                "status": "too_large",
            }

        if not raw.get("is_html"):
            logger.warning(
                "[HomepagePreview] Non-HTML content-type for %s: %s",
                homepage_url,
                raw.get("content_type"),
            )
            return {
                "html": "",
                "base_url": homepage_url,
                "title": "",
                "status": "not_html",
            }

        if raw["status_code"] != 200:
            logger.warning("[HomepagePreview] HTTP %d for %s", raw["status_code"], homepage_url)
            return {
                "html": "",
                "base_url": homepage_url,
                "title": "",
                "status": f"http_{raw['status_code']}",
            }

        content = raw["content"]
        # Detect BOM and fix encoding if httpx didn't
        if content.startswith(b"\xff\xfe") or content.startswith(b"\xfe\xff"):
            try:
                raw_html = content.decode("utf-16")
            except Exception:
                raw_html = content.decode("utf-8", errors="replace")
        else:
            raw_html = content.decode("utf-8", errors="replace")

        return self._clean_html(raw_html, raw["final_url"])

    @retry(
        stop=stop_after_attempt(_MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((_RetryableHttpError, _RetryableNetworkError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _fetch_raw_with_retry(self, homepage_url: str) -> dict:
        """Fetch raw response bytes with transient-failure retry."""
        return await self._fetch_raw_once(homepage_url)

    async def _fetch_raw_once(self, homepage_url: str) -> dict:
        """Single HTTP fetch using streaming to bound memory usage."""
        try:
            async with HttpClientFactory.create_client_for_url(
                homepage_url, timeout=15.0, follow_redirects=True
            ) as client:
                async with client.stream(
                    "GET",
                    homepage_url,
                    headers={"User-Agent": _USER_AGENT},
                    follow_redirects=True,
                ) as resp:
                    if resp.status_code >= 500:
                        raise _RetryableHttpError(resp.status_code)

                    content_type = resp.headers.get("content-type", "")
                    is_html = content_type.startswith("text/html") or not content_type

                    if not is_html:
                        # Don't bother reading the body for non-HTML responses.
                        return {
                            "status_code": resp.status_code,
                            "content": b"",
                            "final_url": str(resp.url),
                            "content_type": content_type,
                            "is_html": False,
                            "too_large": False,
                        }

                    content = b""
                    async for chunk in resp.aiter_bytes():
                        content += chunk
                        if len(content) > _MAX_CONTENT_LENGTH:
                            return {
                                "status_code": resp.status_code,
                                "content": b"",
                                "final_url": str(resp.url),
                                "content_type": content_type,
                                "is_html": True,
                                "too_large": True,
                            }

                    return {
                        "status_code": resp.status_code,
                        "content": content,
                        "final_url": str(resp.url),
                        "content_type": content_type,
                        "is_html": True,
                        "too_large": False,
                    }
        except _RetryableHttpError:
            raise
        except Exception as e:
            # Wrap all other network/transport errors as retryable.
            raise _RetryableNetworkError(str(e)) from e

    @staticmethod
    def _clean_html(raw_html: str, base_url: str) -> dict:
        """Clean raw HTML into a safe fragment for inline rendering."""
        soup = BeautifulSoup(raw_html, "html.parser")

        # Extract title
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else ""

        # Remove unwanted tags
        for tag in soup(_STRIP_TAGS):
            tag.decompose()

        # Remove on* attributes (inline event handlers)
        for tag in soup.find_all(True):
            for attr in list(tag.attrs):
                if attr.startswith("on"):
                    del tag.attrs[attr]

        body = soup.find("body") or soup

        # Fix relative image URLs
        for img in body.find_all("img"):
            src = img.get("src", "")
            if (
                isinstance(src, str)
                and src
                and not src.startswith(("http://", "https://", "data:"))
            ):
                img["src"] = urljoin(base_url, src)
            # Remove lazy-loading attributes that break inline display
            for attr in ("loading", "srcset"):
                if attr in img.attrs:
                    del img[attr]

        # Fix relative link URLs + open in new tab
        for a in body.find_all("a"):
            href = a.get("href", "")
            if (
                isinstance(href, str)
                and href
                and not href.startswith(("http://", "https://", "#", "mailto:", "tel:"))
            ):
                a["href"] = urljoin(base_url, href)
            a["target"] = "_blank"
            a["rel"] = "noopener noreferrer"

        # Security: strip javascript: / data: protocol URLs from href and src
        for tag in body.find_all(["a", "img", "iframe", "embed", "object"]):
            for attr in ("href", "src", "xlink:href"):
                val = tag.get(attr, "")
                if isinstance(val, str) and val.lower().lstrip().startswith(
                    ("javascript:", "vbscript:", "data:text/html")
                ):
                    del tag[attr]

        html = str(body)

        # Truncate if too large
        if len(html) > _MAX_HTML_LENGTH:
            html = html[:_MAX_HTML_LENGTH] + "\n<!-- content truncated -->"

        return {
            "html": html,
            "base_url": base_url,
            "title": title,
            "status": "ok",
        }

    async def _wait_domain_delay(self, hostname: str) -> None:
        """Enforce a minimum interval between requests to the same hostname."""
        async with self._domain_lock:
            last_fetch = self._domain_last_fetch.get(hostname, 0.0)
            elapsed = time.monotonic() - last_fetch
            sleep_for = max(0.0, _DOMAIN_MIN_INTERVAL_SECONDS - elapsed)

        if sleep_for:
            await asyncio.sleep(sleep_for)

        async with self._domain_lock:
            self._domain_last_fetch[hostname] = time.monotonic()

    async def _fetch_one(
        self, talent_id: int, name: str, homepage_url: str
    ) -> tuple[int, str, dict]:
        """Fetch a single homepage under concurrency and politeness controls."""
        parsed = urlparse(homepage_url)
        hostname = parsed.hostname or ""

        async with self._semaphore:
            await self._wait_domain_delay(hostname)
            preview = await self.fetch_preview(homepage_url)

        return talent_id, name, preview

    async def prefetch_all(
        self,
        session: AsyncSession,
        parent_lab: str,
        progress_callback: Any | None = None,
    ) -> dict:
        """Batch-fetch and cache homepage HTML for all talents in a lab.

        Processes talents concurrently while serializing DB writes. Failed
        fetches are skipped (not fatal). Progress is reported via callback.

        Args:
            session: AsyncSession for DB operations.
            parent_lab: The parent lab to scope the prefetch.
            progress_callback: Optional callable(processed, total, current_name).

        Returns:
            dict with keys: total, fetched, failed
        """
        ttl_threshold = datetime.utcnow() - timedelta(seconds=_HOMEPAGE_CACHE_TTL_SECONDS)

        # Find talents with homepage and either no cache or expired cache.
        result = await session.execute(
            select(LabTalent.talent_id, LabTalent.name, LabTalent.homepage).where(
                LabTalent.parent_lab == parent_lab,
                LabTalent.is_visible.is_(True),
                LabTalent.homepage.isnot(None),
                LabTalent.homepage != "",
                (
                    (LabTalent.homepage_cache.is_(None))
                    | (LabTalent.homepage_cached_at.is_(None))
                    | (LabTalent.homepage_cached_at < ttl_threshold)
                ),
            )
        )
        pending = result.all()
        total = len(pending)
        fetched = 0
        failed = 0
        logger.info("[HomepagePrefetch] Starting: %d talents to fetch for %s", total, parent_lab)

        if not pending:
            return {"total": 0, "fetched": 0, "failed": 0}

        tasks = [asyncio.create_task(self._fetch_one(tid, name, url)) for tid, name, url in pending]

        for idx, coro in enumerate(asyncio.as_completed(tasks), start=1):
            talent_id, name, preview = await coro

            if progress_callback:
                progress_callback(idx, total, name or f"talent_{talent_id}")

            if preview["status"] == "ok" and preview["html"]:
                talent = await session.get(LabTalent, talent_id)
                if talent:
                    talent.homepage_cache = preview["html"]
                    talent.homepage_cached_at = datetime.utcnow()
                    await session.flush()
                fetched += 1
            else:
                failed += 1
                logger.debug("[HomepagePrefetch] Failed %s: status=%s", name, preview["status"])

            # Commit every 5 items (balance between progress persistence and perf)
            if idx % 5 == 0:
                await session.commit()

        await session.commit()
        logger.info(
            "[HomepagePrefetch] Done: total=%d fetched=%d failed=%d", total, fetched, failed
        )
        return {"total": total, "fetched": fetched, "failed": failed}
