"""Homepage preview service — fetch and clean external personal homepage HTML.

Fetches a talent's homepage URL via HttpClientFactory, cleans the HTML
(remove scripts/styles/nav, fix relative URLs), and returns a safe HTML
fragment for inline display in the detail page.
"""

from __future__ import annotations

import logging
from urllib.parse import urljoin

from bs4 import BeautifulSoup

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


class HomepagePreviewService:
    """Fetch and clean a personal homepage for inline preview."""

    async def fetch_preview(self, homepage_url: str) -> dict:
        """Fetch homepage URL and return cleaned HTML + metadata.

        Returns:
            dict with keys: html, base_url, title, status
        """
        try:
            async with HttpClientFactory.create_client_for_url(
                homepage_url, timeout=15.0
            ) as client:
                resp = await client.get(
                    homepage_url,
                    headers={"User-Agent": "Mozilla/5.0 (compatible; AI4TalentBot/1.0)"},
                )
        except Exception as e:
            logger.warning("[HomepagePreview] Fetch failed for %s: %s", homepage_url, str(e)[:200])
            return {"html": "", "base_url": homepage_url, "title": "", "status": "fetch_error"}

        if resp.status_code != 200:
            logger.warning("[HomepagePreview] HTTP %d for %s", resp.status_code, homepage_url)
            return {
                "html": "",
                "base_url": homepage_url,
                "title": "",
                "status": f"http_{resp.status_code}",
            }

        return self._clean_html(resp.text, homepage_url)

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
            if src and not src.startswith(("http://", "https://", "data:")):
                img["src"] = urljoin(base_url, src)
            # Remove lazy-loading attributes that break inline display
            img.pop("loading", None)
            img.pop("srcset", None)

        # Fix relative link URLs + open in new tab
        for a in body.find_all("a"):
            href = a.get("href", "")
            if href and not href.startswith(("http://", "https://", "#", "mailto:", "tel:")):
                a["href"] = urljoin(base_url, href)
            a["target"] = "_blank"
            a["rel"] = "noopener noreferrer"

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
