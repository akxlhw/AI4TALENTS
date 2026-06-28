"""Integration tests for LWRepository (uses talent_db_test)."""
from __future__ import annotations

import pytest

from app.domains.lab_web.repositories.lab_web import LWRepository
from app.domains.lab_web.services.collectors.base_collector import RawPersonDraft

pytestmark = pytest.mark.integration


async def test_lab_crud(test_session, sample_lab):
    repo = LWRepository(test_session)
    fetched = await repo.get_lab(sample_lab.lab_id)
    assert fetched is not None
    assert fetched.lab_code == "test_lab"

    by_code = await repo.get_lab_by_code("test_lab")
    assert by_code is not None
    assert by_code.lab_id == sample_lab.lab_id

    labs = await repo.list_labs(only_active=True)
    assert any(l.lab_code == "test_lab" for l in labs)


async def test_task_lifecycle(test_session, sample_lab):
    repo = LWRepository(test_session)
    task = await repo.create_task(
        task_name="t1", lab_id=sample_lab.lab_id, status="pending"
    )
    assert task.task_id is not None
    await repo.update_task(task.task_id, status="running", progress_percent=50)
    refreshed = await repo.get_task(task.task_id)
    assert refreshed.status == "running"
    assert refreshed.progress_percent == 50
    tasks = await repo.list_tasks(lab_id=sample_lab.lab_id)
    assert len(tasks) == 1


async def test_upsert_raw_persons_dedups_by_hash(test_session, sample_lab):
    repo = LWRepository(test_session)
    task = await repo.create_task(
        task_name="t1", lab_id=sample_lab.lab_id, status="running"
    )
    drafts = [
        RawPersonDraft(name_raw="John Smith", title_raw="PhD Candidate"),
        # Duplicate of the first (same name/title/email/homepage => same hash).
        RawPersonDraft(name_raw="John Smith", title_raw="PhD Candidate"),
        RawPersonDraft(name_raw="Jane Doe", title_raw="Professor"),
    ]
    created = await repo.upsert_raw_persons(
        lab_id=sample_lab.lab_id,
        drafts=drafts,
        task_id=task.task_id,
        lab_code="test_lab",
    )
    # Two distinct persons despite three drafts.
    assert len(created) == 2
    rows = await repo.get_raw_persons_by_task(task.task_id)
    assert len(rows) == 2
    names = {r.name_raw for r in rows}
    assert names == {"John Smith", "Jane Doe"}


async def test_raw_layer_is_append_only(test_session, sample_lab):
    """Re-inserting the same person across tasks adds a new snapshot row."""
    repo = LWRepository(test_session)
    t1 = await repo.create_task(task_name="t1", lab_id=sample_lab.lab_id, status="success")
    await repo.upsert_raw_persons(
        lab_id=sample_lab.lab_id,
        drafts=[RawPersonDraft(name_raw="John Smith")],
        task_id=t1.task_id,
        lab_code="test_lab",
    )
    t2 = await repo.create_task(task_name="t2", lab_id=sample_lab.lab_id, status="success")
    await repo.upsert_raw_persons(
        lab_id=sample_lab.lab_id,
        drafts=[RawPersonDraft(name_raw="John Smith")],
        task_id=t2.task_id,
        lab_code="test_lab",
    )
    from sqlalchemy import select

    from app.domains.lab_web.models.lab_web import LWRawPerson

    result = await test_session.execute(
        select(LWRawPerson).where(LWRawPerson.name_raw == "John Smith")
    )
    rows = list(result.scalars().all())
    # Two snapshots across two tasks, even though hash is identical.
    assert len(rows) == 2

