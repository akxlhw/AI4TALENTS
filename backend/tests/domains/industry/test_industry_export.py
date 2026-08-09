"""Tests for industry talent export endpoint and export→import round-trip.

Covers the cross-server migration contract: export on server A as JSONL,
import on server B via the existing upload endpoint, verify the merge
semantics (operational state preserved, scores refreshed).
"""

from __future__ import annotations

import json

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.industry.models.industry import (
    IndustryPosition,
    IndustryPositionTalent,
    IndustryTalent,
)
from app.domains.industry.services.industry_import_service import IndustryImportService
from app.domains.shared.api.auth import get_current_user
from app.main import app


def _jsonl(*records: dict) -> str:
    return "\n".join(json.dumps(r, ensure_ascii=False) for r in records)


@pytest.fixture
async def admin_client(client: AsyncClient, test_session: AsyncSession) -> AsyncClient:
    """super_admin client backed by a real user row."""
    from app.domains.shared.models.iam import UserAccount

    user = UserAccount(
        username="export_admin",
        email="export_admin@example.com",
        password_hash="x",
        role_type="super_admin",
        is_active=True,
    )
    test_session.add(user)
    await test_session.commit()
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": user.user_id,
        "username": "export_admin",
        "role": "super_admin",
    }
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
async def user_client(client: AsyncClient) -> AsyncClient:
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": 1,
        "username": "normal_user",
        "role": "user",
    }
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
async def export_position(test_session: AsyncSession) -> IndustryPosition:
    """One position with two batches of candidates."""
    pos = IndustryPosition(
        title="LLM 系统工程师",
        department="基础架构",
        tech_direction_codes=["ai"],
        status="open",
    )
    test_session.add(pos)
    await test_session.commit()
    service = IndustryImportService(test_session)
    # Batch b1: two candidates with full scores
    await service.import_jsonl(
        _jsonl(
            {
                "name": "王五",
                "current_org": "字节跳动",
                "current_title": "资深算法工程师",
                "degree": "硕士",
                "years_of_exp": "8年",
                "location": "北京",
                "source": "maimai",
                "match_score": 92,
                "score_school": 80,
                "score_company": 95,
                "score_direction": 90,
                "match_tags": ["LLM", "Infra"],
                "match_reason": "LLM 系统方向匹配",
            },
            {
                "name": "赵六",
                "current_org": "阿里巴巴",
                "current_title": "技术专家",
                "degree": "博士",
                "source": "linkedin",
                "match_score": 85,
            },
        ),
        position_id=pos.position_id,
        batch="b1",
    )
    # Batch b2: one candidate
    await service.import_jsonl(
        _jsonl(
            {
                "name": "钱七",
                "current_org": "百度",
                "current_title": "架构师",
                "match_score": 78,
                "source": "maimai",
            }
        ),
        position_id=pos.position_id,
        batch="b2",
    )
    return pos


# ============ Format & filtering ============


