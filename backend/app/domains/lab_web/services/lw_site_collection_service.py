"""Collection orchestration for lab_web_site (v2, LLM-driven)."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.domains.lab_web.models.lab_web_site import LWSiteRawPage
from app.domains.lab_web.repositories.lab_web import LWRepository
from app.domains.lab_web.repositories.lab_web.site import LWSiteRepository
from app.domains.lab_web.services.collectors.base_site_collector import (
    BaseLabSiteCollector,
    SiteCollectContext,
)
from app.domains.lab_web.services.lw_site_person_service import LWSitePersonService

logger = logging.getLogger(__name__)

SITE_COLLECTION_SEMAPHORE = asyncio.Semaphore(
    int(getattr(settings, "LAB_WEB_SITE_MAX_CONCURRENT", 2))
)


class LWSiteCollectionService:
    """Orchestrates one lab-site LLM collection run end-to-end."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = LWSiteRepository(session)
        self.task_repo = LWRepository(session)

    async def list_sites(self, only_active: bool = False) -> list:
        return await self.repo.list_sites(only_active=only_active)

    async def get_task_status(self, task_id: int) -> Any:
        return await self.task_repo.get_task(task_id)

    async def cancel_collection(self, task_id: int) -> bool:
        await self.task_repo.update_task(task_id, status="cancelled")
        return True

    async def get_review_items(self, site_code: str) -> list[LWSiteRawPage]:
        stmt = (
            select(LWSiteRawPage)
            .where(
                LWSiteRawPage.site_code == site_code,
                LWSiteRawPage.parse_status == "needs_review",
            )
            .order_by(LWSiteRawPage.created_at.desc())
            .limit(20)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def start_collection(
        self,
        site_code: str,
        force_reparse: bool = False,
        created_by: int | None = None,
    ) -> int:
        """Create a task and launch background collection. Returns task_id."""
        site = await self.repo.get_site_by_code(site_code)
        if site is None:
            raise LookupError(f"Site {site_code} not found")
        if not site.is_active:
            raise RuntimeError(f"Site {site_code} is not active")

        lab_id = await self.repo.resolve_lab_id(str(site.parent_lab_code))
        task = await self.task_repo.create_task(
            task_name=f"lab_web_site_collect_{site_code}",
            lab_id=lab_id,
            status="pending",
            config_json={
                "source": "lab_web_site",
                "site_code": site_code,
                "force_reparse": force_reparse,
            },
            created_by=created_by,
        )
        asyncio.create_task(self._run_collection(int(task.task_id), site_code, force_reparse))
        return int(task.task_id)

    async def _run_collection(self, task_id: int, site_code: str, force_reparse: bool) -> None:
        async with SITE_COLLECTION_SEMAPHORE:
            async with AsyncSessionLocal() as session:
                site_repo = LWSiteRepository(session)
                person_service = LWSitePersonService(session)
                task_repo = LWRepository(session)
                try:
                    site = await site_repo.get_site_by_code(site_code)
                    if site is None:
                        raise LookupError(f"Site {site_code} not found during run")
                    await task_repo.update_task(
                        task_id,
                        status="running",
                        started_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    )
                    collector = self._make_collector(site, site_repo, person_service)
                    ctx = SiteCollectContext(
                        task_id=task_id, site_code=site_code, force_reparse=force_reparse
                    )
                    await collector.collect(ctx)
                    # Determine final status from the latest raw page.
                    final_status = await self._latest_page_status(session, site_code)
                    await task_repo.update_task(
                        task_id,
                        status=final_status,
                        progress_percent=100,
                        completed_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    )
                    await site_repo.update_site_collected_at(
                        site_code,
                        datetime.now(timezone.utc).replace(tzinfo=None),
                    )
                except Exception as exc:
                    logger.exception("lab_web_site collection failed: task=%s", task_id)
                    msg = str(exc)
                    max_len = int(getattr(settings, "COLLECT_ERROR_MAX_LENGTH", 500))
                    # M3 fix: if a needs_review page was already written before the
                    # exception, prefer 'partial' over 'failed' so partial results
                    # aren't hidden. Only mark 'failed' when no page was produced.
                    status = await self._latest_page_status(session, site_code)
                    if status == "success":
                        status = "failed"
                    await task_repo.update_task(
                        task_id,
                        status=status,
                        error_message=(msg[:max_len] if len(msg) > max_len else msg),
                        completed_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    )

    @staticmethod
    async def _latest_page_status(session: AsyncSession, site_code: str) -> str:
        """Return 'success' (or 'partial' if the latest page is needs_review)."""
        latest = (
            await session.execute(
                select(LWSiteRawPage)
                .where(LWSiteRawPage.site_code == site_code)
                .order_by(LWSiteRawPage.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if latest is not None and latest.parse_status == "needs_review":
            return "partial"
        return "success"

    @staticmethod
    def _make_collector(site: Any, site_repo: Any, person_service: Any) -> BaseLabSiteCollector:
        from app.domains.lab_web.services.collectors.scrapling_fetcher import ScraplingFetcher
        from app.domains.shared.services.llm.llm_gateway import create_llm_gateway

        fetcher = ScraplingFetcher(fetch_mode=str(getattr(site, "fetch_mode", "static")))
        llm_gateway = create_llm_gateway()
        return BaseLabSiteCollector(
            fetcher=fetcher,
            site=site,
            repo=site_repo,
            person_service=person_service,
            llm_gateway=llm_gateway,
        )
