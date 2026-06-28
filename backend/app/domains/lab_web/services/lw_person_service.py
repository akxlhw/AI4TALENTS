"""Sync lw_raw_person snapshots into the shared core_talent serving layer.

Strategy: upsert by source_record_id (= content_hash) scoped to
source_type='lab_web'. openalex-sourced talents are never touched.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domains.academic.models.talent import Talent
from app.domains.lab_web.constants.normalizers import normalize_email, normalize_name
from app.domains.lab_web.constants.role_mapping import map_role_type
from app.domains.lab_web.models.lab_web import LWRawPerson
from app.domains.shared.models.enums import SourceType, VisibilityStatus

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Outcome of one sync run."""

    synced: int = 0
    created: int = 0
    updated: int = 0


class LWPersonService:
    """Sync raw lab persons into core_talent (source_type=lab_web)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def sync_to_core_talent(self, raw_persons: list[LWRawPerson], lab) -> SyncResult:
        """Upsert raw snapshots into core_talent, scoped to lab_web source."""
        result = SyncResult()
        commit_batch = getattr(settings, "SYNC_COMMIT_BATCH_SIZE", 100)

        for i, raw in enumerate(raw_persons):
            role_type, confidence = map_role_type(raw.title_raw)
            name = normalize_name(raw.name_raw) or raw.name_raw
            email = normalize_email(raw.email_raw)

            existing = await self._find_existing(raw.content_hash)
            if existing is None:
                talent = Talent(
                    name=name,
                    source_type=SourceType.LAB_WEB.value,
                    source_record_id=raw.content_hash,
                    role_type=role_type.value,
                    role_confidence=confidence,
                    current_title=raw.title_raw,
                    lab_name=lab.lab_name,
                    department_name=lab.institution,
                    visibility_status=VisibilityStatus.ACTIVE.value,
                    is_visible=True,
                    extra_data={
                        "homepage_url": raw.homepage_url,
                        "avatar_url": raw.avatar_url,
                        "email": email,
                        "source_url": raw.source_url,
                        "title_raw": raw.title_raw,
                    },
                )
                self.session.add(talent)
                result.created += 1
            else:
                existing.name = name
                existing.role_type = role_type.value
                existing.role_confidence = confidence
                existing.current_title = raw.title_raw
                existing.lab_name = lab.lab_name
                existing.department_name = lab.institution
                existing.is_visible = True
                existing.extra_data = {
                    "homepage_url": raw.homepage_url,
                    "avatar_url": raw.avatar_url,
                    "email": email,
                    "source_url": raw.source_url,
                    "title_raw": raw.title_raw,
                }
                result.updated += 1
            result.synced += 1

            if (i + 1) % commit_batch == 0:
                await self.session.commit()

        await self.session.commit()
        return result

    async def _find_existing(self, content_hash: str) -> Talent | None:
        """Find a lab_web talent by source_record_id; never matches openalex rows."""
        stmt = select(Talent).where(
            Talent.source_type == SourceType.LAB_WEB.value,
            Talent.source_record_id == content_hash,
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()
