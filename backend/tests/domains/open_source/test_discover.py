"""Tests for the auto-discover feature (keyword seeds + status machine + API).

Taxonomy v2: directions come from the shared taxonomy (75 codes); element
layer (34 codes) is the tech_element value domain.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import create_access_token
from app.domains.open_source.constants.discover_keywords import (
    DIRECTION_SEARCH_KEYWORDS,
    DIRECTION_TO_DOMAIN,
    DIRECTION_TO_ELEMENT,
    DOMAIN_MIN_STARS_OVERRIDE,
)
from app.domains.open_source.services.discover_service import (
    DISCOVER_STATUS_KEY,
    is_heartbeat_alive,
)
from app.domains.shared.constants.tech_taxonomy import (
    TECH_DIRECTIONS,
    TECH_DOMAINS,
    VALID_TECH_ELEMENTS,
)

# The 75 direction codes from the shared taxonomy (single source of truth)
SEEDED_DIRECTIONS = {code for code, _, _, _ in TECH_DIRECTIONS}


# ============ Keyword seed completeness ============


def test_keywords_cover_all_seeded_directions() -> None:
    """Every taxonomy direction has at least one search query."""
    missing = SEEDED_DIRECTIONS - set(DIRECTION_SEARCH_KEYWORDS)
    assert not missing, f"Directions without keywords: {missing}"


def test_keywords_have_no_extra_directions() -> None:
    """No keyword entries for directions that don't exist in the taxonomy."""
    extra = set(DIRECTION_SEARCH_KEYWORDS) - SEEDED_DIRECTIONS
    assert not extra, f"Keywords reference unknown directions: {extra}"


def test_direction_to_domain_covers_all() -> None:
    """Every direction maps to a valid domain code."""
    domain_codes = {d["code"] for d in TECH_DOMAINS}
    assert set(DIRECTION_TO_DOMAIN) == SEEDED_DIRECTIONS
    for direction, domain in DIRECTION_TO_DOMAIN.items():
        assert domain in domain_codes, f"{direction} → invalid domain {domain}"


def test_direction_to_element_covers_all() -> None:
    """Every direction maps to a valid element code (tech_element domain)."""
    assert set(DIRECTION_TO_ELEMENT) == SEEDED_DIRECTIONS
    for direction, element in DIRECTION_TO_ELEMENT.items():
        assert element in VALID_TECH_ELEMENTS, f"{direction} → invalid element {element}"


def test_threshold_override_domains_exist() -> None:
    """Per-domain threshold overrides reference real domain codes."""
    domain_codes = {d["code"] for d in TECH_DOMAINS}
    for domain in DOMAIN_MIN_STARS_OVERRIDE:
        assert domain in domain_codes, f"override references unknown domain: {domain}"


def test_taxonomy_shape() -> None:
    """Structural sanity: 10 domains / 34 elements / 75 directions."""
    assert len(TECH_DOMAINS) == 10
    assert len(VALID_TECH_ELEMENTS) == 34
    assert len(TECH_DIRECTIONS) == 75


# ============ Heartbeat ============


def test_heartbeat_alive_fresh() -> None:
    from datetime import datetime, timezone

    fresh = datetime.now(timezone.utc).isoformat()
    assert is_heartbeat_alive(fresh) is True


def test_heartbeat_alive_stale() -> None:
    from datetime import datetime, timedelta, timezone

    stale = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    assert is_heartbeat_alive(stale) is False


def test_heartbeat_alive_garbage() -> None:
    assert is_heartbeat_alive(None) is False
    assert is_heartbeat_alive("not-a-date") is False


# ============ API (real JWT — open_source auth reads the header directly) ============


