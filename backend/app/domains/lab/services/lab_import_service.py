"""Lab import service — parse crawler JSONL and load into lab_talent.

Consumes the JSONL output format defined by ai-lab-talent-crawler's
references/output-schema.md. Two HTTP entry points (hermes push + admin
upload) share this single service.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.lab.constants.role_mapping import map_role
from app.domains.lab.repositories.lab_talent_repository import LabTalentRepository
from app.domains.lab.schemas.lab_talent import LabImportReport, SkipReason

logger = logging.getLogger(__name__)


class LabImportService:
    """Parse JSONL and replace a parent lab's talent data atomically."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = LabTalentRepository(session)

    async def import_jsonl(self, jsonl_content: str, parent_lab: str) -> LabImportReport:
        """Import a JSONL string, fully replacing the given parent_lab's data.

        Strategy: per-lab full replace (DELETE existing parent_lab rows, then
        INSERT parsed rows) within a single transaction — atomic, no partial
        state on failure.
        """
        lines = jsonl_content.splitlines()
        total_lines = len(lines)

        parsed: list[dict[str, Any]] = []
        skip_reasons: list[SkipReason] = []

        for idx, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()
            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                skip_reasons.append(SkipReason(line=idx, reason="invalid JSON"))
                continue

            if not record.get("name"):
                skip_reasons.append(SkipReason(line=idx, reason="missing name"))
                continue
            if not record.get("parent_lab"):
                skip_reasons.append(SkipReason(line=idx, reason="missing parent_lab"))
                continue

            mapped = self._map_record(record, parent_lab)
            if mapped is not None:
                parsed.append(mapped)

        # Atomic replace: delete + insert in one transaction
        # (the surrounding API endpoint does NOT auto-commit; we commit here)
        deleted = await self.repo.delete_by_parent_lab(parent_lab)
        inserted = await self.repo.bulk_insert(parsed)
        await self.session.commit()

        logger.info(
            "[LabImport] parent_lab=%s lines=%d parsed=%d deleted=%d inserted=%d skipped=%d",
            parent_lab,
            total_lines,
            len(parsed),
            deleted,
            inserted,
            len(skip_reasons),
        )

        return LabImportReport(
            parent_lab=parent_lab,
            total_lines=total_lines,
            total_parsed=len(parsed),
            inserted=inserted,
            skipped=len(skip_reasons),
            skip_reasons=skip_reasons[:50],  # cap reasons to avoid huge payloads
        )

    @staticmethod
    def _map_record(record: dict[str, Any], fallback_parent_lab: str) -> dict[str, Any] | None:
        """Map a JSONL record to a lab_talent row dict.

        Field mapping per docs/lab-talent-v1.0-design.md §3.1.
        Returns None if the record cannot be mapped.
        """
        name = (record.get("name") or "").strip()
        if not name:
            return None

        role_section = record.get("role_section") or "Unknown"
        role_type, academic_level = map_role(role_section)

        lab_name = record.get("lab_name") or fallback_parent_lab
        parent_lab = record.get("parent_lab") or fallback_parent_lab

        # Dedup key
        dedup_hash = hashlib.sha256(f"{name}|{lab_name}|{role_section}".encode()).hexdigest()

        # Parse collected_at — strip tzinfo because the DB column is
        # TIMESTAMP WITHOUT TIME ZONE; mixing aware/naive datetimes breaks asyncpg.
        collected_at = None
        raw_collected_at = record.get("collected_at")
        if raw_collected_at:
            try:
                parsed = datetime.fromisoformat(raw_collected_at.replace("Z", "+00:00"))
                collected_at = parsed.replace(tzinfo=None)
            except (ValueError, AttributeError):
                pass

        return {
            "name": name,
            "role_section": role_section,
            "role_type": role_type,
            "academic_level": academic_level,
            "current_title": record.get("role_raw"),
            "homepage": record.get("homepage"),
            "email": record.get("email"),
            "photo_url": record.get("photo_url"),
            "department": record.get("department"),
            "research_areas": record.get("research_areas") or [],
            "cohort_year": record.get("cohort_year"),
            "cohort_source": record.get("cohort_source"),
            "lab_name": lab_name,
            "parent_lab": parent_lab,
            "source_url": record.get("source_url"),
            "source_detail_url": record.get("source_detail_url"),
            "collected_at": collected_at,
            "dedup_hash": dedup_hash,
            "is_visible": True,
        }
