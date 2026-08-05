"""Competition import service — parse crawler JSONL and load into comp_* tables.

Consumes the JSONL contract in docs/competition-v1.0/02_数据源与爬虫Schema.md
(schema_version "1.0": meta → series → contest → team* → person*).
The admin upload endpoint is the only HTTP entry point using this service.
"""

from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.competition.models.competition import CompTalent
from app.domains.competition.repositories.competition_repository import CompetitionRepository
from app.domains.competition.schemas.competition import CompImportReport, SkipReason
from app.domains.shared.services.jsonl_import import (
    abort_if_empty,
    count_jsonl_lines,
    iter_jsonl_records,
)
from app.domains.shared.services.jsonl_import import trimmed_str as _str

logger = logging.getLogger(__name__)

SCHEMA_VERSION = "1.0"
_VALID_TYPES = {"meta", "series", "contest", "team", "person"}
_VALID_AWARDS = {"gold", "silver", "bronze", "hm", "none"}


class CompImportError(Exception):
    """Structural JSONL error — the whole file is rejected (endpoint maps to 400)."""


def _md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _parse_dt(value: Any) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


class CompImportService:
    """Parse JSONL and replace one contest's results atomically."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = CompetitionRepository(session)

    # ---------------- Parse & validate ----------------

    def _parse(
        self, jsonl_content: str
    ) -> tuple[dict, dict, dict, list[dict], list[dict], list[SkipReason]]:
        meta: dict | None = None
        series: dict | None = None
        contest: dict | None = None
        teams: list[dict] = []
        persons: list[dict] = []
        skips: list[SkipReason] = []
        stage = "meta"  # meta → series → contest → body

        for jl in iter_jsonl_records(jsonl_content):
            lineno = jl.lineno
            if jl.error is not None:
                skips.append(SkipReason(line=lineno, reason=jl.error))
                continue
            record = jl.record
            rtype = record.get("type")
            if rtype not in _VALID_TYPES:
                skips.append(SkipReason(line=lineno, reason=f"unknown type: {rtype}"))
                continue

            if rtype in ("meta", "series", "contest"):
                expected = {"meta": "series", "series": "contest", "contest": "body"}
                if rtype != stage:
                    raise CompImportError(
                        f"line {lineno}: expected type '{stage}' but got '{rtype}' "
                        "(row order must be meta → series → contest → team* → person*)"
                    )
                if rtype == "meta":
                    meta = record
                elif rtype == "series":
                    series = record
                else:
                    contest = record
                stage = expected[rtype]
                continue

            # team/person body rows
            if stage != "body":
                raise CompImportError(
                    f"line {lineno}: '{rtype}' row before meta/series/contest headers"
                )
            if rtype == "team":
                if persons:
                    raise CompImportError(
                        f"line {lineno}: team rows must precede person rows (no interleaving)"
                    )
                if not _str(record.get("name"), 255):
                    skips.append(SkipReason(line=lineno, reason="missing team name"))
                    continue
                if not isinstance(record.get("result"), dict):
                    skips.append(SkipReason(line=lineno, reason="missing team result"))
                    continue
                record["_line"] = lineno
                teams.append(record)
            else:  # person
                if not _str(record.get("handle"), 255):
                    skips.append(SkipReason(line=lineno, reason="missing handle"))
                    continue
                result = record.get("result")
                if not isinstance(result, dict) or (
                    result.get("rank") is None and not result.get("participated")
                ):
                    skips.append(SkipReason(line=lineno, reason="missing result"))
                    continue
                award = result.get("award")
                if award is not None and award not in _VALID_AWARDS:
                    skips.append(SkipReason(line=lineno, reason=f"invalid award: {award}"))
                    continue
                record["_line"] = lineno
                persons.append(record)

        if meta is None or series is None or contest is None:
            raise CompImportError("missing required meta/series/contest header rows")
        return meta, series, contest, teams, persons, skips

    def _validate_headers(self, meta: dict, series: dict, contest: dict) -> None:
        if meta.get("schema_version") != SCHEMA_VERSION:
            raise CompImportError(
                f"incompatible schema_version: {meta.get('schema_version')!r} "
                f"(expected {SCHEMA_VERSION!r})"
            )
        source_code = _str(meta.get("source_code"), 50)
        contest_external_id = _str(meta.get("contest_external_id"), 100)
        if not source_code:
            raise CompImportError("meta.source_code is required")
        if not contest_external_id:
            raise CompImportError("meta.contest_external_id is required")
        if _str(series.get("code"), 50) != source_code:
            raise CompImportError(
                f"meta.source_code ({source_code}) != series.code ({series.get('code')})"
            )
        if _str(contest.get("external_id"), 100) != contest_external_id:
            raise CompImportError(
                f"meta.contest_external_id ({contest_external_id}) != "
                f"contest.external_id ({contest.get('external_id')})"
            )
        if not _str(contest.get("name"), 500):
            raise CompImportError("contest.name is required")

    # ---------------- Import ----------------

    async def import_jsonl(self, jsonl_content: str) -> CompImportReport:
        """Import one contest JSONL file with full result replacement."""
        started = time.monotonic()
        meta, series, contest, teams, persons, skips = self._parse(jsonl_content)
        self._validate_headers(meta, series, contest)
        source_code = meta["source_code"].strip()
        external_id = meta["contest_external_id"].strip()

        report = CompImportReport(
            source_code=source_code,
            contest_external_id=external_id,
            contest_name=_str(contest.get("name"), 500) or "",
            total_lines=count_jsonl_lines(jsonl_content, skip_blank=True),
            persons_parsed=len(persons),
            teams_parsed=len(teams),
            skipped=len(skips),
            skip_reasons=skips,
        )

        def _zero_valid_report() -> CompImportReport:
            logger.warning(
                "[CompImport] %s:%s — 0 valid records, aborting without touching DB",
                source_code,
                external_id,
            )
            report.duration_ms = int((time.monotonic() - started) * 1000)
            return report

        # Hard guard (lab V3.1.0 lesson): never delete when nothing valid parsed
        aborted = abort_if_empty(persons or teams, on_abort=_zero_valid_report)
        if aborted is not None:
            return aborted

        # Batch dedup: dup handle → keep last; dup team → merge members, keep last result
        persons = list({p["handle"].strip().lower(): p for p in persons}.values())
        merged_teams: dict[tuple[str, str], dict] = {}
        members_acc: dict[tuple[str, str], list] = {}
        for row in teams:
            key = (row["name"].strip().lower(), (row.get("school") or "").strip())
            members_acc.setdefault(key, []).extend(row.get("members") or [])
            merged_teams[key] = {**merged_teams.get(key, {}), **row}
        for key, row in merged_teams.items():
            row["members"] = members_acc[key]
        teams = list(merged_teams.values())

        # Auto-create team rows for person.team_name without a matching team row
        known_team_names = {t["name"].strip().lower() for t in teams}
        for person in persons:
            team_name = _str(person.get("team_name"), 255)
            if team_name and team_name.lower() not in known_team_names:
                teams.append(
                    {
                        "type": "team",
                        "name": team_name,
                        "_auto_created": True,  # linkage only — no team result row
                        "_line": person["_line"],
                    }
                )
                known_team_names.add(team_name.lower())
                skips.append(
                    SkipReason(
                        line=person["_line"],
                        reason=f"auto-created team row for '{team_name}' (no team line in file)",
                    )
                )
        report.skipped = len(skips)
        report.skip_reasons = (
            skips  # pydantic copies the list at construction; refresh after late appends
        )

        async with self.session.begin():
            series_row = await self.repo.upsert_series(
                {
                    "code": source_code,
                    "name": _str(series.get("name"), 255) or source_code,
                    "name_en": _str(series.get("name_en"), 255),
                    "homepage": _str(series.get("homepage"), 500),
                    "description": _str(series.get("description"), 2000),
                    "logo_url": _str(series.get("logo_url"), 1000),
                }
            )
            contest_row = await self.repo.upsert_contest(
                series_row.series_id,
                {
                    "source_code": source_code,
                    "external_id": external_id,
                    "name": _str(contest.get("name"), 500) or external_id,
                    "start_time": _parse_dt(contest.get("start_time")),
                    "duration_seconds": contest.get("duration_seconds"),
                    "season": _str(contest.get("season"), 50),
                    "status": _str(contest.get("status"), 20) or "finished",
                    "source_url": _str(contest.get("source_url"), 1000),
                    "raw_meta": contest.get("raw_meta"),
                },
            )

            report.results_deleted = await self.repo.delete_results_by_contest(
                contest_row.contest_id
            )

            # Teams + team results
            team_ids: dict[str, int] = {}
            contest_url = contest_row.source_url
            for row in teams:
                name = row["name"].strip()
                team = await self.repo.upsert_team(
                    {
                        "source_code": source_code,
                        "name": name,
                        "name_lower": name.lower(),
                        "school": _str(row.get("school"), 255),
                        "country_code": _str(row.get("country_code"), 10),
                        "logo_url": _str(row.get("logo_url"), 1000),
                        "dedup_hash": _md5(
                            f"{source_code}:{name.lower()}:{(row.get('school') or '').strip()}"
                        ),
                    }
                )
                team_ids[name.lower()] = team.team_id
                report.teams_upserted += 1
                if row.get("_auto_created"):
                    continue  # linkage-only team, no team result row
                result = row["result"]
                await self.repo.insert_result(
                    {
                        "talent_id": None,
                        "team_id": team.team_id,
                        "contest_id": contest_row.contest_id,
                        "rank": result.get("rank"),
                        "score": result.get("score"),
                        "award": result.get("award"),
                        "team_name": name,
                        "team_members": row.get("members"),
                        "source_url": _str(result.get("source_url"), 1000) or contest_url,
                        "raw_meta": result.get("raw_meta"),
                    }
                )
                report.results_inserted += 1

            # Persons + personal results
            involved_talent_ids: list[int] = []
            for row in persons:
                handle = row["handle"].strip()
                talent = await self.repo.upsert_talent(
                    {
                        "source_code": source_code,
                        "handle": handle,
                        "handle_lower": handle.lower(),
                        "dedup_hash": _md5(f"{source_code}:{handle.lower()}"),
                        "real_name": _str(row.get("real_name"), 255),
                        "school": _str(row.get("school"), 255),
                        "country_code": _str(row.get("country_code"), 10),
                        "avatar_url": _str(row.get("avatar_url"), 1000),
                        "profile_url": _str(row.get("profile_url"), 1000),
                        "rank_title": _str(row.get("rank_title"), 50),
                        "specialties": row.get("specialties"),
                        "max_rating": row.get("max_rating"),
                        "current_rating": row.get("rating"),
                    }
                )
                result = row["result"]
                team_id = None
                if row.get("team_name"):
                    team_id = team_ids.get(row["team_name"].strip().lower())
                await self.repo.insert_result(
                    {
                        "talent_id": talent.talent_id,
                        "team_id": team_id,
                        "contest_id": contest_row.contest_id,
                        "rank": result.get("rank"),
                        "score": result.get("score"),
                        "rating_before": result.get("rating_before"),
                        "rating_after": result.get("rating_after"),
                        "award": result.get("award"),
                        "team_name": _str(row.get("team_name"), 255),
                        "source_url": _str(result.get("source_url"), 1000) or contest_url,
                        "raw_meta": result.get("raw_meta"),
                    }
                )
                involved_talent_ids.append(talent.talent_id)
                report.persons_upserted += 1
                report.results_inserted += 1

            # Recompute aggregates for involved talents
            file_rated = {
                t_id
                for t_id, row in zip(involved_talent_ids, persons, strict=False)
                if row.get("rating")
            }
            for talent_id in set(involved_talent_ids):
                await self._recompute_aggregates(talent_id, talent_id in file_rated)

        report.duration_ms = int((time.monotonic() - started) * 1000)
        logger.info(
            "[CompImport] %s:%s persons=%d teams=%d deleted=%d inserted=%d skipped=%d",
            source_code,
            external_id,
            report.persons_upserted,
            report.teams_upserted,
            report.results_deleted,
            report.results_inserted,
            report.skipped,
        )
        return report

    async def _recompute_aggregates(self, talent_id: int, file_rated: bool) -> None:
        """Recompute one talent's aggregates after import (§03 doc 2.5)."""
        talent = await self.session.get(CompTalent, talent_id)
        if talent is None:
            return
        talent.contests_count = await self.repo.count_results(talent_id)
        talent.medals_gold = await self.repo.count_awards(talent_id, "gold")
        talent.medals_silver = await self.repo.count_awards(talent_id, "silver")
        talent.medals_bronze = await self.repo.count_awards(talent_id, "bronze")
        latest = await self.repo.latest_talent_result(talent_id)
        if not file_rated and latest and latest.rating_after:
            talent.current_rating = latest.rating_after
        max_after = await self.repo.max_rating_after(talent_id)
        if max_after:
            talent.max_rating = max(talent.max_rating or 0, max_after)
        last_at = await self.repo.latest_contest_time(talent_id)
        if last_at:
            talent.last_contest_at = last_at
