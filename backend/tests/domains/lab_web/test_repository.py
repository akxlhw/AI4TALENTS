"""Integration tests for LWRepository (uses talent_db_test)."""
from __future__ import annotations

import pytest

from app.domains.lab_web.repositories.lab_web import LWRepository

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
