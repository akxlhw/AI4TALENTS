"""Unit tests for BaseLabSiteCollector end-to-end (mock fetcher + mock LLM)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select

from app.domains.academic.models.talent import Talent
from app.domains.lab_web.models.lab_web import LWCollectTask, LWRawPerson
from app.domains.lab_web.models.lab_web_site import LWSiteConfig
from app.domains.lab_web.repositories.lab_web.site import LWSiteRepository
from app.domains.lab_web.services.collectors.base_site_collector import (
    BaseLabSiteCollector,
    SiteCollectContext,
)
from app.domains.lab_web.services.lw_site_person_service import LWSitePersonService
from app.domains.shared.models.enums import SourceType

pytestmark = pytest.mark.integration


class _FakeFetcher:
    robots_disallows: set = set()

    def __init__(self, html: str) -> None:
        self.html = html

    async def is_allowed_by_robots(self, url: str) -> bool:
        return True

    async def fetch(self, url: str) -> str:
        return self.html


def _mock_llm_gateway(persons_json: str):
    gw = MagicMock()
    gw.complete = AsyncMock(return_value=MagicMock(content=persons_json, tokens_used=10))
    gw.model = "test-model"
    return gw


async def _make_task(test_session, sample_lab):
    t = LWCollectTask(task_name="t1", lab_id=sample_lab.lab_id, status="running")
    test_session.add(t)
    await test_session.commit()
    return int(t.task_id)


async def test_collect_writes_raw_and_syncs_core_talent(test_session, sample_lab):
    repo = LWSiteRepository(test_session)
    person_service = LWSitePersonService(test_session)
    site = LWSiteConfig(
        site_code="test_site",
        site_name="Test Site",
        parent_lab_code="test_lab",  # matches conftest sample_lab.lab_code
        people_url="https://example.test/people/",
    )
    test_session.add(site)
    await test_session.commit()

    fetcher = _FakeFetcher("<body><div>Faculty: Alice</div></body>")
    llm = _mock_llm_gateway(
        '[{"name": "Alice Lee", "role_section": "PhD Students", "homepage": "https://alice.example"}]'
    )
    collector = BaseLabSiteCollector(
        fetcher=fetcher, site=site, repo=repo, person_service=person_service, llm_gateway=llm
    )
    task_id = await _make_task(test_session, sample_lab)
    ctx = SiteCollectContext(task_id=task_id, site_code="test_site")
    await collector.collect(ctx)

    # raw persons written
    raw = (await test_session.execute(select(LWRawPerson))).scalars().all()
    assert len(raw) == 1
    assert raw[0].name_raw == "Alice Lee"
    # core_talent written with lab_web_site source + STUDENT role
    talents = (
        await test_session.execute(
            select(Talent).where(Talent.source_type == SourceType.LAB_WEB_SITE.value)
        )
    ).scalars().all()
    assert len(talents) == 1
    assert talents[0].name == "Alice Lee"


async def test_collect_uses_cache_on_html_hash_hit(test_session, sample_lab):
    """When a parsed cached page exists for the same html_hash, LLM is NOT called."""
    import hashlib as _hashlib

    repo = LWSiteRepository(test_session)
    person_service = LWSitePersonService(test_session)
    site = LWSiteConfig(
        site_code="cache_site",
        site_name="Cache Site",
        parent_lab_code="test_lab",
        people_url="https://example.test/people/",
    )
    test_session.add(site)
    await test_session.commit()

    html = "<body>cached page</body>"
    html_hash = _hashlib.sha256(html.encode()).hexdigest()
    await repo.insert_raw_page(
        site_code="cache_site",
        people_url="https://example.test/people/",
        html_content=html,
        html_hash=html_hash,
        parsed_persons=[{"name": "Cached Person", "role_section": "Faculty"}],
        parse_status="parsed",
        llm_model="prev-model",
    )

    fetcher = _FakeFetcher(html)
    llm = _mock_llm_gateway('[{"name": "SHOULD NOT BE USED"}]')
    collector = BaseLabSiteCollector(
        fetcher=fetcher, site=site, repo=repo, person_service=person_service, llm_gateway=llm
    )
    task_id = await _make_task(test_session, sample_lab)
    ctx = SiteCollectContext(task_id=task_id, site_code="cache_site")
    await collector.collect(ctx)

    llm.complete.assert_not_awaited()  # cache hit -> no LLM call
    talents = (
        await test_session.execute(
            select(Talent).where(Talent.source_type == SourceType.LAB_WEB_SITE.value)
        )
    ).scalars().all()
    assert len(talents) == 1
    assert talents[0].name == "Cached Person"


async def test_collect_needs_review_on_empty_parse(test_session, sample_lab):
    """LLM returning 0 persons -> needs_review, no core_talent written."""
    repo = LWSiteRepository(test_session)
    person_service = LWSitePersonService(test_session)
    site = LWSiteConfig(
        site_code="empty_site",
        site_name="Empty Site",
        parent_lab_code="test_lab",
        people_url="https://example.test/people/",
    )
    test_session.add(site)
    await test_session.commit()
    fetcher = _FakeFetcher("<body>nobody here</body>")
    llm = _mock_llm_gateway("[]")
    collector = BaseLabSiteCollector(
        fetcher=fetcher, site=site, repo=repo, person_service=person_service, llm_gateway=llm
    )
    task_id = await _make_task(test_session, sample_lab)
    ctx = SiteCollectContext(task_id=task_id, site_code="empty_site")
    await collector.collect(ctx)

    talents = (
        await test_session.execute(
            select(Talent).where(Talent.source_type == SourceType.LAB_WEB_SITE.value)
        )
    ).scalars().all()
    assert len(talents) == 0  # needs_review -> nothing synced
