"""Tests for the industry talent API-Key push import channel.

Covers the machine-to-machine import flow (POST /industry/import with
X-API-Key header) that lets the sourcing skill push JSONL without admin
manual upload. Verifies the auth boundary, error cases, and audit logging.
"""

from __future__ import annotations

import json

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.industry.models.industry import IndustryPosition, IndustryTalent
from app.domains.shared.models.system_config import SystemConfig

_API_KEY = "test-secret-key-do-not-use-in-prod"
_VALID_JSONL = json.dumps(
    {
        "name": "测试候选人",
        "current_org": "测试公司",
        "current_title": "工程师",
        "source": "maimai",
        "match_score": 90,
    },
    ensure_ascii=False,
)


async def _set_api_key(session: AsyncSession, value: str = _API_KEY) -> None:
    """Insert (or update) the INDUSTRY_IMPORT_API_KEY config row."""
    existing = await session.execute(
        select(SystemConfig).where(SystemConfig.config_key == "INDUSTRY_IMPORT_API_KEY")
    )
    row = existing.scalar_one_or_none()
    if row is None:
        session.add(
            SystemConfig(
                config_key="INDUSTRY_IMPORT_API_KEY",
                config_value=value,
                config_type="string",
                is_sensitive=True,
            )
        )
    else:
        row.config_value = value
    await session.commit()
    # Bust ConfigService cache so the new value is visible to the endpoint
    from app.domains.shared.services.config_service import ConfigService

    ConfigService.clear_cache()


async def _make_position(session: AsyncSession) -> IndustryPosition:
    pos = IndustryPosition(title="push 测试岗位", status="open")
    session.add(pos)
    await session.commit()
    return pos


@pytest.mark.asyncio
async def test_push_import_success(client: AsyncClient, test_session: AsyncSession) -> None:
    """Valid API key + valid JSONL → 200, data imported."""
    await _set_api_key(test_session)
    pos = await _make_position(test_session)

    resp = await client.post(
        f"/api/v1/industry/import?position_id={pos.position_id}",
        headers={"X-API-Key": _API_KEY, "Content-Type": "application/x-jsonlines"},
        content=_VALID_JSONL,
    )
    assert resp.status_code == 200, resp.text
    report = resp.json()
    assert report["total_parsed"] == 1
    assert report["talents_inserted"] == 1

    # Verify the talent actually landed in the DB
    result = await test_session.execute(
        select(IndustryTalent).where(IndustryTalent.name == "测试候选人")
    )
    talent = result.scalar_one()
    assert talent.current_org == "测试公司"


