"""Abstract base collector that fixes the scrape flow; subclasses fill hooks.

Flow (collect()):
  1. preflight (lab active, fetch_mode)
  2. robots.txt guard
  3. fetch entry page via ScraplingFetcher
  4. parse_person_cards (hook) -> cards
  5. get_next_page_url (hook, optional) -> loop back to 3
  6. extract_person (hook) per card -> RawPersonDraft
  7. normalize (shared: email/name/role)
  8. write raw layer
  9. sync to core_talent
  10. update task status + lab.last_collected_at

Steps 1,2,3,5,8,9,10 are fixed; 4 and 6 are abstract hooks.
"""
from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.domains.lab_web.models.lab_web import LWLabRegistry
    from app.domains.lab_web.repositories.lab_web import LWRepository
    from app.domains.lab_web.services.collectors.scrapling_fetcher import ScraplingFetcher
    from app.domains.lab_web.services.lw_person_service import LWPersonService

logger = logging.getLogger(__name__)


@dataclass
class RawPersonDraft:
    """A person parsed from a card, pre-normalization, not yet persisted."""

    name_raw: str
    title_raw: str | None = None
    email_raw: str | None = None
    homepage_url: str | None = None
    avatar_url: str | None = None
    source_url: str | None = None
    extra: dict[str, Any] | None = None


@dataclass
class CollectContext:
    """Shared context for one collection run."""

    task_id: int
    lab_id: int
    cancelled: asyncio.Event = field(default_factory=asyncio.Event)


class BaseLabCollector(ABC):
    """Abstract lab collector. Subclasses implement the parse/extract hooks."""

    lab_code: str = ""
    request_delay: float = 1.0  # seconds between requests (per lab, sequential)
    max_pages: int = 50  # pagination guard

    def __init__(
        self,
        fetcher: "ScraplingFetcher",
        lab: "LWLabRegistry",
        repo: "LWRepository",
        person_service: "LWPersonService",
    ) -> None:
        self.fetcher = fetcher
        self.lab = lab
        self.repo = repo
        self.person_service = person_service

    async def collect(self, ctx: CollectContext) -> None:
        """Fixed main flow. Subclasses should not override."""
        await self._preflight()
        await self._guard_robots_txt()
        drafts: list[RawPersonDraft] = []
        url: str | None = self.lab.people_url
        pages = 0
        while url and pages < self.max_pages:
            if ctx.cancelled.is_set():
                await self.repo.update_task(ctx.task_id, status="cancelled")
                return
            response = await self.fetcher.fetch(url)
            cards = self.parse_person_cards(response)
            for card in cards:
                try:
                    drafts.append(self.extract_person(card))
                except Exception:
                    logger.warning("extract_person failed for a card; skipping", exc_info=True)
            await self.repo.update_task(
                ctx.task_id,
                current_step=f"page {pages + 1}, {len(drafts)} persons so far",
            )
            url = self.get_next_page_url(response)
            pages += 1
            if url:
                await asyncio.sleep(self.request_delay)

        await self.repo.update_task(
            ctx.task_id, total_records=len(drafts), current_step="persisting"
        )
        raw_rows = await self.repo.upsert_raw_persons(
            lab_id=ctx.lab_id,
            drafts=drafts,
            task_id=ctx.task_id,
            lab_code=self.lab_code or self.lab.lab_code,
        )
        sync_result = await self.person_service.sync_to_core_talent(raw_rows, self.lab)
        logger.info(
            "lab_web collect done: lab=%s raw=%d synced=%d",
            self.lab.lab_code, len(raw_rows), sync_result.synced,
        )

    async def _preflight(self) -> None:
        if not self.lab.is_active:
            raise RuntimeError(f"Lab {self.lab.lab_code} is not active")
        if self.lab.fetch_mode not in ("static", "dynamic"):
            raise RuntimeError(f"Unknown fetch_mode {self.lab.fetch_mode!r}")

    async def _guard_robots_txt(self) -> None:
        """Disallow scraping if robots.txt forbids the People path.

        Delegates the actual /robots.txt fetch+eval to ScraplingFetcher, which
        caches disallowed URLs in self.fetcher.robots_disallows.
        """
        allowed = await self.fetcher.is_allowed_by_robots(self.lab.people_url)
        if not allowed:
            raise PermissionError(
                f"people_url {self.lab.people_url} disallowed by robots.txt"
            )

    # ===== Hooks =====

    @abstractmethod
    def parse_person_cards(self, response: Any) -> list[Any]:
        """Locate person-card elements in the fetched page."""

    @abstractmethod
    def extract_person(self, card: Any) -> RawPersonDraft:
        """Extract fields from one card into a RawPersonDraft."""

    def get_next_page_url(self, response: Any) -> str | None:
        """Pagination hook. Default: no pagination."""
        return None