@pytest.mark.asyncio
async def test_export_returns_jsonl_format(
    admin_client: AsyncClient, export_position: IndustryPosition
) -> None:
    """Export produces one valid JSON object per line, contract-aligned fields."""
    resp = await admin_client.get(
        f"/api/v1/industry/positions/{export_position.position_id}/export"
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/x-jsonlines")
    assert "attachment" in resp.headers["content-disposition"]

    lines = [line for line in resp.text.strip().split("\n") if line]
    assert len(lines) == 3  # b1(2) + b2(1)

    for line in lines:
        record = json.loads(line)
        # talent-layer contract fields
        for talent_field in (
            "name",
            "current_org",
            "current_title",
            "degree",
            "years_of_exp",
            "experiences",
            "expect",
            "location",
            "profile_url",
            "photo_url",
            "source",
        ):
            assert talent_field in record, f"missing talent field: {talent_field}"
        # link-layer contract fields
        for link_field in (
            "position_id",
            "match_score",
            "score_school",
            "score_company",
            "score_direction",
            "match_tags",
            "match_reason",
            "batch",
        ):
            assert link_field in record, f"missing link field: {link_field}"
        # operational state MUST NOT be exported
        for forbidden in ("touched", "status", "notes", "dedup_hash", "talent_id", "is_visible"):
            assert forbidden not in record, f"operational/internal field leaked: {forbidden}"


@pytest.mark.asyncio
async def test_export_filter_by_batch(
    admin_client: AsyncClient, export_position: IndustryPosition
) -> None:
    """Batch filter restricts export to that batch only."""
    resp = await admin_client.get(
        f"/api/v1/industry/positions/{export_position.position_id}/export",
        params={"batch": "b1"},
    )
    assert resp.status_code == 200
    lines = [line for line in resp.text.strip().split("\n") if line]
    assert len(lines) == 2
    names = {json.loads(line)["name"] for line in lines}
    assert names == {"王五", "赵六"}


@pytest.mark.asyncio
async def test_export_empty_position_returns_404(
    admin_client: AsyncClient, test_session: AsyncSession
) -> None:
    """Exporting a position with no candidates returns 404."""
    pos = IndustryPosition(title="空岗位", status="open")
    test_session.add(pos)
    await test_session.commit()
    resp = await admin_client.get(f"/api/v1/industry/positions/{pos.position_id}/export")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_export_requires_super_admin(
    user_client: AsyncClient, export_position: IndustryPosition
) -> None:
    """Normal user cannot export (super_admin only)."""
    resp = await user_client.get(f"/api/v1/industry/positions/{export_position.position_id}/export")
    assert resp.status_code == 403


# ============ Export → Import round-trip ============


@pytest.mark.asyncio
async def test_export_import_roundtrip(
    admin_client: AsyncClient,
    export_position: IndustryPosition,
    test_session: AsyncSession,
) -> None:
    """Export → wipe → re-import → data identical, operational state reset to defaults."""
    pid = export_position.position_id

    # 1. Export batch b1 (王五 + 赵六)
    resp = await admin_client.get(
        f"/api/v1/industry/positions/{pid}/export", params={"batch": "b1"}
    )
    assert resp.status_code == 200
    exported_jsonl = resp.text

    # 2. Simulate "server B": delete the batch, then re-import the exported file
    del_resp = await admin_client.delete(f"/api/v1/industry/positions/{pid}/batches/b1")
    assert del_resp.status_code == 200
    assert del_resp.json()["links_deleted"] == 2

    # 3. Re-import the exported JSONL
    import_resp = await admin_client.post(
        "/api/v1/industry/import/upload",
        data={"position_id": str(pid), "batch": "b1"},
        files={"file": ("export.jsonl", exported_jsonl.encode("utf-8"), "application/x-jsonlines")},
    )
    assert import_resp.status_code == 200
    report = import_resp.json()
    assert report["total_parsed"] == 2

    # 4. Verify 王五's data round-tripped with scores intact
    result = await test_session.execute(select(IndustryTalent).where(IndustryTalent.name == "王五"))
    talent = result.scalar_one()
    assert talent.current_org == "字节跳动"
    assert talent.degree == "硕士"
    assert talent.location == "北京"

    link_result = await test_session.execute(
        select(IndustryPositionTalent).where(
            IndustryPositionTalent.talent_id == talent.talent_id,
            IndustryPositionTalent.position_id == pid,
        )
    )
    link = link_result.scalar_one()
    assert link.match_score == 92
    assert link.score_school == 80
    assert link.score_company == 95
    assert link.score_direction == 90
    # Operational state reset to defaults on fresh import
    assert link.touched is False
    assert link.status == "new"
    assert link.batch == "b1"


@pytest.mark.asyncio
async def test_export_preserves_merge_semantics(
    admin_client: AsyncClient,
    export_position: IndustryPosition,
    test_session: AsyncSession,
) -> None:
    """Import onto a server that already has operational state: state preserved, scores refreshed."""
    pid = export_position.position_id

    # 1. Set operational state on 王五's link (simulating server B's recruiting progress)
    result = await test_session.execute(select(IndustryTalent).where(IndustryTalent.name == "王五"))
    talent = result.scalar_one()
    link_result = await test_session.execute(
        select(IndustryPositionTalent).where(
            IndustryPositionTalent.talent_id == talent.talent_id,
            IndustryPositionTalent.position_id == pid,
        )
    )
    link = link_result.scalar_one()
    link.touched = True
    link.status = "contacted"
    link.notes = "已通过内推联系"
    await test_session.commit()

    # 2. Export b1 from this position (operational state NOT in the file)
    resp = await admin_client.get(
        f"/api/v1/industry/positions/{pid}/export", params={"batch": "b1"}
    )
    assert resp.status_code == 200
    exported_jsonl = resp.text
    # Confirm operational state absent from export
    for line in exported_jsonl.strip().split("\n"):
        rec = json.loads(line)
        assert "touched" not in rec
        assert "status" not in rec
        assert "notes" not in rec

    # 3. Re-import (simulating A's export landing on B which has the operational state)
    import_resp = await admin_client.post(
        "/api/v1/industry/import/upload",
        data={"position_id": str(pid), "batch": "b1"},
        files={"file": ("export.jsonl", exported_jsonl.encode("utf-8"), "application/x-jsonlines")},
    )
    assert import_resp.status_code == 200

    # 4. Operational state PRESERVED, scores refreshed from export
    await test_session.refresh(link)
    assert link.touched is True  # preserved
    assert link.status == "contacted"  # preserved
    assert link.notes == "已通过内推联系"  # preserved
    assert link.match_score == 92  # refreshed from export (same value here)


@pytest.mark.asyncio
async def test_null_batch_listed_and_deletable(
    admin_client: AsyncClient,
    export_position: IndustryPosition,
    test_session: AsyncSession,
) -> None:
    """Rows imported without a batch id must show up as a (null) batch group
    and be deletable via the __none__ sentinel — no blind spot."""
    pid = export_position.position_id
    service = IndustryImportService(test_session)
    await service.import_jsonl(
        _jsonl({"name": "孙八", "current_org": "美团", "match_score": 66}),
        position_id=pid,
        batch=None,
    )

    # 1. list_batches includes the null group alongside b1/b2
    resp = await admin_client.get(f"/api/v1/industry/positions/{pid}/batches")
    assert resp.status_code == 200
    batches = {row["batch"]: row["count"] for row in resp.json()}
    assert batches.get("b1") == 2
    assert batches.get("b2") == 1
    assert batches.get(None) == 1  # null-batch group visible

    # 2. delete via the __none__ sentinel removes only the null-batch rows
    del_resp = await admin_client.delete(f"/api/v1/industry/positions/{pid}/batches/__none__")
    assert del_resp.status_code == 200
    assert del_resp.json()["links_deleted"] == 1

    remaining = await test_session.execute(
        select(IndustryPositionTalent).where(IndustryPositionTalent.position_id == pid)
    )
    remaining_batches = sorted(link.batch for link in remaining.scalars().all())
    assert remaining_batches == ["b1", "b1", "b2"]

    # 3. export with the sentinel filters exactly the null group (now empty → 404)
    exp_resp = await admin_client.get(
        f"/api/v1/industry/positions/{pid}/export", params={"batch": "__none__"}
    )
    assert exp_resp.status_code == 404
