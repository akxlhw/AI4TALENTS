"""ApiKeyService behavior: generate/hash/verify/scope/revocation/expiry."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.shared.services.api_key_service import ApiKeyService


def _utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.mark.asyncio
async def test_create_and_verify_roundtrip(test_session: AsyncSession) -> None:
    svc = ApiKeyService(test_session)
    created = await svc.create_key(
        key_name="洞察 Skill", scopes=["academic:read", "industry:write"], created_by=1
    )
    await test_session.commit()

    assert created["key"].startswith("ak_")
    assert len(created["key"]) == 46  # ak_ + 43 chars base62
    assert created["record"].key_prefix == created["key"][:8]
    assert created["record"].key_hash != created["key"]  # hashed, not plaintext

    verified = await svc.verify_key(created["key"])
    assert verified is not None
    assert verified.api_key_id == created["record"].api_key_id


@pytest.mark.asyncio
async def test_verify_rejects_unknown_and_revoked(test_session: AsyncSession) -> None:
    svc = ApiKeyService(test_session)
    assert await svc.verify_key("ak_unknown") is None

    created = await svc.create_key(key_name="x", scopes=["academic:read"], created_by=1)
    await test_session.commit()
    await svc.set_active(created["record"].api_key_id, False)
    await test_session.commit()
    assert await svc.verify_key(created["key"]) is None


@pytest.mark.asyncio
async def test_verify_rejects_expired(test_session: AsyncSession) -> None:
    svc = ApiKeyService(test_session)
    created = await svc.create_key(
        key_name="过期",
        scopes=["academic:read"],
        expires_at=_utcnow_naive() - timedelta(minutes=1),
    )
    await test_session.commit()
    assert await svc.verify_key(created["key"]) is None


@pytest.mark.asyncio
async def test_scope_check_and_last_used_touch(test_session: AsyncSession) -> None:
    svc = ApiKeyService(test_session)
    created = await svc.create_key(key_name="部分授权", scopes=["academic:read"], created_by=1)
    await test_session.commit()

    assert svc.has_scope(created["record"], "academic:read") is True
    assert svc.has_scope(created["record"], "industry:write") is False

    await svc.verify_key(created["key"])
    await test_session.commit()
    await test_session.refresh(created["record"])
    assert created["record"].last_used_at is not None
