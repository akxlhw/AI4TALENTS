"""Tests for the industry import service — incremental upsert rules."""

from __future__ import annotations

import json
import logging

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.industry.models.industry import (
    IndustryPosition,
    IndustryPositionTalent,
    IndustryTalent,
)
from app.domains.industry.services.industry_import_service import (
    IndustryImportService,
    compute_dedup_hash,
    parse_years_of_exp,
)


def _jsonl(*records: dict) -> str:
    return "\n".join(json.dumps(r, ensure_ascii=False) for r in records)


async def _make_position(
    session: AsyncSession, title: str = "大模型推理工程师", **kwargs
) -> IndustryPosition:
    position = IndustryPosition(title=title, status="open", **kwargs)
    session.add(position)
    await session.commit()
    return position


@pytest.fixture
async def position(test_session: AsyncSession) -> IndustryPosition:
    return await _make_position(test_session)


@pytest.fixture
async def position2(test_session: AsyncSession) -> IndustryPosition:
    return await _make_position(test_session, title="推荐算法工程师")


# ============ pure helpers ============


def test_dedup_hash_normalization() -> None:
    """Full-width → half-width, whitespace collapse, empty → '' all map together."""
    base = compute_dedup_hash("张三", "亚马逊云科技", "应用科学家")
    # full-width characters + extra whitespace normalize to the same hash
    assert base == compute_dedup_hash("张三 ", " 亚马逊云科技", "应用科学家")
    assert base == compute_dedup_hash("张三", "亚马逊云科技", "应用科学家")
    # different org → different hash （王伟问题：同名不同人不合并）
    assert base != compute_dedup_hash("张三", "其他公司", "应用科学家")
    # missing org/title normalize to empty string, not crash
    assert compute_dedup_hash("张三", None, None) == compute_dedup_hash("张三", "", "  ")


def test_parse_years_of_exp() -> None:
    assert parse_years_of_exp("10年") == 10.0
    assert parse_years_of_exp("8-10年") == 8.0
    assert parse_years_of_exp("3.5年") == 3.5
    assert parse_years_of_exp(7) == 7.0
    assert parse_years_of_exp("应届") is None
    assert parse_years_of_exp(None) is None


# ============ import & upsert rules ============


@pytest.mark.asyncio
async def test_import_creates_talent_and_link(
    test_session: AsyncSession, position: IndustryPosition
) -> None:
    content = _jsonl(
        {
            "name": "张三",
            "current_org": "亚马逊云科技",
            "current_title": "应用科学家",
            "degree": "博士",
            "years_of_exp": "10年",
            "location": "北京",
            "source": "maimai",
            "match_score": 98,
            "score_school": 95,
            "score_company": 90,
            "score_direction": 99,
            "match_tags": ["顶级院校", "LLM"],
            "match_reason": "CMU 博士，AWS 大模型推理团队 10 年",
            "batch": "2026-08-llm",
        }
    )
    report = await IndustryImportService(test_session).import_jsonl(
        content, position_id=position.position_id
    )
    assert report.total_lines == 1
    assert report.total_parsed == 1
    assert report.talents_inserted == 1
    assert report.links_inserted == 1
    assert report.talents_updated == 0
    assert report.skipped == 0

    talent = (await test_session.execute(select(IndustryTalent))).scalar_one()
    assert talent.name == "张三"
    assert talent.years_of_exp_num == 10.0
    assert talent.dedup_hash == compute_dedup_hash("张三", "亚马逊云科技", "应用科学家")

    link = (await test_session.execute(select(IndustryPositionTalent))).scalar_one()
    assert link.position_id == position.position_id
    assert link.match_score == 98
    assert link.score_direction == 99
    assert link.status == "new"
    assert link.touched is False
    assert link.batch == "2026-08-llm"
    assert link.source_platform == "maimai"


@pytest.mark.asyncio
async def test_upsert_empty_fields_do_not_overwrite(
    test_session: AsyncSession, position: IndustryPosition
) -> None:
    """Rule 1: fields absent/empty in a later import keep the old values."""
    service = IndustryImportService(test_session)
    await service.import_jsonl(
        _jsonl(
            {
                "name": "李四",
                "current_org": "腾讯",
                "current_title": "研究员",
                "degree": "博士",
                "location": "深圳",
                "match_score": 80,
            }
        ),
        position_id=position.position_id,
    )
    # Second import: degree empty (no overwrite), location updated, score updated
    report = await service.import_jsonl(
        _jsonl(
            {
                "name": "李四",
                "current_org": "腾讯",
                "current_title": "研究员",
                "degree": "",
                "location": "北京",
                "match_score": 85,
            }
        ),
        position_id=position.position_id,
    )
    assert report.talents_inserted == 0
    assert report.talents_updated == 1
    assert report.links_updated == 1

    talent = (await test_session.execute(select(IndustryTalent))).scalar_one()
    assert talent.current_title == "研究员"  # hash component, unchanged
    assert talent.degree == "博士"  # empty string does not overwrite
    assert talent.location == "北京"  # non-empty field updates

    link = (await test_session.execute(select(IndustryPositionTalent))).scalar_one()
    assert link.match_score == 85


