"""Abstract base collector for lab-site People pages (v2, LLM-driven).

Flow (collect()):
  1. preflight (site active, people_url)
  2. robots.txt guard
  3. fetch HTML (reuses v1 ScraplingFetcher)
  4. compute html_hash
  5. cache check: parsed page for (site_code, html_hash)?
     -> hit: reuse parsed_persons, skip to step 8
  6. preprocess HTML (strip script/style/nav, cap size)
  7. LLM parse + schema validation (retry once; needs_review on failure/empty)
  8. write lw_site_raw_page snapshot
  9. convert to lw_raw_person rows
  10. sync to core_talent (source_type=lab_web_site)

All steps fixed in the base class; sites are config-driven (no subclasses).
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from app.domains.lab_web.services.collectors.html_preprocessor import preprocess_html
from app.domains.lab_web.services.collectors.llm_parser import parse_persons_from_html
from app.domains.lab_web.services.collectors.prompts import SITE_PEOPLE_PARSE_PROMPT

if TYPE_CHECKING:
    from app.domains.lab_web.models.lab_web_site import LWSiteConfig
    from app.domains.lab_web.repositories.lab_web.site import LWSiteRepository
    from app.domains.lab_web.services.collectors.scrapling_fetcher import ScraplingFetcher
    from app.domains.lab_web.services.lw_site_person_service import LWSitePersonService

logger = logging.getLogger(__name__)


@dataclass
class SiteCollectContext:
    task_id: int
    site_code: str
    force_reparse: bool = False
    cancelled: asyncio.Event = field(default_factory=asyncio.Event)


class BaseLabSiteCollector:
    """LLM-driven collector for a lab-site People page. Config-driven, no subclasses."""

    def __init__(
        self,
        fetcher: ScraplingFetcher,
        site: LWSiteConfig,
        repo: LWSiteRepository,
        person_service: LWSitePersonService,
        llm_gateway: Any,
    ) -> None:
        self.fetcher = fetcher
        self.site = site
        self.repo = repo
        self.person_service = person_service
        self.llm_gateway = llm_gateway

    async def collect(self, ctx: SiteCollectContext) -> None:
        """Fixed main flow."""
        await self._preflight()
        await self._guard_robots_txt()
        html = await self.fetcher.fetch(str(self.site.people_url))
        # Tolerate a response wrapper (e.g. a FakeResponse with .html) — v1
        # ScraplingFetcher.fetch returns a Scrapling Selector whose str() is the
        # parsed HTML; tests may pass a plain string or a wrapper.
        if hasattr(html, "html") and not isinstance(html, str):
            html = html.html
        html_str = str(html)
        # Cache key is the raw HTML hash (I3, acknowledged): real lab pages may
        # embed dynamic tokens/timestamps that bust the cache, forcing a reparse.
        # Correctness is unaffected (cache is a cost optimization); if cache-hit
        # rates are low in production, consider hashing the preprocessed text
        # instead so cosmetic changes don't trigger an LLM call.
        html_hash = hashlib.sha256(html_str.encode("utf-8")).hexdigest()

        # Step 5: cache check
        parsed_persons: list[dict] | None = None
        site_code = str(self.site.site_code)
        if not ctx.force_reparse:
            cached = await self.repo.find_cached_page(site_code, html_hash)
            if cached is not None and cached.parsed_persons:
                cached_persons: list[dict] = list(cached.parsed_persons)
                parsed_persons = cached_persons
                logger.info(
                    "lab_web_site cache hit: site=%s hash=%s -> %d persons (no LLM call)",
                    site_code,
                    html_hash,
                    len(cached_persons),
                )

        # Step 6+7: parse if not cached
        parse_status = "parsed"
        parse_error: str | None = None
        llm_model: str | None = None
        llm_tokens: int | None = None
        if parsed_persons is None:
            cleaned = preprocess_html(html_str)
            result = await parse_persons_from_html(
                self.llm_gateway, cleaned, SITE_PEOPLE_PARSE_PROMPT
            )
            llm_tokens = result.tokens_used
            llm_model = getattr(self.llm_gateway, "model", None)
            if not result.ok or not result.persons:
                parse_status = "needs_review"
                parse_error = result.error or "unknown parse failure"
                logger.warning(
                    "lab_web_site parse needs_review: site=%s err=%s",
                    self.site.site_code,
                    parse_error,
                )
                parsed_persons = None
            else:
                parsed_persons = [p.model_dump() for p in result.persons]

        # Step 8: write raw page snapshot
        await self.repo.insert_raw_page(
            site_code=site_code,
            people_url=str(self.site.people_url),
            html_content=html_str,
            html_hash=html_hash,
            parsed_persons=parsed_persons,
            parse_status=parse_status,
            parse_error=parse_error,
            llm_model=llm_model,
            llm_tokens_used=llm_tokens,
        )

        # Step 9+10: if parsed, write raw persons + sync core_talent
        if parse_status == "parsed" and parsed_persons:
            raw_rows = await self.repo.upsert_site_raw_persons(
                site_code=site_code,
                parent_lab_code=str(self.site.parent_lab_code),
                parsed_persons=parsed_persons,
                task_id=ctx.task_id,
            )
            sync_result = await self.person_service.sync_to_core_talent(raw_rows)
            logger.info(
                "lab_web_site collect done: site=%s raw=%d synced=%d",
                self.site.site_code,
                len(raw_rows),
                sync_result.synced,
            )
        else:
            logger.info(
                "lab_web_site collect done: site=%s (needs_review, nothing synced)",
                self.site.site_code,
            )

    async def _preflight(self) -> None:
        if not self.site.is_active:
            raise RuntimeError(f"Site {self.site.site_code} is not active")

    async def _guard_robots_txt(self) -> None:
        allowed = await self.fetcher.is_allowed_by_robots(str(self.site.people_url))
        if not allowed:
            raise PermissionError(f"people_url {self.site.people_url} disallowed by robots.txt")
