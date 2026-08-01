"""Industry import service — parse skill JSONL and incrementally upsert.

Consumes the JSONL contract (schema v1.0) defined in
docs/v5.0.0/02-技术设计.md §5. Incremental upsert with three boundary rules:
1. Empty fields never overwrite existing values.
2. Talents/links absent from a batch are left untouched (no full replace).
3. An existing talent appearing under a new position only gains a new link;
   its scores and recruiting state on other positions are unaffected.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import unicodedata
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.industry.models.industry import IndustryTalent
from app.domains.industry.repositories.industry_repository import IndustryRepository
from app.domains.industry.schemas.industry import IndustryImportReport, SkipReason

logger = logging.getLogger(__name__)

_YEARS_NUM_RE = re.compile(r"\d+(?:\.\d+)?")

# Talent profile fields filled from a JSONL row (max length per column)
_STR_FIELDS: dict[str, int] = {
    "current_org": 255,
    "current_title": 255,
    "degree": 50,
    "years_of_exp": 20,
    "expect": 500,
    "location": 255,
    "profile_url": 1000,
    "photo_url": 1000,
    "source": 50,
}


def normalize_text(value: Any) -> str:
    """Normalize a dedup component: strip, full-width→half-width, collapse blanks."""
    if not value or not isinstance(value, str):
        return ""
    text = unicodedata.normalize("NFKC", value)
    return re.sub(r"\s+", " ", text).strip()


def compute_dedup_hash(name: Any, current_org: Any, current_title: Any) -> str:
    """sha256(normalize(name) + '|' + normalize(org) + '|' + normalize(title))."""
    key = "|".join(
        [normalize_text(name), normalize_text(current_org), normalize_text(current_title)]
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def parse_years_of_exp(value: Any) -> float | None:
    """Extract a numeric years-of-experience from raw text like '10年' or '8-10年'."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None
    match = _YEARS_NUM_RE.search(value)
    return float(match.group()) if match else None


def _str(value: Any, max_len: int) -> str | None:
    """Trimmed string truncated to max_len, or None when absent/blank."""
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()[:max_len]


