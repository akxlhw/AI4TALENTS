"""Tests for the lab profile endpoint — including lab names containing slashes.

Regression: "Princeton CS / ML" contains "/" which broke the old
``/labs/{parent_lab}/profile`` route (404 → frontend lost the profile banner
and role tabs). The route now uses the ``{parent_lab:path}`` converter.
"""

from __future__ import annotations

import json
from urllib.parse import quote

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.lab.services.lab_import_service import LabImportService
from app.domains.shared.api.auth import get_current_user
from app.main import app

PROFILE_PATH = "/api/v1/lab/labs/{name}/profile"


@pytest.fixture
async def user_client(client: AsyncClient) -> AsyncClient:
    """HTTP client with an authenticated user dependency override."""
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": 1,
        "username": "tester",
        "role": "user",
    }
    yield client
    app.dependency_overrides.pop(get_current_user, None)


async def _seed_lab(session: AsyncSession, parent_lab: str) -> None:
    lab_header = json.dumps(
        {
            "type": "lab",
            "lab_name": parent_lab,
            "lab_slug": "test_slug",
            "homepage": "https://example.edu",
            "description": "A test lab",
        }
    )
    person = json.dumps(
        {
            "name": "Test Person",
            "role_section": "Faculty",
            "lab_name": parent_lab,
            "parent_lab": parent_lab,
            "source_url": "https://example.edu/people",
            "collected_at": "2026-07-17T10:00:00Z",
        }
    )
    await LabImportService(session).import_jsonl(lab_header + "\n" + person, parent_lab)


@pytest.mark.asyncio
async def test_profile_with_slash_in_lab_name(
    user_client: AsyncClient, test_session: AsyncSession
) -> None:
    """Lab names containing "/" must resolve to their profile, not 404."""
    await _seed_lab(test_session, "Princeton CS / ML")
    # quote() encodes "/" as %2F; the server decodes it before routing
    response = await user_client.get(PROFILE_PATH.format(name=quote("Princeton CS / ML")))
    assert response.status_code == 200
    body = response.json()
    assert body["parent_lab"] == "Princeton CS / ML"
    assert body["description"] == "A test lab"
    assert body["role_distribution"] == {"professor": 1}
    assert body["total_talents"] == 1


@pytest.mark.asyncio
async def test_profile_with_plain_lab_name(
    user_client: AsyncClient, test_session: AsyncSession
) -> None:
    """Normal lab names keep working after the path-converter change."""
    await _seed_lab(test_session, "MIT CSAIL")
    response = await user_client.get(PROFILE_PATH.format(name=quote("MIT CSAIL")))
    assert response.status_code == 200
    assert response.json()["parent_lab"] == "MIT CSAIL"
