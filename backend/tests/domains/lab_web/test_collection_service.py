"""Unit tests for LWCollectionService orchestration (no real network)."""
from __future__ import annotations

import pytest

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
