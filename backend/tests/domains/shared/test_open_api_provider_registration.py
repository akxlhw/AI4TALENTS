"""All five domains register search providers; integration via the endpoint.

The registry must stay clean of the previous test file's fakes — importing
the domain provider modules here registers the real factories.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.shared.services.api_key_service import ApiKeyService
from app.domains.shared.services.open_api.registry import registered_domains

_ALL = ["academic", "competition", "industry", "lab", "open_source"]  # sorted


def test_all_five_domains_registered() -> None:
    # Import the api modules (as api_router does) to trigger registration
    import app.domains.academic.api.open_api  # noqa: F401
    import app.domains.competition.api.open_api  # noqa: F401
    import app.domains.industry.api.open_api  # noqa: F401
    import app.domains.lab.api.open_api  # noqa: F401
    import app.domains.open_source.api.open_api  # noqa: F401

    assert registered_domains() == _ALL


@pytest.mark.asyncio
async def test_unified_search_against_seeded_domains(
    client: AsyncClient, test_session: AsyncSession
) -> None:
    from app.domains.open_source.models.open_source import OSDeveloper

    test_session.add(
        OSDeveloper(
            github_login="zsearchdev",
            github_id=991,
            name="搜索测试开发者",
            tech_tags=["models"],
            is_visible=True,
        )
    )
    await test_session.commit()

    scopes = [f"{d}:read" for d in _ALL]
    created = await ApiKeyService(test_session).create_key(
        key_name="全读", scopes=scopes, created_by=1
    )
    await test_session.commit()

    r = await client.get(
        "/api/v1/open-api/search/talents",
        params={"keyword": "zsearchdev", "domains": "open_source,industry", "per_domain": 5},
        headers={"X-API-Key": created["key"]},
    )
    assert r.status_code == 200
    body = r.json()
    assert set(body["domains"]) == {"open_source", "industry"}
    matches = [i for i in body["items"] if i["identifier"] == "zsearchdev"]
    assert matches, body["items"]
    assert matches[0]["url"] == "https://github.com/zsearchdev"
    # industry returned zero rows but no error (empty is a valid result)
    assert "industry" not in body["errors"]
