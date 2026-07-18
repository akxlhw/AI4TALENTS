"""Lab import service — parse crawler JSONL and load into lab_talent.

Consumes the JSONL output format defined by ai-lab-talent-crawler's
references/output-schema.md. The admin upload endpoint is the only HTTP
entry point that uses this service.
"""

from __future__ import annotations

import hashlib
import html
import json
import logging
import re
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.lab.constants.role_mapping import map_role
from app.domains.lab.repositories.lab_talent_repository import LabTalentRepository
from app.domains.lab.schemas.lab_talent import LabImportReport, SkipReason

logger = logging.getLogger(__name__)

# Patterns for cleaning research_areas extracted from lab websites
_HTML_ENTITY_RE = re.compile(r"&[a-zA-Z]+;|&#\d+;")
# Person name pattern: only match hyphenated names (e.g. "Jun-Peng Jiang")
# or 3+ word names. Two-word "Machine Learning" must NOT match.
_PERSON_NAME_RE = re.compile(r"^[A-Z][a-z]+-[A-Z][a-z]+\s[A-Z][a-z]+")
_MULTILINE_SENTENCE_RE = re.compile(r"[.!?]\s+[A-Z]")  # sentence boundary inside one item
# Fragments that are clearly not research areas
_NOISE_FRAGMENTS = {
    "more specifically",
    "i am interested in",
    "text",
    "&nbsp",
}


def _clean_research_area(raw: str) -> str | None:
    """Clean a single research_areas item extracted from a lab website.

    Returns None if the item is not a valid research area (HTML entity,
    sentence fragment, person name, or too short).
    """
    if not raw or not isinstance(raw, str):
        return None
    # Decode HTML entities and strip residual tags
    cleaned = html.unescape(raw).strip()
    cleaned = _HTML_ENTITY_RE.sub("", cleaned).strip()
    cleaned = cleaned.replace("&nbsp", "").strip()
    # Remove leading punctuation/colons
    cleaned = cleaned.lstrip(":.,;- ").strip()
    if not cleaned:
        return None
    # Skip if it's a known noise fragment
    lower = cleaned.lower()
    if lower in _NOISE_FRAGMENTS:
        return None
    if any(lower.startswith(nf) for nf in _NOISE_FRAGMENTS):
        return None
    # Skip person names (e.g. "Jun-Peng Jiang", "Si-Yang Liu")
    if _PERSON_NAME_RE.match(cleaned):
        return None
    # Skip if it's a full sentence (contains sentence boundary or > 80 chars)
    if len(cleaned) > 80:
        return None
    if _MULTILINE_SENTENCE_RE.search(cleaned):
        return None
    return cleaned


def _clean_research_areas(raw_areas: list[Any] | None) -> list[str]:
    """Clean and deduplicate a list of research_areas items."""
    if not raw_areas:
        return []
    result: list[str] = []
    seen: set[str] = set()
    for item in raw_areas:
        cleaned = _clean_research_area(str(item) if item else "")
        if cleaned and cleaned.lower() not in seen:
            seen.add(cleaned.lower())
            result.append(cleaned)
    return result


