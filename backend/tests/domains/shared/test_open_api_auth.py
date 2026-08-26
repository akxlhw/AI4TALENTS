"""require_api_key dependency: 401/403 semantics and principal shape."""

from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.shared.api.open_api_auth import require_api_key
from app.domains.shared.services.api_key_service import ApiKeyService


@pytest.fixture
def probe_app(test_session: AsyncSession) -> FastAPI:
    async def override_session():
        yield test_session

    a = FastAPI()
    a.dependency_overrides[get_async_session] = override_session

    @a.get("/probe")
    async def probe(principal: dict = Depends(require_api_key("academic:read"))):
        return principal

    return a


@pytest.mark.asyncio
async def test_missing_header_401(
    test_session: AsyncSession, probe_app: FastAPI
) -> None:
    async with AsyncClient(transport=ASGITransport(app=probe_app), base_url="http://t") as c:
        r = await c.get("/probe")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_wrong_or_unknown_key_401(
    test_session: AsyncSession, probe_app: FastAPI
) -> None:
    async with AsyncClient(transport=ASGITransport(app=probe_app), base_url="http://t") as c:
        r = await c.get("/probe", headers={"X-API-Key": "ak_wrong"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_scope_missing_403(test_session: AsyncSession, probe_app: FastAPI) -> None:
    svc = ApiKeyService(test_session)
    created = await svc.create_key(key_name="只读行业", scopes=["industry:read"], created_by=1)
    await test_session.commit()
    async with AsyncClient(transport=ASGITransport(app=probe_app), base_url="http://t") as c:
        r = await c.get("/probe", headers={"X-API-Key": created["key"]})
    assert r.status_code == 403
    assert "academic:read" in r.json()["detail"]


@pytest.mark.asyncio
async def test_valid_key_returns_principal(
    test_session: AsyncSession, probe_app: FastAPI
) -> None:
    svc = ApiKeyService(test_session)
    created = await svc.create_key(
        key_name="洞察", scopes=["academic:read", "industry:write"], created_by=1
    )
    await test_session.commit()
    async with AsyncClient(transport=ASGITransport(app=probe_app), base_url="http://t") as c:
        r = await c.get("/probe", headers={"X-API-Key": created["key"]})
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "api_agent"
    assert body["key_name"] == "洞察"
    assert set(body["scopes"]) == {"academic:read", "industry:write"}
