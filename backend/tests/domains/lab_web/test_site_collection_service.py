"""Unit tests for LWSiteCollectionService orchestration (no real network/LLM)."""
from __future__ import annotations

import pytest

from app.domains.lab_web.models.lab_web_site import LWSiteConfig
from app.domains.lab_web.services.lw_site_collection_service import (
    LWSiteCollectionService,
)

pytestmark = pytest.mark.unit


async def test_start_collection_unknown_site(test_session):
    svc = LWSiteCollectionService(test_session)
    with pytest.raises(LookupError):
        await svc.start_collection("nonexistent_site")


async def test_start_collection_inactive_site(test_session, sample_lab):
    site = LWSiteConfig(
        site_code="inactive_site",
        site_name="Inactive",
        parent_lab_code=sample_lab.lab_code,
        people_url="https://example.test/",
        is_active=False,
    )
    test_session.add(site)
    await test_session.commit()
    svc = LWSiteCollectionService(test_session)
    with pytest.raises(RuntimeError):
        await svc.start_collection("inactive_site")