@pytest.mark.asyncio
async def test_push_import_missing_api_key_header(
    client: AsyncClient, test_session: AsyncSession
) -> None:
    """No X-API-Key header → 401."""
    await _set_api_key(test_session)
    pos = await _make_position(test_session)

    resp = await client.post(
        f"/api/v1/industry/import?position_id={pos.position_id}",
        content=_VALID_JSONL,
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_push_import_wrong_api_key(client: AsyncClient, test_session: AsyncSession) -> None:
    """Wrong API key → 401."""
    await _set_api_key(test_session)
    pos = await _make_position(test_session)

    resp = await client.post(
        f"/api/v1/industry/import?position_id={pos.position_id}",
        headers={"X-API-Key": "wrong-key"},
        content=_VALID_JSONL,
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_push_import_api_key_not_configured(
    client: AsyncClient, test_session: AsyncSession
) -> None:
    """No key in DB → 503 (admin must configure first)."""
    # Ensure no key configured (default state, but clear cache to be safe)
    from app.domains.shared.services.config_service import ConfigService

    ConfigService.clear_cache()
    pos = await _make_position(test_session)

    resp = await client.post(
        f"/api/v1/industry/import?position_id={pos.position_id}",
        headers={"X-API-Key": _API_KEY},
        content=_VALID_JSONL,
    )
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_push_import_empty_body(client: AsyncClient, test_session: AsyncSession) -> None:
    """Empty body → 200 but report.aborted=True (0 valid rows, nothing written)."""
    await _set_api_key(test_session)
    pos = await _make_position(test_session)

    resp = await client.post(
        f"/api/v1/industry/import?position_id={pos.position_id}",
        headers={"X-API-Key": _API_KEY},
        content="",
    )
    assert resp.status_code == 200
    report = resp.json()
    assert report["aborted"] is True
    assert report["total_parsed"] == 0


@pytest.mark.asyncio
async def test_push_import_unknown_position(
    client: AsyncClient, test_session: AsyncSession
) -> None:
    """Non-existent position_id → 404 (get_position raises NotFoundError)."""
    await _set_api_key(test_session)

    resp = await client.post(
        "/api/v1/industry/import?position_id=999999",
        headers={"X-API-Key": _API_KEY},
        content=_VALID_JSONL,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_push_import_does_not_require_jwt(
    client: AsyncClient, test_session: AsyncSession
) -> None:
    """Push channel works with only X-API-Key, no Bearer/JWT token at all."""
    await _set_api_key(test_session)
    pos = await _make_position(test_session)

    # Explicitly send NO Authorization header — only X-API-Key
    resp = await client.post(
        f"/api/v1/industry/import?position_id={pos.position_id}",
        headers={"X-API-Key": _API_KEY, "Content-Type": "application/x-jsonlines"},
        content=_VALID_JSONL,
    )
    assert resp.status_code == 200
    assert resp.json()["total_parsed"] == 1


@pytest.mark.asyncio
async def test_push_import_with_batch_param(
    client: AsyncClient, test_session: AsyncSession
) -> None:
    """Batch query param is honored — imported talents carry the batch tag."""
    await _set_api_key(test_session)
    pos = await _make_position(test_session)

    resp = await client.post(
        f"/api/v1/industry/import?position_id={pos.position_id}&batch=agent-2026-08",
        headers={"X-API-Key": _API_KEY},
        content=_VALID_JSONL,
    )
    assert resp.status_code == 200
    assert resp.json()["total_parsed"] == 1

    # Verify batch recorded on the link (via repository)
    from app.domains.industry.repositories.industry_repository import IndustryRepository

    rows = await IndustryRepository(test_session).list_batches(pos.position_id)
    batch_names = {r["batch"] for r in rows}
    assert "agent-2026-08" in batch_names


@pytest.mark.asyncio
async def test_push_import_audit_logged(client: AsyncClient, test_session: AsyncSession) -> None:
    """Successful push import writes an audit log with operation='import'."""
    from app.domains.shared.models.audit import AuditOperationLog

    await _set_api_key(test_session)
    pos = await _make_position(test_session)

    resp = await client.post(
        f"/api/v1/industry/import?position_id={pos.position_id}&batch=audit-test",
        headers={"X-API-Key": _API_KEY},
        content=_VALID_JSONL,
    )
    assert resp.status_code == 200

    # Read audit log on the same test session's connection
    log_result = await test_session.execute(
        select(AuditOperationLog)
        .where(
            AuditOperationLog.operation == "import",
            AuditOperationLog.resource_type == "industry_talent",
        )
        .order_by(AuditOperationLog.log_id.desc())
        .limit(1)
    )
    log = log_result.scalar_one_or_none()
    assert log is not None, "import audit log not written"
    assert log.status == "success"
    assert log.user_id is None  # machine call, no user
    assert log.event_subtype == "import"
    detail = log.operation_detail
    assert detail["source"] == "api_key"
    assert detail["batch"] == "audit-test"
    assert detail["position_id"] == pos.position_id


@pytest.mark.asyncio
async def test_agent_can_list_positions_with_api_key(
    client: AsyncClient, test_session: AsyncSession
) -> None:
    """Agent discovers position_id via GET /industry/positions with X-API-Key.

    GET /industry/positions accepts both JWT (admin UI) and API Key (sourcing
    skill). This test verifies the API Key path works and returns position_id.
    """
    await _set_api_key(test_session)
    pos1 = await _make_position(test_session)
    pos2 = IndustryPosition(title="第二个岗位", status="open")
    test_session.add(pos2)
    await test_session.commit()

    resp = await client.get(
        "/api/v1/industry/positions",
        headers={"X-API-Key": _API_KEY},
    )
    assert resp.status_code == 200
    items = resp.json()
    ids = {item["position_id"] for item in items}
    assert pos1.position_id in ids
    assert pos2.position_id in ids
    sample = items[0]
    assert "position_id" in sample
    assert "title" in sample
    assert "status" in sample


@pytest.mark.asyncio
async def test_list_positions_no_credentials_returns_401(client: AsyncClient) -> None:
    """Without any credential (no JWT, no X-API-Key), returns 401."""
    resp = await client.get("/api/v1/industry/positions")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_positions_works_with_jwt_user(
    client: AsyncClient, test_session: AsyncSession
) -> None:
    """Regression: a logged-in user (JWT) must still access GET /industry/positions.

    This was broken when the API-Key position endpoint was registered in
    import_endpoint.py (registered before positions.py), shadowing the JWT
    endpoint and returning 401 for all normal users — kicking them back to
    the login page. The endpoints are now merged into one dual-auth endpoint.
    """
    from app.domains.shared.api.auth import get_current_user
    from app.main import app

    await _make_position(test_session)
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": 1,
        "username": "normal_user",
        "role": "user",
    }
    try:
        resp = await client.get("/api/v1/industry/positions")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1
    finally:
        app.dependency_overrides.pop(get_current_user, None)
