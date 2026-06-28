"""Unit tests for LWSiteCollectionService orchestration (no real network/LLM)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

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


async def test_run_collection_happy_path_calls_collector(test_session, sample_lab, monkeypatch):
    """I2: the orchestration layer wires fetcher->collector->status correctly.

    _run_collection uses its own AsyncSessionLocal, whose commits aren't visible
    to the test_session (separate connection + test isolation). So we assert the
    orchestration contract directly: the injected fake collector's collect() is
    called exactly once, and _run_collection completes without raising. Status
    persistence is covered by the repository integration tests.
    """
    site = LWSiteConfig(
        site_code="happy_site",
        site_name="Happy",
        parent_lab_code=sample_lab.lab_code,
        people_url="https://example.test/people/",
        is_active=True,
    )
    test_session.add(site)
    await test_session.commit()

    fake_collector = MagicMock()
    fake_collector.collect = AsyncMock(return_value=None)

    def _fake_make_collector(cls_or_self=None, *a, **k):
        return fake_collector

    monkeypatch.setattr(LWSiteCollectionService, "_make_collector", _fake_make_collector)

    svc = LWSiteCollectionService(test_session)
    lab_id = await svc.repo.resolve_lab_id(sample_lab.lab_code)
    task = await svc.task_repo.create_task(
        task_name="t_happy",
        lab_id=lab_id,
        status="pending",
        config_json={"source": "lab_web_site", "site_code": "happy_site"},
    )
    # _run_collection should complete without raising and call collect once.
    await svc._run_collection(int(task.task_id), "happy_site", force_reparse=False)
    fake_collector.collect.assert_awaited_once()



