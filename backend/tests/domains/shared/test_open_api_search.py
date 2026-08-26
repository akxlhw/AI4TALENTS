"""Cross-domain unified search endpoint: aggregation, degrade, scope gate."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.shared.services.api_key_service import ApiKeyService
from app.domains.shared.services.open_api.registry import (
    UnifiedTalentSummary,
    register_search_provider,
)

_SEARCH_URL = "/api/v1/open-api/search/talents"


class _FakeProvider:
    def __init__(self, domain: str, *, fail: bool = False) -> None:
        self.domain = domain
        self._fail = fail

    async def search(self, keyword: str, limit: int) -> list[UnifiedTalentSummary]:
        if self._fail:
            raise RuntimeError("provider exploded")
        return [
            UnifiedTalentSummary(
                domain=self.domain, talent_id=i, name=f"{keyword}-{i}", identifier="x", tags=["t"]
            )
            for i in range(limit)
        ]


@pytest.fixture(autouse=True)
def _fake_registry():
    from app.domains.shared.services.open_api import registry

    saved = dict(registry._REGISTRY)
    registry._REGISTRY.clear()
    register_search_provider("fake_a", lambda session: _FakeProvider("fake_a"))
    register_search_provider("fake_b", lambda session: _FakeProvider("fake_b", fail=True))
    yield
    registry._REGISTRY.clear()
    registry._REGISTRY.update(saved)


async def _make_key(session: AsyncSession, scopes: list[str]) -> str:
    created = await ApiKeyService(session).create_key(
        key_name="search", scopes=scopes, created_by=1
    )
    await session.commit()
    return created["key"]


@pytest.mark.asyncio
async def test_search_requires_auth(client: AsyncClient) -> None:
    r = await client.get(_SEARCH_URL, params={"keyword": "abc"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_search_missing_scope_403_lists_domains(
    client: AsyncClient, test_session: AsyncSession
) -> None:
    key = await _make_key(test_session, ["fake_a:read"])
    r = await client.get(
        _SEARCH_URL,
        params={"keyword": "abc", "domains": "fake_a,fake_b"},
        headers={"X-API-Key": key},
    )
    assert r.status_code == 403
    assert "fake_b:read" in r.json()["detail"]


@pytest.mark.asyncio
async def test_search_aggregates_and_degrades(
    client: AsyncClient, test_session: AsyncSession
) -> None:
    key = await _make_key(test_session, ["fake_a:read", "fake_b:read"])
    r = await client.get(
        _SEARCH_URL, params={"keyword": "abc", "per_domain": 3}, headers={"X-API-Key": key}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["keyword"] == "abc"
    assert set(body["domains"]) == {"fake_a", "fake_b"}
    # fake_a returned 3 items; fake_b failed and is degraded into errors
    assert len([i for i in body["items"] if i["domain"] == "fake_a"]) == 3
    assert "exploded" in body["errors"]["fake_b"]


@pytest.mark.asyncio
async def test_search_unknown_domains_reported(
    client: AsyncClient, test_session: AsyncSession
) -> None:
    key = await _make_key(test_session, ["fake_a:read"])
    r = await client.get(
        _SEARCH_URL,
        params={"keyword": "abc", "domains": "fake_a,nope"},
        headers={"X-API-Key": key},
    )
    assert r.status_code == 200
    assert r.json()["unknown_domains"] == ["nope"]