@pytest.fixture
async def super_admin_headers(client: AsyncClient, test_session: AsyncSession):
    """Create a super-admin user row and a valid Bearer token for it."""
    from app.domains.shared.models.iam import UserAccount

    user = UserAccount(
        username="discover_admin",
        email="discover_admin@example.com",
        password_hash="x",
        role_type="super_admin",
        is_active=True,
    )
    test_session.add(user)
    await test_session.commit()
    token = create_access_token(user_id=user.user_id, username=user.username, role="super_admin")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def normal_user_headers(client: AsyncClient, test_session: AsyncSession):
    """Create a normal user row and a valid Bearer token for it."""
    from app.domains.shared.models.iam import UserAccount

    user = UserAccount(
        username="discover_user",
        email="discover_user@example.com",
        password_hash="x",
        role_type="user",
        is_active=True,
    )
    test_session.add(user)
    await test_session.commit()
    token = create_access_token(user_id=user.user_id, username=user.username, role="user")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_discover_status_default_idle(client: AsyncClient, super_admin_headers: dict) -> None:
    """GET /discover/status returns a well-formed status doc."""
    resp = await client.get("/api/v1/open-source/discover/status", headers=super_admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in {"idle", "running", "completed", "error"}
    assert isinstance(data["results"], list)
    assert "processed" in data and "total" in data


@pytest.mark.asyncio
async def test_discover_requires_auth(client: AsyncClient) -> None:
    """No token → 401."""
    resp = await client.get("/api/v1/open-source/discover/status")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_discover_start_requires_super_admin(
    client: AsyncClient, normal_user_headers: dict
) -> None:
    """Normal users cannot start discovery (403)."""
    resp = await client.post(
        "/api/v1/open-source/discover/start",
        json={"direction_codes": [], "min_stars": 30000},
        headers=normal_user_headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_discover_start_writes_status(
    client: AsyncClient,
    super_admin_headers: dict,
    test_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """After a start request, the status key exists in sys_config.

    The real run_discovery coroutine is stubbed out: it makes live GitHub
    calls and holds a pooled DB session that outlives the test, which dead-
    locks later tests' TRUNCATE teardown (table locks). start_discovery's
    synchronous status write is what this test verifies.
    """
    from app.domains.open_source.services import discover_service
    from app.domains.shared.services.config_service import ConfigService

    async def _fake_run_discovery(
        direction_codes: list[str], min_stars: int, min_contributors: int = 0
    ) -> None:
        """No-op stub: the real coroutine is what this test explicitly avoids."""
        return None

    monkeypatch.setattr(discover_service, "run_discovery", _fake_run_discovery)

    resp = await client.post(
        "/api/v1/open-source/discover/start",
        json={"direction_codes": ["llm"], "min_stars": 50000},
        headers=super_admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "running"
    assert data["total"] == 1
    assert data["params"]["min_stars"] == 50000

    # The (stubbed) background task was spawned; give it a beat to run
    import asyncio

    await asyncio.sleep(0.05)
    cfg = await ConfigService(test_session).get_value(
        DISCOVER_STATUS_KEY, default=None, use_cache=False
    )
    assert cfg is not None
    assert cfg["status"] in {"running", "completed", "error"}


@pytest.mark.asyncio
async def test_discover_start_empty_means_all_directions(
    client: AsyncClient, super_admin_headers: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression: an empty direction_codes list defaults to ALL seeded
    directions — previously it ran 0 directions and 'completed' instantly
    with no results (read as a silent failure)."""
    from app.domains.open_source.services import discover_service

    captured: dict = {}

    async def _capture_run(
        direction_codes: list[str], min_stars: int, min_contributors: int = 0
    ) -> None:
        captured["directions"] = direction_codes
        captured["min_stars"] = min_stars
        captured["min_contributors"] = min_contributors

    monkeypatch.setattr(discover_service, "run_discovery", _capture_run)

    resp = await client.post(
        "/api/v1/open-source/discover/start",
        json={"direction_codes": [], "min_stars": 30000},
        headers=super_admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == len(DIRECTION_SEARCH_KEYWORDS)  # all 75
    assert len(data["params"]["direction_codes"]) == len(DIRECTION_SEARCH_KEYWORDS)
