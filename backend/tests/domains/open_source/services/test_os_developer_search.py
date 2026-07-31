"""Tests for open-source developer search (keyword path fix + hybrid RRF fusion).

Regression tests for:
1. POST /search keyword path silently ignoring the query (wrong field name
   ``query`` instead of ``q``) and dropping filters/sort_by.
2. Hybrid search naive merge with truncated ``total`` — now RRF fusion with
   ``total = max(keyword_total, semantic_total)``.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.open_source.models.open_source import OSDeveloper
from app.domains.open_source.repositories.open_source import OpenSourceRepository
from app.domains.open_source.schemas.open_source import OSSearchFilters, OSSearchRequest
from app.domains.open_source.services.open_source_embedding_service import (
    OpenSourceEmbeddingService,
)
from app.domains.open_source.services.os_developer_service import OSDeveloperService
from app.domains.shared.services.config_service import ConfigService


def _make_developer(
    github_login: str,
    github_id: int,
    name: str,
    stars: int = 0,
    company: str | None = None,
) -> OSDeveloper:
    return OSDeveloper(
        github_login=github_login,
        github_id=github_id,
        name=name,
        company=company,
        total_stars_received=stars,
        primary_languages=["Python"],
        tech_tags=["ai"],
        is_visible=True,
    )


async def _seed_developers(test_session: AsyncSession) -> list[OSDeveloper]:
    devs = [
        _make_developer("alice", 1, "Alice Zhang", stars=100, company="AliceCorp"),
        _make_developer("bob", 2, "Bob Li", stars=50, company="TestCorp"),
        _make_developer("carol", 3, "Carol Wang", stars=10, company="TestCorp"),
    ]
    test_session.add_all(devs)
    await test_session.commit()
    for dev in devs:
        await test_session.refresh(dev)
    return devs


@pytest.mark.asyncio
async def test_keyword_search_uses_q_field(test_session: AsyncSession) -> None:
    """OSSearchRequest.q must drive the keyword path (was read as 'query')."""
    await _seed_developers(test_session)
    repo = OpenSourceRepository(test_session)

    items, total = await repo.search_developers(OSSearchRequest(q="alice", mode="keyword"))

    assert total == 1
    assert [d.github_login for d in items] == ["alice"]


@pytest.mark.asyncio
async def test_keyword_search_passes_filters_and_sort(test_session: AsyncSession) -> None:
    """Keyword path must honor filters and sort_by like the GET list endpoint."""
    await _seed_developers(test_session)
    repo = OpenSourceRepository(test_session)

    req = OSSearchRequest(
        q="",
        mode="keyword",
        filters=OSSearchFilters(min_stars=20),
        sort_by="stars_asc",
    )
    items, total = await repo.search_developers(req)

    assert total == 2
    assert [d.github_login for d in items] == ["bob", "alice"]


@pytest.mark.asyncio
async def test_hybrid_falls_back_to_keyword_when_embedding_disabled(
    test_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Hybrid mode without embedding config degrades to a working keyword search."""
    await _seed_developers(test_session)

    async def _fake_llm_config(self):
        return SimpleNamespace(embedding_enabled=False, embedding_model=None)

    monkeypatch.setattr(ConfigService, "get_llm_config", _fake_llm_config)

    service = OSDeveloperService(test_session)
    items, total = await service.search_developers(OSSearchRequest(q="alice", mode="hybrid"))

    assert total == 1
    assert [d.github_login for d in items] == ["alice"]


@pytest.mark.asyncio
async def test_hybrid_rrf_fusion_orders_and_totals(
    test_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Hybrid mode fuses both legs via RRF and reports a non-truncated total."""
    devs = await _seed_developers(test_session)
    alice, bob, carol = devs

    async def _fake_llm_config(self):
        return SimpleNamespace(
            embedding_enabled=True,
            embedding_model="test-embed",
            api_key="key",
            api_base="http://localhost",
            model="test-chat",
            embedding_api_base=None,
            embedding_api_key=None,
            timeout=1,
            api_format=None,
            embedding_api_format=None,
            embedding_dimension=1536,
        )

    async def _fake_query_embedding(self, query: str) -> list[float]:
        return [0.1] * 1536

    semantic_total = 10

    async def _fake_vector_search(self, **kwargs):
        # Semantic leg: carol first, alice second (bob absent)
        return [carol, alice], semantic_total

    monkeypatch.setattr(ConfigService, "get_llm_config", _fake_llm_config)
    monkeypatch.setattr(OpenSourceEmbeddingService, "get_query_embedding", _fake_query_embedding)
    monkeypatch.setattr(OpenSourceRepository, "search_by_vector_similarity", _fake_vector_search)

    service = OSDeveloperService(test_session)
    req = OSSearchRequest(q="corp", mode="hybrid", page=1, page_size=20)
    items, total = await service.search_developers(req)

    # Keyword leg order (stars desc): alice, bob, carol.
    # Semantic leg order: carol, alice.
    # RRF (k=60): alice = 1/61 + 1/62 > carol = 1/61 + 1/63 > bob = 1/62.
    assert [d.github_login for d in items] == ["alice", "carol", "bob"]
    # total must not be truncated to the merged candidate count (3)
    assert total == semantic_total