@pytest.mark.asyncio
async def test_link_upsert_preserves_recruiting_state(
    test_session: AsyncSession, position: IndustryPosition
) -> None:
    """Rule: touched/status/notes survive re-import; only scores update."""
    service = IndustryImportService(test_session)
    await service.import_jsonl(
        _jsonl({"name": "王五", "current_org": "阿里", "match_score": 70}),
        position_id=position.position_id,
    )
    link = (await test_session.execute(select(IndustryPositionTalent))).scalar_one()
    link.status = "connected"
    link.touched = True
    link.notes = "一面通过"
    await test_session.commit()

    await service.import_jsonl(
        _jsonl({"name": "王五", "current_org": "阿里", "match_score": 88}),
        position_id=position.position_id,
    )
    await test_session.refresh(link)
    assert link.match_score == 88
    assert link.status == "connected"
    assert link.touched is True
    assert link.notes == "一面通过"


@pytest.mark.asyncio
async def test_absent_talents_not_deleted(
    test_session: AsyncSession, position: IndustryPosition
) -> None:
    """Rule 2: talents absent from a new batch are left untouched."""
    service = IndustryImportService(test_session)
    await service.import_jsonl(
        _jsonl(
            {"name": "甲", "current_org": "A公司", "match_score": 60},
            {"name": "乙", "current_org": "B公司", "match_score": 61},
        ),
        position_id=position.position_id,
    )
    await service.import_jsonl(
        _jsonl({"name": "甲", "current_org": "A公司", "match_score": 62}),
        position_id=position.position_id,
    )
    count = await test_session.scalar(select(func.count()).select_from(IndustryTalent))
    assert count == 2  # 乙 was not deleted


@pytest.mark.asyncio
async def test_same_talent_new_position_only_adds_link(
    test_session: AsyncSession,
    position: IndustryPosition,
    position2: IndustryPosition,
) -> None:
    """Rule 3: an existing talent in a new position gains only a new link."""
    service = IndustryImportService(test_session)
    await service.import_jsonl(
        _jsonl({"name": "赵六", "current_org": "字节", "match_score": 90}),
        position_id=position.position_id,
    )
    link1 = (await test_session.execute(select(IndustryPositionTalent))).scalar_one()
    link1.status = "connected"
    await test_session.commit()

    report = await service.import_jsonl(
        _jsonl({"name": "赵六", "current_org": "字节", "match_score": 75}),
        position_id=position2.position_id,
    )
    assert report.talents_inserted == 0
    assert report.links_inserted == 1

    talent_count = await test_session.scalar(select(func.count()).select_from(IndustryTalent))
    assert talent_count == 1
    links = (await test_session.execute(select(IndustryPositionTalent))).scalars().all()
    assert len(links) == 2
    old = next(link for link in links if link.position_id == position.position_id)
    assert old.status == "connected"  # other position's state untouched
    assert old.match_score == 90


@pytest.mark.asyncio
async def test_dedup_merges_same_person(
    test_session: AsyncSession, position: IndustryPosition
) -> None:
    """Same normalized (name, org, title) merges into one talent row."""
    service = IndustryImportService(test_session)
    await service.import_jsonl(
        _jsonl({"name": "王伟", "current_org": "　华为 ", "match_score": 70}),
        position_id=position.position_id,
    )
    await service.import_jsonl(
        _jsonl({"name": "王伟", "current_org": "华为", "match_score": 72}),
        position_id=position.position_id,
    )
    count = await test_session.scalar(select(func.count()).select_from(IndustryTalent))
    assert count == 1  # full-width space + trailing space normalized away


@pytest.mark.asyncio
async def test_invalid_lines_skipped_not_fatal(
    test_session: AsyncSession, position: IndustryPosition
) -> None:
    content = "\n".join(
        [
            "{not valid json",
            json.dumps({"current_org": "某公司"}),  # missing name
            json.dumps({"name": "错岗位", "position_id": 999999}),  # unknown position
            json.dumps({"name": "正常", "current_org": "某公司", "match_score": 50}),
        ]
    )
    report = await IndustryImportService(test_session).import_jsonl(
        content, position_id=position.position_id
    )
    assert report.total_parsed == 1
    assert report.skipped == 3
    reasons = [r.reason for r in report.skip_reasons]
    assert "invalid JSON" in reasons
    assert "missing name" in reasons
    assert "unknown position_id: 999999" in reasons
    assert report.talents_inserted == 1


