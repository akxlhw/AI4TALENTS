"""Acceptance tests for CompImportService (docs/competition-v1.0/03 §4)."""

from __future__ import annotations

import json

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.competition.models.competition import (
    CompContest,
    CompResult,
    CompSeries,
    CompTalent,
    CompTeam,
)
from app.domains.competition.services.comp_import_service import (
    CompImportError,
    CompImportService,
)


def _jsonl(*records: dict) -> str:
    return "\n".join(json.dumps(r, ensure_ascii=False) for r in records)


def _meta(source: str = "codeforces", contest_id: str = "1950", version: str = "1.0") -> dict:
    return {
        "type": "meta",
        "schema_version": version,
        "source_code": source,
        "contest_external_id": contest_id,
        "crawler": "comp-talent-crawler",
        "crawler_version": "1.0.0",
        "collected_at": "2026-07-19T08:00:00Z",
    }


def _series(code: str = "codeforces") -> dict:
    return {
        "type": "series",
        "code": code,
        "name": "Codeforces",
        "homepage": "https://codeforces.com",
    }


def _contest(external_id: str = "1950", name: str = "Codeforces Round 951 (Div. 1)") -> dict:
    return {
        "type": "contest",
        "external_id": external_id,
        "name": name,
        "start_time": "2024-05-30T14:35:00Z",
        "season": "2024",
        "status": "finished",
        "source_url": "https://codeforces.com/contest/1950",
    }


def _person(handle: str, result: dict | None = None, **profile) -> dict:
    rec = {"type": "person", "handle": handle, "result": result or {"rank": 1}}
    rec.update(profile)
    return rec


def _sample_file(*persons: dict) -> str:
    return _jsonl(_meta(), _series(), _contest(), *persons)


async def _count(session: AsyncSession, model) -> int:
    return (await session.scalar(select(func.count()).select_from(model))) or 0


@pytest.mark.asyncio
async def test_valid_file_loads_all_entities_and_aggregates(test_session: AsyncSession) -> None:
    """Case 1: valid file → series/contest/talent/result all loaded with correct aggregates."""
    content = _sample_file(
        _person(
            "tourist",
            {"rank": 1, "rating_before": 3904, "rating_after": 3948, "award": "gold"},
            real_name="Gennady Korotkevich",
            school="ITMO University",
            country_code="BY",
            rating=3948,
            max_rating=3979,
            rank_title="legendary grandmaster",
        ),
        _person(
            "jiangly", {"rank": 3, "rating_before": 3711, "rating_after": 3756, "award": "bronze"}
        ),
    )
    report = await CompImportService(test_session).import_jsonl(content)

    assert report.persons_upserted == 2
    assert report.results_inserted == 2
    assert report.results_deleted == 0
    assert await _count(test_session, CompSeries) == 1
    assert await _count(test_session, CompContest) == 1
    assert await _count(test_session, CompTalent) == 2
    assert await _count(test_session, CompResult) == 2

    tourist = await test_session.scalar(
        select(CompTalent).where(CompTalent.handle_lower == "tourist")
    )
    assert tourist is not None
    assert tourist.current_rating == 3948  # from file rating
    assert tourist.max_rating == 3979
    assert tourist.contests_count == 1
    assert tourist.medals_gold == 1
    assert tourist.school == "ITMO University"
    assert tourist.last_contest_at is not None

    jiangly = await test_session.scalar(
        select(CompTalent).where(CompTalent.handle_lower == "jiangly")
    )
    assert jiangly is not None
    assert jiangly.current_rating == 3756  # from latest rating_after
    assert jiangly.medals_bronze == 1


@pytest.mark.asyncio
async def test_reimport_same_file_is_idempotent(test_session: AsyncSession) -> None:
    """Case 2: importing the same file twice yields identical state."""
    content = _sample_file(_person("tourist", {"rank": 1, "rating_after": 3948}))
    service = CompImportService(test_session)
    await service.import_jsonl(content)
    report2 = await service.import_jsonl(content)

    assert report2.results_deleted == 1
    assert report2.results_inserted == 1
    assert await _count(test_session, CompResult) == 1
    assert await _count(test_session, CompTalent) == 1


