"""Open-API read endpoints: auth gate + envelope shape for all five domains."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.shared.services.api_key_service import ApiKeyService

_ENDPOINTS = [
    ("/api/v1/open-api/academic/talents", "academic:read"),
    ("/api/v1/open-api/open-source/talents", "open_source:read"),
    ("/api/v1/open-api/competition/talents", "competition:read"),
    ("/api/v1/open-api/lab/talents", "lab:read"),
    ("/api/v1/open-api/industry/talents", "industry:read"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("url,scope", _ENDPOINTS)
async def test_read_endpoints_require_scope(
    client: AsyncClient, test_session: AsyncSession, url: str, scope: str
) -> None:
    # No key -> 401
    r = await client.get(url)
    assert r.status_code == 401

    # Key without the domain scope -> 403
    svc = ApiKeyService(test_session)
    created = await svc.create_key(key_name="无权限", scopes=["other:read"], created_by=1)
    await test_session.commit()
    r = await client.get(url, headers={"X-API-Key": created["key"]})
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_academic_talents_envelope(client: AsyncClient, test_session: AsyncSession) -> None:
    svc = ApiKeyService(test_session)
    created = await svc.create_key(key_name="学术读", scopes=["academic:read"], created_by=1)
    await test_session.commit()
    r = await client.get("/api/v1/open-api/academic/talents", headers={"X-API-Key": created["key"]})
    assert r.status_code == 200
    body = r.json()
    assert set(body) >= {"items", "total", "page", "page_size"}
    for item in body["items"]:
        assert "orcid" not in item and "extra_data" not in item
