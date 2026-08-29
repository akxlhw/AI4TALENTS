"""Per-API-key rate limit enforcement (rate_limit_per_minute)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.shared.services.api_key_service import ApiKeyService
from app.domains.shared.services.open_api.rate_limiter import api_key_rate_limiter

_URL = "/api/v1/open-api/academic/stats"


@pytest.fixture(autouse=True)
def _reset_limiter():
    api_key_rate_limiter.reset()
    yield
    api_key_rate_limiter.reset()


@pytest.mark.asyncio
async def test_per_key_rate_limit_429(client: AsyncClient, test_session: AsyncSession) -> None:
    created = await ApiKeyService(test_session).create_key(
        key_name="rl", scopes=["academic:read"], rate_limit_per_minute=2, created_by=1
    )
    await test_session.commit()
    headers = {"X-API-Key": created["key"]}
    assert (await client.get(_URL, headers=headers)).status_code == 200
    assert (await client.get(_URL, headers=headers)).status_code == 200
    r3 = await client.get(_URL, headers=headers)
    assert r3.status_code == 429
    assert "Retry-After" in r3.headers


@pytest.mark.asyncio
async def test_no_limit_when_unset(client: AsyncClient, test_session: AsyncSession) -> None:
    created = await ApiKeyService(test_session).create_key(
        key_name="rl2", scopes=["academic:read"], created_by=1
    )
    await test_session.commit()
    headers = {"X-API-Key": created["key"]}
    for _ in range(5):
        r = await client.get(_URL, headers=headers)
        assert r.status_code == 200