@pytest.mark.asyncio
async def test_missing_position_id_skipped(
    test_session: AsyncSession, position: IndustryPosition
) -> None:
    """Without a default position, rows lacking position_id are skipped."""
    content = _jsonl({"name": "无岗位", "current_org": "某公司"})
    report = await IndustryImportService(test_session).import_jsonl(content)
    assert report.total_parsed == 0
    assert report.skipped == 1
    assert report.skip_reasons[0].reason == "missing position_id"


@pytest.mark.asyncio
async def test_missing_current_org_warns(
    test_session: AsyncSession, position: IndustryPosition
) -> None:
    content = _jsonl({"name": "无名氏", "match_score": 50})
    messages: list[str] = []

    class _Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            messages.append(record.getMessage())

    module_logger = logging.getLogger("app.domains.industry.services.industry_import_service")
    handler = _Capture()
    module_logger.addHandler(handler)
    try:
        report = await IndustryImportService(test_session).import_jsonl(
            content, position_id=position.position_id
        )
    finally:
        module_logger.removeHandler(handler)
    assert report.warnings == 1
    assert any("current_org" in m for m in messages)


@pytest.mark.asyncio
async def test_row_position_id_overrides_param(
    test_session: AsyncSession,
    position: IndustryPosition,
    position2: IndustryPosition,
) -> None:
    """A row-level position_id overrides the import parameter (contract v1.0)."""
    content = _jsonl({"name": "甲", "position_id": position2.position_id, "match_score": 60})
    report = await IndustryImportService(test_session).import_jsonl(
        content, position_id=position.position_id
    )
    assert report.links_inserted == 1
    link = (await test_session.execute(select(IndustryPositionTalent))).scalar_one()
    assert link.position_id == position2.position_id


# ============ hard guards (lab/competition standard) ============


@pytest.mark.asyncio
async def test_empty_file_aborts_without_writing(
    test_session: AsyncSession, position: IndustryPosition
) -> None:
    """Hard guard: an empty file writes nothing and is explicitly flagged."""
    report = await IndustryImportService(test_session).import_jsonl(
        "", position_id=position.position_id
    )
    assert report.aborted is True
    assert report.total_parsed == 0
    talent_count = await test_session.scalar(select(func.count()).select_from(IndustryTalent))
    link_count = await test_session.scalar(select(func.count()).select_from(IndustryPositionTalent))
    assert talent_count == 0
    assert link_count == 0


@pytest.mark.asyncio
async def test_all_invalid_lines_abort_without_writing(
    test_session: AsyncSession, position: IndustryPosition
) -> None:
    """Hard guard: a fully-invalid file is an error signal, not a silent success."""
    content = "\n".join(
        [
            "{not valid json",
            json.dumps({"current_org": "某公司"}),  # missing name
        ]
    )
    report = await IndustryImportService(test_session).import_jsonl(
        content, position_id=position.position_id
    )
    assert report.aborted is True
    assert report.total_parsed == 0
    assert report.skipped == 2
    talent_count = await test_session.scalar(select(func.count()).select_from(IndustryTalent))
    assert talent_count == 0


@pytest.mark.asyncio
async def test_single_row_db_error_isolated(
    test_session: AsyncSession,
    position: IndustryPosition,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A DB error on one row rolls that row back alone; other rows still commit."""
    from sqlalchemy.exc import OperationalError

    original_upsert_link = IndustryImportService._upsert_link

    async def flaky_upsert_link(self, talent, row, default_batch):  # type: ignore[no-untyped-def]
        if row.get("name") == "坏行":
            raise OperationalError("INSERT", {}, Exception("simulated DB failure"))
        return await original_upsert_link(self, talent, row, default_batch)

    monkeypatch.setattr(IndustryImportService, "_upsert_link", flaky_upsert_link)

    content = _jsonl(
        {"name": "正常", "current_org": "某公司", "match_score": 50},
        {"name": "坏行", "current_org": "坏公司", "match_score": 60},
    )
    report = await IndustryImportService(test_session).import_jsonl(
        content, position_id=position.position_id
    )

    assert report.aborted is False
    assert report.talents_inserted == 1
    assert report.links_inserted == 1
    assert report.skipped == 1
    assert report.skip_reasons[0].reason.startswith("db error")

    # The bad row's talent insert rolled back with its savepoint; the good
    # row committed atomically in the outer transaction.
    talents = (await test_session.execute(select(IndustryTalent))).scalars().all()
    assert [t.name for t in talents] == ["正常"]
    links = (await test_session.execute(select(IndustryPositionTalent))).scalars().all()
    assert len(links) == 1
