"""Open-API search registry: registration, filtering, factory semantics."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.shared.api.open_api_auth import require_valid_api_key
from app.domains.shared.services.api_key_service import ApiKeyService
from app.domains.shared.services.open_api.registry import (
    UnifiedTalentSummary,
    get_search_provider_factories,
    register_search_provider,
    registered_domains,
)


class _FakeProvider:
    def __init__(self, domain: str) -> None:
        self.domain = domain

    async def search(self, keyword: str, limit: int) -> list[UnifiedTalentSummary]:
        return [
            UnifiedTalentSummary(
                domain=self.domain, talent_id=1, name=keyword, identifier="x", tags=["t"]
            )
        ]


@pytest.fixture(autouse=True)
def _clean_registry():
    from app.domains.shared.services.open_api import registry

    saved = dict(registry._REGISTRY)
    registry._REGISTRY.clear()
    yield
    registry._REGISTRY.clear()
    registry._REGISTRY.update(saved)


def test_register_and_filter_providers() -> None:
    register_search_provider("fake_a", lambda session: _FakeProvider("fake_a"))
    register_search_provider("fake_b", lambda session: _FakeProvider("fake_b"))

    assert set(registered_domains()) == {"fake_a", "fake_b"}
    assert set(get_search_provider_factories()) == {"fake_a", "fake_b"}
    assert set(get_search_provider_factories(["fake_a"])) == {"fake_a"}
    # Unknown domains are silently ignored (not an error)
    assert get_search_provider_factories(["fake_a", "nope"]) == get_search_provider_factories(
        ["fake_a"]
    )


def test_re_registration_overrides_same_domain() -> None:
    register_search_provider("fake_a", lambda session: _FakeProvider("fake_a"))
    register_search_provider("fake_a", lambda session: _FakeProvider("other"))
    assert len(registered_domains()) == 1


@pytest.mark.asyncio
async def test_require_valid_api_key_no_scope_check(test_session: AsyncSession) -> None:
    svc = ApiKeyService(test_session)
    created = await svc.create_key(key_name="搜索", scopes=["lab:read"], created_by=1)
    await test_session.commit()

    dep = require_valid_api_key()
    principal = await dep(request=_FakeRequest(), api_key=created["key"], session=test_session)
    assert principal["role"] == "api_agent"
    assert principal["scopes"] == ["lab:read"]

    with pytest.raises(Exception) as exc_info:
        await dep(request=_FakeRequest(), api_key="ak_wrong", session=test_session)
    assert exc_info.value.status_code == 401


class _FakeRequest:
    """Minimal Request stand-in for the dependency (only url.path is read)."""

    class _URL:
        path = "/test"

    url = _URL()
