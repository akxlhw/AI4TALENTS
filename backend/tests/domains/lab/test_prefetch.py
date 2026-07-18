"""Tests for lab homepage prefetch endpoints and service."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.lab.models.lab_talent import LabTalent
from app.domains.lab.services.homepage_preview_service import HomepagePreviewService
from app.domains.shared.services.config_service import ConfigService
from app.main import app

PREFETCH_STATUS_PATH = "/api/v1/lab/prefetch-homepages/status"
PREFETCH_TRIGGER_PATH = "/api/v1/lab/prefetch-homepages"


@pytest.fixture
async def admin_client(client: AsyncClient) -> AsyncClient:
    """HTTP client with admin auth dependency overridden."""
    from app.domains.shared.api.auth import require_admin

    app.dependency_overrides[require_admin] = lambda: {
        "user_id": 1,
        "username": "admin",
        "role": "admin",
    }
    yield client
    app.dependency_overrides.pop(require_admin, None)


async def _set_lab_status(session: AsyncSession, parent_lab: str, status: dict[str, Any]) -> None:
    config_service = ConfigService(session)
    await config_service.set_value(
        f"lab_homepage_prefetch_status:{parent_lab}", status, config_type="json"
    )
    await session.commit()


@pytest.mark.asyncio
async def test_prefetch_status_requires_auth(client: AsyncClient) -> None:
    """The status endpoint must reject unauthenticated requests."""
    response = await client.get(PREFETCH_STATUS_PATH, params={"parent_lab": "Test Lab"})
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_prefetch_status_is_per_lab(
    admin_client: AsyncClient, test_session: AsyncSession
) -> None:
    """Status is scoped by parent_lab and does not leak across labs."""
    await _set_lab_status(
        test_session,
        "Lab A",
        {
            "status": "running",
            "processed": 3,
            "total": 10,
            "current": "Alice",
            "errors": 0,
            "heartbeat_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    running = await admin_client.get(PREFETCH_STATUS_PATH, params={"parent_lab": "Lab A"})
    assert running.status_code == 200
    assert running.json()["status"] == "running"
    assert running.json()["processed"] == 3

    idle = await admin_client.get(PREFETCH_STATUS_PATH, params={"parent_lab": "Lab B"})
    assert idle.status_code == 200
    assert idle.json()["status"] == "idle"


@pytest.mark.asyncio
async def test_stale_heartbeat_allows_retrigger(
    admin_client: AsyncClient, test_session: AsyncSession
) -> None:
    """A running but stale status is treated as idle and can be retriggered."""
    stale_time = (datetime.now(timezone.utc) - timedelta(seconds=400)).isoformat()
    await _set_lab_status(
        test_session,
        "Stale Lab",
        {
            "status": "running",
            "processed": 1,
            "total": 5,
            "current": "Bob",
            "errors": 0,
            "heartbeat_at": stale_time,
        },
    )

    with patch.object(
        HomepagePreviewService,
        "prefetch_all",
        new=AsyncMock(return_value={"total": 0, "fetched": 0, "failed": 0}),
    ):
        response = await admin_client.post(
            PREFETCH_TRIGGER_PATH, params={"parent_lab": "Stale Lab"}
        )
        assert response.status_code == 200

        # Give the background task a moment to update status.
        await asyncio.sleep(0.2)

        status_resp = await admin_client.get(
            PREFETCH_STATUS_PATH, params={"parent_lab": "Stale Lab"}
        )
        data = status_resp.json()
        assert data["status"] in ("pending", "running", "completed")


@pytest.mark.asyncio
async def test_running_prefetch_returns_409(
    admin_client: AsyncClient, test_session: AsyncSession
) -> None:
    """Triggering a prefetch for a lab that is already running returns 409."""
    heartbeat = datetime.now(timezone.utc).isoformat()
    await _set_lab_status(
        test_session,
        "Running Lab",
        {
            "status": "running",
            "processed": 1,
            "total": 5,
            "current": "Carol",
            "errors": 0,
            "heartbeat_at": heartbeat,
        },
    )

    response = await admin_client.post(PREFETCH_TRIGGER_PATH, params={"parent_lab": "Running Lab"})
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_fetch_preview_rejects_invalid_url() -> None:
    """fetch_preview rejects non-http/https URLs."""
    svc = HomepagePreviewService()
    result = await svc.fetch_preview("mailto:alice@example.com")
    assert result["status"] == "invalid_url"


@pytest.mark.asyncio
async def test_fetch_preview_rejects_non_html() -> None:
    """fetch_preview rejects responses that are not text/html."""
    svc = HomepagePreviewService()
    raw = {
        "status_code": 200,
        "content": b"PDF content",
        "final_url": "https://example.com/cv.pdf",
        "content_type": "application/pdf",
        "is_html": False,
        "too_large": False,
    }
    with patch.object(svc, "_fetch_raw_with_retry", new=AsyncMock(return_value=raw)):
        result = await svc.fetch_preview("https://example.com/cv.pdf")
        assert result["status"] == "not_html"


@pytest.mark.asyncio
async def test_prefetch_all_respects_ttl_and_updates_cache(
    test_session: AsyncSession,
) -> None:
    """prefetch_all re-fetches talents whose cached homepage has expired."""
    from datetime import datetime as dt

    # Insert a talent with an expired cache.
    talent = LabTalent(
        name="Expired Talent",
        parent_lab="TTL Lab",
        lab_name="TTL Lab",
        role_section="PhD Students",
        role_type="student",
        academic_level="phd",
        homepage="https://example.com/expired",
        homepage_cache="<html><body>old</body></html>",
        homepage_cached_at=dt.utcnow() - timedelta(days=10),
        is_visible=True,
        dedup_hash="expired-talent-hash",
    )
    test_session.add(talent)
    await test_session.commit()

    svc = HomepagePreviewService()
    with patch.object(
        svc,
        "fetch_preview",
        new=AsyncMock(
            return_value={
                "html": "<html><body>new</body></html>",
                "base_url": "https://example.com/expired",
                "title": "New",
                "status": "ok",
            }
        ),
    ):
        result = await svc.prefetch_all(test_session, "TTL Lab")
        assert result["total"] == 1
        assert result["fetched"] == 1
        assert result["failed"] == 0

    # Refresh and verify cache was updated.
    await test_session.refresh(talent)
    assert talent.homepage_cache == "<html><body>new</body></html>"
    assert talent.homepage_cached_at is not None
    assert talent.homepage_cached_at > dt.utcnow() - timedelta(minutes=1)


@pytest.mark.asyncio
async def test_prefetch_all_skips_fresh_cache(
    test_session: AsyncSession,
) -> None:
    """prefetch_all skips talents whose cached homepage is still fresh."""
    from datetime import datetime as dt

    talent = LabTalent(
        name="Fresh Talent",
        parent_lab="Fresh Lab",
        lab_name="Fresh Lab",
        role_section="PhD Students",
        role_type="student",
        academic_level="phd",
        homepage="https://example.com/fresh",
        homepage_cache="<html><body>fresh</body></html>",
        homepage_cached_at=dt.utcnow(),
        is_visible=True,
        dedup_hash="fresh-talent-hash",
    )
    test_session.add(talent)
    await test_session.commit()

    svc = HomepagePreviewService()
    with patch.object(svc, "fetch_preview", new=AsyncMock()) as mock_fetch:
        result = await svc.prefetch_all(test_session, "Fresh Lab")
        assert result["total"] == 0
        assert result["fetched"] == 0
        mock_fetch.assert_not_awaited()