@pytest.mark.asyncio
async def test_empty_or_all_invalid_file_never_deletes(test_session: AsyncSession) -> None:
    """Case 3: empty/all-invalid file is rejected WITHOUT touching existing data."""
    await CompImportService(test_session).import_jsonl(
        _sample_file(_person("tourist", {"rank": 1}))
    )
    assert await _count(test_session, CompResult) == 1

    # All lines invalid (bad JSON + missing handle)
    garbage = (
        _jsonl(
            _meta(),
            _series(),
            _contest(),
            {"type": "person", "handle": "", "result": {"rank": 1}},
            {"not": "even a type"},
        )
        + "\n{broken json"
    )
    report = await CompImportService(test_session).import_jsonl(garbage)

    assert report.persons_upserted == 0
    assert report.results_deleted == 0
    assert report.results_inserted == 0
    assert await _count(test_session, CompResult) == 1  # untouched


@pytest.mark.asyncio
async def test_duplicate_handles_in_batch_keep_last(test_session: AsyncSession) -> None:
    """Case 4: duplicated handle in one file keeps the last record, no unique conflict."""
    content = _sample_file(
        _person("Tourist", {"rank": 10}),
        _person("tourist", {"rank": 5}),
    )
    report = await CompImportService(test_session).import_jsonl(content)

    assert report.persons_parsed == 2  # both rows parsed
    assert report.persons_upserted == 1  # deduped to one talent (last record wins)
    assert await _count(test_session, CompTalent) == 1
    rank = await test_session.scalar(select(CompResult.rank).limit(1))
    assert rank == 5  # last record wins


@pytest.mark.asyncio
async def test_incompatible_schema_version_rejected(test_session: AsyncSession) -> None:
    """Case 5: schema_version != 1.0 → whole file rejected."""
    content = _jsonl(_meta(version="2.0"), _series(), _contest(), _person("tourist", {"rank": 1}))
    with pytest.raises(CompImportError, match="schema_version"):
        await CompImportService(test_session).import_jsonl(content)


@pytest.mark.asyncio
async def test_meta_contest_mismatch_rejected(test_session: AsyncSession) -> None:
    """Case 6: meta.contest_external_id != contest.external_id → rejected."""
    content = _jsonl(
        _meta(contest_id="9999"), _series(), _contest(), _person("tourist", {"rank": 1})
    )
    with pytest.raises(CompImportError, match="contest_external_id"):
        await CompImportService(test_session).import_jsonl(content)


@pytest.mark.asyncio
async def test_reimport_replaces_not_appends(test_session: AsyncSession) -> None:
    """Case 7: re-import with changed standings replaces old results."""
    service = CompImportService(test_session)
    await service.import_jsonl(
        _sample_file(_person("tourist", {"rank": 1}), _person("jiangly", {"rank": 2}))
    )
    await service.import_jsonl(
        _sample_file(_person("tourist", {"rank": 5}), _person("benq", {"rank": 2}))
    )

    assert await _count(test_session, CompResult) == 2
    tourist_rank = await test_session.scalar(
        select(CompResult.rank)
        .join(CompTalent, CompResult.talent_id == CompTalent.talent_id)
        .where(CompTalent.handle_lower == "tourist")
    )
    assert tourist_rank == 5
    jiangly = await test_session.scalar(
        select(CompTalent).where(CompTalent.handle_lower == "jiangly")
    )
    assert jiangly is not None
    assert jiangly.contests_count == 1  # his old result was deleted


