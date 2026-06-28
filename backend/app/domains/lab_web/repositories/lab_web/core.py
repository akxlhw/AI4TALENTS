"""Data access layer for lab_web tables."""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.lab_web.constants.normalizers import (
    compute_content_hash,
    normalize_email,
    normalize_name,
)
from app.domains.lab_web.models.lab_web import (
    LWCollectTask,
    LWLabRegistry,
    LWRawPerson,
)
from app.domains.lab_web.services.collectors.base_collector import RawPersonDraft

logger = logging.getLogger(__name__)


class LWRepository:
    """Read/write access to lw_lab_registry, lw_raw_person, lw_collect_task."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ===== Labs =====

    async def get_lab(self, lab_id: int) -> LWLabRegistry | None:
        return await self.session.get(LWLabRegistry, lab_id)

    async def get_lab_by_code(self, lab_code: str) -> LWLabRegistry | None:
        stmt = select(LWLabRegistry).where(LWLabRegistry.lab_code == lab_code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_labs(self, only_active: bool = False) -> list[LWLabRegistry]:
        stmt = select(LWLabRegistry)
        if only_active:
            stmt = stmt.where(LWLabRegistry.is_active.is_(True))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_lab_collected_at(
        self, lab_id: int, collected_at: Any
    ) -> None:
        lab = await self.session.get(LWLabRegistry, lab_id)
        if lab:
            lab.last_collected_at = collected_at

    # ===== Tasks =====

    async def create_task(self, **kwargs: Any) -> LWCollectTask:
        task = LWCollectTask(**kwargs)
        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def update_task(self, task_id: int, **kwargs: Any) -> None:
        task = await self.session.get(LWCollectTask, task_id)
        if task:
            for key, value in kwargs.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            await self.session.commit()

    async def get_task(self, task_id: int) -> LWCollectTask | None:
        return await self.session.get(LWCollectTask, task_id)

    async def list_tasks(
        self, lab_id: int | None = None, limit: int = 50
    ) -> list[LWCollectTask]:
        stmt = select(LWCollectTask)
        if lab_id is not None:
            stmt = stmt.where(LWCollectTask.lab_id == lab_id)
        stmt = stmt.order_by(LWCollectTask.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ===== Raw persons =====

    async def upsert_raw_persons(
        self,
        lab_id: int,
        drafts: list[RawPersonDraft],
        task_id: int,
        lab_code: str,
    ) -> list[LWRawPerson]:
        """Insert raw-person snapshots, deduping by content_hash within this call.

        raw layer is append-only: existing rows are never updated. Dedup happens
        within the current batch (same person appearing twice in one scrape).
        """
        seen_hashes: set[str] = set()
        created: list[LWRawPerson] = []
        for draft in drafts:
            name = normalize_name(draft.name_raw) or draft.name_raw
            email = normalize_email(draft.email_raw)
            hash_ = compute_content_hash(
                lab_code=lab_code,
                name=name,
                title=draft.title_raw,
                email=email,
                homepage=draft.homepage_url,
            )
            if hash_ in seen_hashes:
                continue
            seen_hashes.add(hash_)
            row = LWRawPerson(
                lab_id=lab_id,
                source_url=draft.source_url,
                name_raw=draft.name_raw,
                title_raw=draft.title_raw,
                email_raw=draft.email_raw,
                homepage_url=draft.homepage_url,
                avatar_url=draft.avatar_url,
                raw_data={
                    "title_raw": draft.title_raw,
                    "email_raw": draft.email_raw,
                    "homepage_url": draft.homepage_url,
                    "avatar_url": draft.avatar_url,
                    "source_url": draft.source_url,
                    **(draft.extra or {}),
                },
                collect_task_id=task_id,
                content_hash=hash_,
            )
            self.session.add(row)
            created.append(row)
        await self.session.commit()
        return created

    async def get_raw_persons_by_task(self, task_id: int) -> list[LWRawPerson]:
        stmt = select(LWRawPerson).where(LWRawPerson.collect_task_id == task_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
