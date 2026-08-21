"""Regression tests for collect-task fixes.

1. get_active_tasks must eager-load tech_domain — the API handler reads
   t.tech_domain.domain_name, and the lazy load blew up with
   "greenlet_spawn has not been called" (500 on /collect/tasks/active).
2. Venue sub-task completion must write author counters — the executor
   only ever passed works_fetched, so authors_fetched/new_authors stayed
   0 forever ("采集人数是 0" in the UI despite authors landing in DB).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.academic.models.raw_data import RawAuthor
from app.domains.academic.models.sync import CollectTask
from app.domains.academic.models.tech_domain import TechDomain
from app.domains.academic.models.venue import Venue, VenueSubTask
from app.domains.academic.services.collect.venue_executor import VenueSubTaskExecutor
from app.domains.academic.services.collect_service import CollectService
from app.domains.academic.services.common.progress import CollectionProgress, FetchProgress


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.mark.asyncio
async def test_get_active_tasks_eager_loads_tech_domain(
    test_session: AsyncSession,
) -> None:
    domain = TechDomain(domain_code="cnt-test", domain_name="计数测试领域")
    test_session.add(domain)
    await test_session.flush()

    test_session.add(
        CollectTask(
            task_code="CNT-ACTIVE-1",
            tech_domain_id=domain.tech_domain_id,
            triggered_at=_utcnow(),
            status="running",
        )
    )
    await test_session.commit()
    # Clear the identity map so the relationship cannot be resolved from
    # in-session objects — mirrors production where /tasks/active runs on a
    # fresh session and the lazy load has to hit the database.
    test_session.expunge_all()

    service = CollectService(test_session)
    tasks = await service.get_active_tasks()

    running = [t for t in tasks if t.task_code == "CNT-ACTIVE-1"]
    assert running, "seeded running task not returned"
    # Pre-fix this attribute access raised greenlet_spawn errors
    assert running[0].tech_domain is not None
    assert running[0].tech_domain.domain_name == "计数测试领域"


@pytest.mark.asyncio
async def test_venue_executor_writes_author_counters(
    test_session: AsyncSession,
) -> None:
    domain = TechDomain(domain_code="cnt-exec", domain_name="执行测试领域")
    test_session.add(domain)
    await test_session.flush()

    venue = Venue(
        venue_code="cnt-venue",
        venue_name="Counters Conference",
        openalex_source_id="S123",
    )
    test_session.add(venue)

    task = CollectTask(
        task_code="CNT-EXEC-1",
        tech_domain_id=domain.tech_domain_id,
        triggered_at=_utcnow(),
        time_window_start=datetime(2020, 1, 1),
        time_window_end=_utcnow(),
        status="running",
    )
    test_session.add(task)
    await test_session.flush()

    sub_task = VenueSubTask(task_id=task.task_id, venue_id=venue.venue_id)
    test_session.add(sub_task)

    # A1 already in the library; A2/A3 are new
    test_session.add(RawAuthor(openalex_author_id="A1", raw_json="{}"))
    await test_session.commit()

    class _StubFetcher:
        async def fetch_works_from_venue(
            self, venue: Any, year_from: int, year_to: int, task_id: int, sub_task_id: int
        ) -> FetchProgress:
            p = FetchProgress(fetched=5)
            p.author_ids = {"A1", "A2", "A3"}
            return p

    executor = VenueSubTaskExecutor(test_session, work_fetcher=_StubFetcher())
    works = await executor.execute(task, sub_task, CollectionProgress(task_id=task.task_id))

    assert works == 5
    await test_session.refresh(sub_task)
    assert sub_task.status == "completed"
    assert sub_task.works_fetched == 5
    assert sub_task.authors_fetched == 3
    assert sub_task.new_authors == 2