@pytest.mark.asyncio
async def test_profile_null_never_overwrites_and_max_rating_monotonic(
    test_session: AsyncSession,
) -> None:
    """Case 8: null profile fields don't overwrite; max_rating only increases."""
    service = CompImportService(test_session)
    await service.import_jsonl(
        _sample_file(
            _person("tourist", {"rank": 1, "rating_after": 3900}, school="ITMO", max_rating=3900)
        )
    )
    await service.import_jsonl(
        _sample_file(_person("tourist", {"rank": 2, "rating_after": 3800}, max_rating=3700))
    )

    tourist = await test_session.scalar(
        select(CompTalent).where(CompTalent.handle_lower == "tourist")
    )
    assert tourist is not None
    assert tourist.school == "ITMO"  # preserved, not nulled
    assert tourist.max_rating == 3900  # not lowered


@pytest.mark.asyncio
async def test_team_contest_file_links_team_results(test_session: AsyncSession) -> None:
    """Case 9: team rows are loaded; person.team_name links to the team."""
    content = _jsonl(
        _meta(source="icpc", contest_id="icpc-2024-wf"),
        {"type": "series", "code": "icpc", "name": "ICPC"},
        {"type": "contest", "external_id": "icpc-2024-wf", "name": "2024 ICPC World Finals"},
        {
            "type": "team",
            "name": "MIPT: Red Pine",
            "school": "MIPT",
            "country_code": "RU",
            "members": [{"real_name": "A"}, {"real_name": "B"}],
            "result": {"rank": 1, "award": "gold"},
        },
        _person(
            "member_a",
            {"rank": 1, "award": "gold"},
            real_name="Member A",
            team_name="MIPT: Red Pine",
        ),
    )
    report = await CompImportService(test_session).import_jsonl(content)

    assert report.teams_upserted == 1
    assert report.persons_upserted == 1
    team = await test_session.scalar(
        select(CompTeam).where(CompTeam.name_lower == "mipt: red pine")
    )
    assert team is not None
    team_result = await test_session.scalar(
        select(CompResult).where(CompResult.team_id == team.team_id)
    )
    assert team_result is not None
    assert team_result.award == "gold"
    person_result = await test_session.scalar(
        select(CompResult)
        .join(CompTalent, CompResult.talent_id == CompTalent.talent_id)
        .where(CompTalent.handle_lower == "member_a")
    )
    assert person_result is not None
    assert person_result.team_id == team.team_id


@pytest.mark.asyncio
async def test_person_team_name_without_team_row_auto_creates(test_session: AsyncSession) -> None:
    """Case 10: person.team_name without a team line → auto-create team with warning."""
    content = _sample_file(_person("tourist", {"rank": 1}, team_name="ITMO Legends"))
    report = await CompImportService(test_session).import_jsonl(content)

    team = await test_session.scalar(select(CompTeam).where(CompTeam.name_lower == "itmo legends"))
    assert team is not None
    assert any("auto-created team" in s.reason for s in report.skip_reasons)
    result = await test_session.scalar(select(CompResult).limit(1))
    assert result is not None
    assert result.team_id == team.team_id


@pytest.mark.asyncio
async def test_duplicate_teams_in_batch_merge_members(test_session: AsyncSession) -> None:
    """Case 11: duplicated team rows (same name+school) merge members, keep last result."""
    content = _jsonl(
        _meta(source="icpc", contest_id="icpc-2024-wf"),
        {"type": "series", "code": "icpc", "name": "ICPC"},
        {"type": "contest", "external_id": "icpc-2024-wf", "name": "2024 ICPC World Finals"},
        {
            "type": "team",
            "name": "ZJU: Fantasia",
            "school": "Zhejiang University",
            "members": [{"real_name": "甲"}],
            "result": {"rank": 5},
        },
        {
            "type": "team",
            "name": "ZJU: Fantasia",
            "school": "Zhejiang University",
            "members": [{"real_name": "乙"}],
            "result": {"rank": 3, "award": "bronze"},
        },
    )
    await CompImportService(test_session).import_jsonl(content)

    assert await _count(test_session, CompTeam) == 1
    result = await test_session.scalar(select(CompResult).limit(1))
    assert result is not None
    assert result.rank == 3  # last result wins
    members = result.team_members or []
    assert {m["real_name"] for m in members} == {"甲", "乙"}