def _clean_social_links(raw_links: Any) -> dict[str, str]:
    """Normalize social_links to a {platform: url} dict.

    Keeps only entries with non-empty string platform keys and http(s) URLs.
    Platform keys are lowercased for consistent frontend icon mapping.
    """
    if not isinstance(raw_links, dict):
        return {}
    result: dict[str, str] = {}
    for key, url in raw_links.items():
        if not isinstance(key, str) or not isinstance(url, str):
            continue
        platform = key.strip().lower()
        link = url.strip()
        if platform and link.startswith(("http://", "https://")):
            result[platform] = link
    return result


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

        Supports the v2 JSONL format where the first line is a ``type: lab``
        metadata record and subsequent lines are ``type: person`` talent records.
        """
        lines = jsonl_content.splitlines()
        total_lines = len(lines)

        parsed: list[dict[str, Any]] = []
        skip_reasons: list[SkipReason] = []
        resolved_parent_lab = parent_lab
        lab_logo_url: str | None = None
        lab_metadata: dict[str, Any] | None = None

        for idx, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()
            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                skip_reasons.append(SkipReason(line=idx, reason="invalid JSON"))
                continue

            record_type = (record.get("type") or "person").lower()

            if record_type == "lab":
                # Metadata header: derive parent_lab and lab logo if available.
                if not resolved_parent_lab:
                    resolved_parent_lab = record.get("lab_name") or record.get("name") or ""
                if record.get("logo_url"):
                    lab_logo_url = record.get("logo_url")
                # Capture lab metadata for lab_info upsert (done after the loop)
                lab_metadata = record
                continue

            if record_type != "person":
                skip_reasons.append(SkipReason(line=idx, reason=f"unknown type: {record_type}"))
                continue

            if not record.get("name"):
                skip_reasons.append(SkipReason(line=idx, reason="missing name"))
                continue
            if not resolved_parent_lab and not record.get("parent_lab"):
                skip_reasons.append(SkipReason(line=idx, reason="missing parent_lab"))
                continue

            mapped = self._map_record(record, resolved_parent_lab, lab_logo_url)
            if mapped is not None:
                parsed.append(mapped)

        if not resolved_parent_lab:
            resolved_parent_lab = "unknown"

        # Deduplicate within the incoming batch so duplicate JSONL lines do not
        # violate the unique constraint. Keep the last occurrence.
        seen: dict[str, dict[str, Any]] = {}
        for row in parsed:
            seen[row["dedup_hash"]] = row
        deduped = list(seen.values())

        # Safety guard: refuse to delete existing data if the import produced
        # zero valid records (all lines were empty/invalid). This prevents
        # a malformed JSONL from wiping out an entire lab's data.
        if not deduped:
            logger.warning(
                "[LabImport] Refusing to replace %s: 0 valid records parsed from %d lines",
                resolved_parent_lab,
                total_lines,
            )
            return LabImportReport(
                parent_lab=resolved_parent_lab,
                total_lines=total_lines,
                total_parsed=0,
                inserted=0,
                skipped=len(skip_reasons),
                skip_reasons=skip_reasons[:50],
            )

        # Atomic replace: delete + insert in one transaction
        deleted = await self.repo.delete_by_parent_lab(resolved_parent_lab)
        await self.session.flush()
        inserted = await self.repo.bulk_insert(deduped)

        # Upsert lab-level metadata (from the type:lab header line)
        if lab_metadata and resolved_parent_lab:
            await self._upsert_lab_info(lab_metadata, resolved_parent_lab)

        await self.session.commit()

        logger.info(
            "[LabImport] parent_lab=%s lines=%d parsed=%d deduped=%d deleted=%d inserted=%d skipped=%d",
            resolved_parent_lab,
            total_lines,
            len(parsed),
            len(deduped),
            deleted,
            inserted,
            len(skip_reasons),
        )

        return LabImportReport(
            parent_lab=resolved_parent_lab,
            total_lines=total_lines,
            total_parsed=len(deduped),
            inserted=inserted,
            skipped=len(skip_reasons),
            skip_reasons=skip_reasons[:50],  # cap reasons to avoid huge payloads
        )

    async def _upsert_lab_info(self, lab_record: dict[str, Any], parent_lab: str) -> None:
        """Upsert lab-level metadata into lab_info table."""
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        from app.domains.lab.models.lab_talent import LabInfo

        values = {
            "parent_lab": parent_lab,
            "lab_slug": lab_record.get("lab_slug"),
            "description": lab_record.get("description"),
            "research_focus": lab_record.get("research_focus"),
            "research_directions": lab_record.get("current_research_directions") or [],
            "homepage": lab_record.get("homepage"),
            "logo_url": lab_record.get("logo_url"),
        }
        stmt = pg_insert(LabInfo).values(values)
        await self.session.execute(
            stmt.on_conflict_do_update(
                index_elements=["parent_lab"],
                set_={
                    "lab_slug": stmt.excluded.lab_slug,
                    "description": stmt.excluded.description,
                    "research_focus": stmt.excluded.research_focus,
                    "research_directions": stmt.excluded.research_directions,
                    "homepage": stmt.excluded.homepage,
                    "logo_url": stmt.excluded.logo_url,
                },
            )
        )

    @staticmethod
    def _map_record(
        record: dict[str, Any], fallback_parent_lab: str, lab_logo_url: str | None = None
    ) -> dict[str, Any] | None:
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
            "social_links": _clean_social_links(record.get("social_links")),
            "photo_url": record.get("photo_url"),
            "department": record.get("department"),
            "research_areas": _clean_research_areas(record.get("research_areas")),
            "cohort_year": record.get("cohort_year"),
            "cohort_source": record.get("cohort_source"),
            "lab_name": lab_name,
            "parent_lab": parent_lab,
            "lab_logo_url": record.get("lab_logo_url") or lab_logo_url,
            "source_url": record.get("source_url"),
            "source_detail_url": record.get("source_detail_url"),
            "collected_at": collected_at,
            "dedup_hash": dedup_hash,
            "is_visible": True,
        }
