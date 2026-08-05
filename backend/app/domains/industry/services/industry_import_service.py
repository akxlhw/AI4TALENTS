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
import logging
import re
import unicodedata
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.industry.models.industry import IndustryTalent
from app.domains.industry.repositories.industry_repository import IndustryRepository
from app.domains.industry.schemas.industry import IndustryImportReport, SkipReason
from app.domains.shared.services.jsonl_import import (
    abort_if_empty,
    cap_skip_reasons,
    count_jsonl_lines,
    iter_jsonl_records,
    run_row_isolated,
)
from app.domains.shared.services.jsonl_import import trimmed_str as _str

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

        Guards (aligned with lab/competition import services):
        - Hard guard: an empty file or one with 0 valid rows writes nothing
          and returns ``aborted=True`` — never a silent success.
        - Row-level isolation: each row upserts under a SAVEPOINT, so a
          single row's DB error rolls back alone and lands in skip_reasons.
        - Atomicity: all surviving rows commit in one outer transaction.
        """
        total_lines = count_jsonl_lines(jsonl_content)

        known_positions = await self.repo.list_position_ids()
        report = IndustryImportReport(total_lines=total_lines, total_parsed=0)

        parsed: list[dict[str, Any]] = []
        skips: list[SkipReason] = []

        for jl in iter_jsonl_records(jsonl_content):
            lineno = jl.lineno
            if jl.error is not None:
                skips.append(SkipReason(line=lineno, reason=jl.error))
                continue
            record = jl.record
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
            record["_line"] = lineno
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

        # Hard guard (lab/competition standard): an empty or fully-invalid
        # file writes nothing and is explicitly flagged, not a silent success.
        def _zero_valid_report() -> IndustryImportReport:
            logger.warning(
                "[IndustryImport] Aborting: 0 valid rows parsed from %d lines, "
                "skipped=%d — no data written",
                total_lines,
                len(skips),
            )
            report.aborted = True
            report.skipped = len(skips)
            report.skip_reasons = cap_skip_reasons(skips)
            return report

        aborted = abort_if_empty(merged, on_abort=_zero_valid_report)
        if aborted is not None:
            return aborted

        # Upsert loop: per-row SAVEPOINT isolation inside one outer
        # transaction. A single row's DB error (constraint violation,
        # unserializable JSON, ...) rolls that row back alone and lands in
        # skip_reasons; all surviving rows commit together below.
        for row in merged.values():
            row_line: int = row.get("_line", 0)

            async def work(row: dict[str, Any] = row) -> tuple[bool, bool]:
                return await self._upsert_row(row, batch)

            def on_error(e: Exception, line: int = row_line) -> None:
                logger.warning("[IndustryImport] line %d DB error, row skipped: %s", line, e)

            outcome = await run_row_isolated(self.session, work, on_error=on_error)
            if outcome.error is not None:
                skips.append(SkipReason(line=row_line, reason=outcome.error))
                continue
            assert outcome.value is not None  # error is None → upsert succeeded
            created, link_created = outcome.value
            if created:
                report.talents_inserted += 1
            else:
                report.talents_updated += 1
            if link_created:
                report.links_inserted += 1
            else:
                report.links_updated += 1

        report.skipped = len(skips)
        report.skip_reasons = cap_skip_reasons(skips)  # cap to avoid huge payloads

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

    async def _upsert_row(self, row: dict[str, Any], batch: str | None) -> tuple[bool, bool]:
        """Upsert one talent plus its position link. Returns (talent_created, link_created).

        Runs as a single unit of work inside the row-level SAVEPOINT opened by
        the import loop, so a failure anywhere in the pair rolls the row back.
        """
        talent, created = await self._upsert_talent(row)
        link_created = await self._upsert_link(talent, row, batch)
        return created, link_created

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
