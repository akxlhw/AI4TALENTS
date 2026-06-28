"""Unit test for BaseLabCollector.collect() end-to-end with a fake fetcher."""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.domains.academic.models.talent import Talent
from app.domains.lab_web.models.lab_web import LWRawPerson
from app.domains.lab_web.repositories.lab_web import LWRepository
from app.domains.lab_web.services.collectors.base_collector import (
    BaseLabCollector,
    CollectContext,
    RawPersonDraft,
)
from app.domains.lab_web.services.lw_person_service import LWPersonService
from app.domains.shared.models.enums import SourceType

pytestmark = pytest.mark.integration


class _FakeResponse:
    def __init__(self, html: str) -> None:
        self.html = html


class _FakeFetcher:
    """Returns a canned response; robots check always allows."""

    robots_disallows: set[str] = set()

    def __init__(self, html: str) -> None:
        self.html = html

    async def fetch(self, url: str) -> _FakeResponse:
        return _FakeResponse(self.html)

    async def is_allowed_by_robots(self, url: str) -> bool:
        return True


class _DummyCollector(BaseLabCollector):
    """A collector whose hooks yield one person from any response."""

    lab_code = "test_lab"
    max_pages = 1

    def parse_person_cards(self, response):
        return [response]  # one card = the whole response

    def extract_person(self, card):
        return RawPersonDraft(
            name_raw="Fake Person",
            title_raw="Assistant Professor",
            email_raw="fake@test.edu",
        )


async def test_collect_writes_raw_and_syncs_core_talent(test_session, sample_lab):
    repo = LWRepository(test_session)
    person_service = LWPersonService(test_session)
    task = await repo.create_task(task_name="t1", lab_id=sample_lab.lab_id, status="running")

    fetcher = _FakeFetcher(html="<html></html>")
    collector = _DummyCollector(
        fetcher=fetcher, lab=sample_lab, repo=repo, person_service=person_service
    )
    ctx = CollectContext(task_id=task.task_id, lab_id=sample_lab.lab_id)

    await collector.collect(ctx)

    raw_rows = (await test_session.execute(select(LWRawPerson))).scalars().all()
    assert len(raw_rows) == 1
    assert raw_rows[0].name_raw == "Fake Person"

    talents = (
        await test_session.execute(
            select(Talent).where(Talent.source_type == SourceType.LAB_WEB.value)
        )
    ).scalars().all()
    assert len(talents) == 1
    assert talents[0].name == "Fake Person"

    refreshed = await repo.get_task(task.task_id)
    # Base flow leaves total_records set; status flip to success happens in
    # LWCollectionService._run_collection (not in collect() itself).
    assert refreshed.total_records == 1


class _DisallowingFetcher:
    """Fake fetcher whose robots check always disallows (for guard test)."""

    robots_disallows: set[str] = set()

    async def is_allowed_by_robots(self, url: str) -> bool:
        return False

    async def fetch(self, url: str):  # never reached — guard raises first
        raise AssertionError("fetch should not be called when robots disallows")


class _NoopCollector(BaseLabCollector):
    """Collector that yields nothing; only the guard matters here."""

    def parse_person_cards(self, response):
        return []

    def extract_person(self, card):
        raise AssertionError("no cards expected")


async def test_guard_robots_txt_blocks_disallowed_people_url(test_session, sample_lab):
    """M6 / spec §10.9: a people_url disallowed by robots.txt must abort the
    collection with PermissionError BEFORE any content fetch occurs.
    """
    repo = LWRepository(test_session)
    person_service = LWPersonService(test_session)
    task = await repo.create_task(task_name="t1", lab_id=sample_lab.lab_id, status="running")
    collector = _NoopCollector(
        fetcher=_DisallowingFetcher(),
        lab=sample_lab,
        repo=repo,
        person_service=person_service,
    )
    ctx = CollectContext(task_id=int(task.task_id), lab_id=sample_lab.lab_id)

    with pytest.raises(PermissionError, match="robots.txt"):
        await collector.collect(ctx)

    # Nothing was scraped: no raw rows, task untouched by the collector flow.
    raw_rows = (await test_session.execute(select(LWRawPerson))).scalars().all()
    assert raw_rows == []
