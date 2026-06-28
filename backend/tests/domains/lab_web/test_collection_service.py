"""Unit tests for LWCollectionService orchestration (no real network)."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

from app.domains.lab_web.repositories.lab_web import LWRepository
from app.domains.lab_web.services.collectors.base_collector import CollectContext
from app.domains.lab_web.services.lw_collection_service import LWCollectionService

pytestmark = pytest.mark.unit


async def test_start_collection_lab_not_implemented(test_session, sample_lab):
    """A lab with collector_class=None yields a failed task with clear error."""
    sample_lab.collector_class = None
    await test_session.commit()

    svc = LWCollectionService(test_session)
    task_id = await svc.start_collection(sample_lab.lab_id)  # no created_by (no FK user)
    # Synchronous failure path: task is created then immediately failed.
    task = await svc.repo.get_task(task_id)
    assert task.status == "failed"
    assert "not implemented" in (task.error_message or "").lower()


async def test_start_collection_unknown_lab(test_session):
    svc = LWCollectionService(test_session)
    with pytest.raises(LookupError):
        await svc.start_collection(999999, created_by=1)


async def test_start_collection_inactive_lab(test_session, sample_lab):
    sample_lab.is_active = False
    await test_session.commit()
    svc = LWCollectionService(test_session)
    with pytest.raises(RuntimeError):
        await svc.start_collection(sample_lab.lab_id, created_by=1)


async def test_watch_cancel_sets_event_when_task_cancelled(test_session, sample_lab):
    """C2 fix: the cancel-watcher observes a DB 'cancelled' status and sets
    ctx.cancelled so a running collector loop can stop cooperatively.

    Without this wiring, POST /tasks/{id}/cancel would flip a DB flag that the
    running scrape loop never reads (a no-op on running tasks).
    """
    repo = LWRepository(test_session)
    task = await repo.create_task(task_name="t1", lab_id=sample_lab.lab_id, status="running")
    ctx = CollectContext(task_id=int(task.task_id), lab_id=sample_lab.lab_id)

    # Flip the task to cancelled after a short delay so the watcher observes it.
    async def flip_after_delay():
        await asyncio.sleep(0.1)
        await repo.update_task(int(task.task_id), status="cancelled")

    # Poll quickly (0.05s) so the test resolves fast.
    with patch("app.domains.lab_web.services.lw_collection_service.settings") as mock_settings:
        mock_settings.LAB_WEB_CANCEL_POLL_INTERVAL = 0.05
        flipper = asyncio.create_task(flip_after_delay())
        await asyncio.wait_for(
            LWCollectionService._watch_cancel(ctx, repo, int(task.task_id)),
            timeout=2.0,
        )
        await flipper
    assert ctx.cancelled.is_set()