def _float(value: Any) -> float | None:
    """Coerce to float, or None when absent/invalid."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


class IndustryImportService:
    """Parse JSONL and incrementally upsert industry talents and links."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = IndustryRepository(session)

    async def import_jsonl(
        self,
        jsonl_content: str,
        position_id: int | None = None,
        batch: str | None = None,
    ) -> IndustryImportReport:
        """Import a JSONL string. Per-row failures are skipped, never fatal.

        ``position_id`` is the default target position; a row-level
        ``position_id`` field overrides it (contract schema v1.0).
        """
        lines = jsonl_content.splitlines()
        total_lines = len(lines)

        known_positions = await self.repo.list_position_ids()
        report = IndustryImportReport(total_lines=total_lines, total_parsed=0)

        parsed: list[dict[str, Any]] = []
        skips: list[SkipReason] = []

        for lineno, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                skips.append(SkipReason(line=lineno, reason="invalid JSON"))
                continue
            if not isinstance(record, dict):
                skips.append(SkipReason(line=lineno, reason="not a JSON object"))
                continue

            if not _str(record.get("name"), 255):
                skips.append(SkipReason(line=lineno, reason="missing name"))
                continue

            row_position_id = record.get("position_id", position_id)
            if not isinstance(row_position_id, int) or isinstance(row_position_id, bool):
                skips.append(SkipReason(line=lineno, reason="missing position_id"))
                continue
            if row_position_id not in known_positions:
                skips.append(
                    SkipReason(line=lineno, reason=f"unknown position_id: {row_position_id}")
                )
                continue

            if not normalize_text(record.get("current_org")):
                report.warnings += 1
                logger.warning(
                    "[IndustryImport] line %d: %s has no current_org — "
                    "dedup hash discrimination is weak, manual review advised",
                    lineno,
                    record.get("name"),
                )

            record["_position_id"] = row_position_id
            parsed.append(record)

        # Deduplicate within the batch on (position_id, dedup_hash), keep last
        merged: dict[tuple[int, str], dict[str, Any]] = {}
        for row in parsed:
            dedup_hash = compute_dedup_hash(
                row.get("name"), row.get("current_org"), row.get("current_title")
            )
            row["_dedup_hash"] = dedup_hash
            merged[(row["_position_id"], dedup_hash)] = row

        report.total_parsed = len(merged)
        report.skipped = len(skips)
        report.skip_reasons = skips[:50]  # cap to avoid huge payloads

        for row in merged.values():
            talent, created = await self._upsert_talent(row)
            if created:
                report.talents_inserted += 1
            else:
                report.talents_updated += 1

            link_created = await self._upsert_link(talent, row, batch)
            if link_created:
                report.links_inserted += 1
            else:
                report.links_updated += 1

        await self.session.commit()

        logger.info(
            "[IndustryImport] lines=%d parsed=%d talents(+%d/~%d) links(+%d/~%d) "
            "skipped=%d warnings=%d",
            total_lines,
            report.total_parsed,
            report.talents_inserted,
            report.talents_updated,
            report.links_inserted,
            report.links_updated,
            report.skipped,
            report.warnings,
        )
        return report

    async def _upsert_talent(self, row: dict[str, Any]) -> tuple[IndustryTalent, bool]:
        """Upsert one talent by dedup_hash. Returns (talent, created).

        Rule 1: fields absent/empty in the new row never overwrite existing
        values (maimai and LinkedIn rows have different richness).
        """
        talent = await self.repo.get_talent_by_hash(row["_dedup_hash"])

        values: dict[str, Any] = {
            "name": _str(row.get("name"), 255),
        }
        for field, max_len in _STR_FIELDS.items():
            values[field] = _str(row.get(field), max_len)
        experiences = row.get("experiences")
        values["experiences"] = experiences if isinstance(experiences, list) else None
        years_num = parse_years_of_exp(row.get("years_of_exp"))
        values["years_of_exp_num"] = years_num

        if talent is None:
            data = {k: v for k, v in values.items() if v is not None}
            data["dedup_hash"] = row["_dedup_hash"]
            data["is_visible"] = True
            return await self.repo.insert_talent(data), True

        for field, value in values.items():
            # Empty (None / blank / empty list) never overwrites
            if value is None or value == []:
                continue
            setattr(talent, field, value)
        await self.session.flush()
        return talent, False

    async def _upsert_link(
        self, talent: IndustryTalent, row: dict[str, Any], default_batch: str | None
    ) -> bool:
        """Upsert one (position_id, talent_id) link. Returns True if created.

        Updates match scores/tags/reason/batch (non-empty only); touched,
        status and notes are preserved on existing links — only newly
        created links get defaults.
        """
        position_id = row["_position_id"]
        # SQLAlchemy Column[int] at runtime is a plain int after flush
        talent_id: int = talent.talent_id  # type: ignore[assignment]
        link = await self.repo.get_link(talent_id, position_id)

        tags = row.get("match_tags")
        values: dict[str, Any] = {
            "match_score": _float(row.get("match_score")),
            "score_school": _float(row.get("score_school")),
            "score_company": _float(row.get("score_company")),
            "score_direction": _float(row.get("score_direction")),
            "match_tags": tags if isinstance(tags, list) and tags else None,
            "match_reason": _str(row.get("match_reason"), 10000),
            "batch": _str(row.get("batch"), 50) or _str(default_batch, 50),
            "source_platform": _str(row.get("source"), 50),
        }

        if link is None:
            data = {k: v for k, v in values.items() if v is not None}
            data["position_id"] = position_id
            data["talent_id"] = talent_id
            data["touched"] = False
            data["status"] = "new"
            await self.repo.insert_link(data)
            return True

        for field, value in values.items():
            if value is None:
                continue
            setattr(link, field, value)
        await self.session.flush()
        return False
