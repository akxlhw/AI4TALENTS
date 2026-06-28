"""Integration tests for LWSiteRepository (uses talent_db_test)."""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.domains.lab_web.models.lab_web import LWLabRegistry
from app.domains.lab_web.models.lab_web_site import LWSiteConfig
from app.domains.lab_web.repositories.lab_web.site import LWSiteRepository

pytestmark = pytest.mark.integration


@pytest.fixture
async def sample_lab(test_session):
    """The test DB doesn't run migration seeds, so create the parent lab explicitly."""
    lab = LWLabRegistry(
        lab_code="stanford_sail",
        lab_name="Stanford AI Lab",
        institution="Stanford University",
        country="US",
        people_url="https://ai.stanford.edu/faculty/",
        fetch_mode="static",
        is_active=True,
    )
    test_session.add(lab)
    await test_session.commit()
    await test_session.refresh(lab)
    return lab


@pytest.fixture
async def sample_site(test_session, sample_lab):
    site = LWSiteConfig(
        site_code="test_site",
        site_name="Test Site",
        parent_lab_code="stanford_sail",
        people_url="https://example.test/people/",
        fetch_mode="static",
        is_active=True,
    )
    test_session.add(site)
    await test_session.commit()
    await test_session.refresh(site)
    return site


async def test_site_crud(test_session, sample_site):
    repo = LWSiteRepository(test_session)
    fetched = await repo.get_site_by_code("test_site")
    assert fetched is not None
    assert fetched.site_id == sample_site.site_id

    sites = await repo.list_sites(only_active=True)
    assert any(s.site_code == "test_site" for s in sites)


async def test_find_cached_page_hit(test_session, sample_site):
    repo = LWSiteRepository(test_session)
    await repo.insert_raw_page(
        site_code="test_site",
        people_url="https://example.test/people/",
        html_content="<html>x</html>",
        html_hash="hash123",
        parsed_persons=[{"name": "Alice"}],
        parse_status="parsed",
        llm_model="test-model",
        llm_tokens_used=10,
    )
    cached = await repo.find_cached_page("test_site", "hash123")
    assert cached is not None
    assert cached.parse_status == "parsed"
    assert cached.parsed_persons == [{"name": "Alice"}]


async def test_find_cached_page_miss_on_different_hash(test_session, sample_site):
    repo = LWSiteRepository(test_session)
    await repo.insert_raw_page(
        site_code="test_site",
        people_url="https://example.test/people/",
        html_content="<html>x</html>",
        html_hash="hash123",
        parsed_persons=[],
        parse_status="parsed",
    )
    assert await repo.find_cached_page("test_site", "different_hash") is None


async def test_find_cached_page_miss_on_non_parsed_status(test_session, sample_site):
    repo = LWSiteRepository(test_session)
    await repo.insert_raw_page(
        site_code="test_site",
        people_url="https://example.test/people/",
        html_content="<html>x</html>",
        html_hash="hash123",
        parse_status="needs_review",
    )
    # Same hash but not 'parsed' status -> cache miss (must reparse).
    assert await repo.find_cached_page("test_site", "hash123") is None


async def test_upsert_raw_persons_dedups_and_resolves_lab_id(test_session, sample_site):
    """Repository converts parsed persons to lw_raw_person rows, resolving lab_id via parent_lab_code."""
    repo = LWSiteRepository(test_session)
    drafts = [
        {"name": "Alice Lee", "role_section": "PhD Students", "homepage": "https://alice.example"},
        {"name": "Bob", "role_section": "Faculty"},
    ]
    rows = await repo.upsert_site_raw_persons(
        site_code="test_site",
        parent_lab_code="stanford_sail",
        parsed_persons=drafts,
        task_id=1,
    )
    assert len(rows) == 2
    names = {r.name_raw for r in rows}
    assert names == {"Alice Lee", "Bob"}
    # lab_id must be resolved to the real stanford_sail lab_id (not a sentinel).
    sail = (
        await test_session.execute(
            select(LWLabRegistry).where(LWLabRegistry.lab_code == "stanford_sail")
        )
    ).scalar_one()
    assert all(r.lab_id == sail.lab_id for r in rows)
    # role_section stored in raw_data
    assert rows[0].raw_data["role_section"] == "PhD Students"
    assert rows[0].raw_data["site_code"] == "test_site"
