"""Sync lab_web_site raw persons into core_talent (source_type=lab_web_site).

Upserts by source_record_id (= content_hash) scoped to source_type='lab_web_site'.
Never touches v1 (lab_web) or openalex records. Role from the site's role_section.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domains.academic.models.talent import Talent
from app.domains.lab_web.constants.normalizers import normalize_name
from app.domains.lab_web.constants.site_role_mapping import map_site_role
from app.domains.lab_web.models.lab_web import LWRawPerson
from app.domains.shared.models.enums import SourceType, VisibilityStatus

logger = logging.getLogger(__name__)


@dataclass
class SiteSyncResult:
    """Outcome of one site sync run."""

    synced: int = 0
    created: int = 0
    updated: int = 0


class LWSitePersonService:
    """Sync lab_web_site raw persons into core_talent."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def sync_to_core_talent(self, raw_persons: list[LWRawPerson]) -> SiteSyncResult:
        result = SiteSyncResult()
        commit_batch = int(getattr(settings, "SYNC_COMMIT_BATCH_SIZE", 100))
        for i, raw in enumerate(raw_persons):
            raw_data = raw.raw_data or {}
            role_section = raw_data.get("role_section", "Unknown")
            role_type, confidence = map_site_role(role_section)
            name = normalize_name(raw.name_raw) or raw.name_raw  # type: ignore[arg-type]
            homepage = raw_data.get("homepage")
            department = raw_data.get("department")
            site_code = raw_data.get("site_code", "")
            existing = await self._find_existing(str(raw.content_hash))
            extra = {
                "site_code": site_code,
                "role_section_raw": role_section,
                "department": department,
                "homepage": homepage,
                "source_url": raw.source_url,
            }
            if existing is None:
                self.session.add(
                    Talent(
                        name=name,  # type: ignore[arg-type]
                        source_type=SourceType.LAB_WEB_SITE.value,
                        source_record_id=str(raw.content_hash),
                        role_type=role_type.value,  # type: ignore[assignment]
                        role_confidence=confidence,  # type: ignore[assignment]
                        current_title=role_section,  # site role section as a displayable title
                        lab_name=site_code,  # type: ignore[assignment]
                        visibility_status=VisibilityStatus.ACTIVE.value,  # type: ignore[assignment]
                        is_visible=True,  # type: ignore[assignment]
                        extra_data=extra,  # type: ignore[assignment]
                    )
                )
                result.created += 1
            else:
                existing.name = name  # type: ignore[assignment]
                existing.role_type = role_type.value  # type: ignore[assignment]
                existing.role_confidence = confidence  # type: ignore[assignment]
                existing.current_title = role_section  # type: ignore[assignment]
                existing.lab_name = site_code  # type: ignore[assignment]
                existing.is_visible = True  # type: ignore[assignment]
                existing.extra_data = extra  # type: ignore[assignment]
                result.updated += 1
            result.synced += 1
            if (i + 1) % commit_batch == 0:
                await self.session.commit()
        await self.session.commit()
        return result

    async def _find_existing(self, content_hash: str) -> Talent | None:
        stmt = select(Talent).where(
            Talent.source_type == SourceType.LAB_WEB_SITE.value,
            Talent.source_record_id == content_hash,
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()
