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
                homepage_url, timeout=15.0, follow_redirects=True
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

        # Handle encoding: some academic sites return UTF-16 or other non-UTF-8
        # encodings. httpx may detect this via Content-Type charset or BOM.
        # Use resp.text (which respects encoding) instead of raw bytes.
        content = resp.content
        # Detect BOM and fix encoding if httpx didn't
        if content.startswith(b"\xff\xfe") or content.startswith(b"\xfe\xff"):
            # UTF-16 BOM — decode explicitly
            try:
                raw_html = content.decode("utf-16")
            except Exception:
                raw_html = resp.text
        else:
            raw_html = resp.text

        return self._clean_html(raw_html, homepage_url)

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
            for attr in ("loading", "srcset"):
                if attr in img.attrs:
                    del img[attr]

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

    async def prefetch_all(
        self,
        session,
        parent_lab: str,
        progress_callback=None,
    ) -> dict:
        """Batch-fetch and cache homepage HTML for all talents in a lab.

        Only processes talents that have a homepage URL and no cached HTML yet.
        Failed fetches are skipped (not fatal). Progress is reported via callback.

        Args:
            session: AsyncSession for DB operations.
            parent_lab: The parent lab to scope the prefetch.
            progress_callback: Optional callable(processed, total, current_name).

        Returns:
            dict with keys: total, fetched, skipped, errors
        """
        from datetime import datetime

        from sqlalchemy import select

        from app.domains.lab.models.lab_talent import LabTalent

        # Find talents with homepage but no cache
        result = await session.execute(
            select(LabTalent.talent_id, LabTalent.name, LabTalent.homepage).where(
                LabTalent.parent_lab == parent_lab,
                LabTalent.is_visible.is_(True),
                LabTalent.homepage.isnot(None),
                LabTalent.homepage != "",
                LabTalent.homepage_cache.is_(None),
            )
        )
        pending = result.all()
        total = len(pending)
        fetched = 0
        errors = 0
        logger.info("[HomepagePrefetch] Starting: %d talents to fetch for %s", total, parent_lab)

        for idx, (talent_id, name, homepage_url) in enumerate(pending, start=1):
            if progress_callback:
                progress_callback(idx, total, name or f"talent_{talent_id}")

            try:
                preview = await self.fetch_preview(homepage_url)
                if preview["status"] == "ok" and preview["html"]:
                    # Update cache
                    talent = await session.get(LabTalent, talent_id)
                    if talent:
                        talent.homepage_cache = preview["html"]
                        talent.homepage_cached_at = datetime.now()
                        await session.flush()
                    fetched += 1
                else:
                    errors += 1
                    logger.debug(
                        "[HomepagePrefetch] Skipped %s: status=%s", name, preview["status"]
                    )
            except Exception as e:
                errors += 1
                logger.warning(
                    "[HomepagePrefetch] Error fetching %s (%s): %s",
                    name,
                    homepage_url,
                    str(e)[:200],
                )

            # Commit every 5 items (balance between progress persistence and perf)
            if idx % 5 == 0:
                await session.commit()

        await session.commit()
        logger.info(
            "[HomepagePrefetch] Done: total=%d fetched=%d errors=%d", total, fetched, errors
        )
        return {"total": total, "fetched": fetched, "skipped": total - fetched, "errors": errors}
