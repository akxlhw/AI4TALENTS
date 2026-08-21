"""OR-semantics tests for the tech element filter in OS talent search.

Bug: selecting multiple tech elements required a developer to be tagged
with ALL of them (jsonb @> containment = AND), so "models + security"
returned only developers tagged with both. Expected: any-of (OR), the
same semantics as the languages filter (?|).
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.open_source.models.open_source import OSDeveloper
from app.domains.open_source.repositories.open_source import OpenSourceRepository


async def _seed(session: AsyncSession) -> dict[str, int]:
    devs = [
        OSDeveloper(github_login="alice", github_id=1, tech_tags=["models"], is_visible=True),
        OSDeveloper(github_login="bob", github_id=2, tech_tags=["security"], is_visible=True),
        OSDeveloper(
            github_login="carol",
            github_id=3,
            tech_tags=["models", "security"],
            is_visible=True,
        ),
        OSDeveloper(github_login="dave", github_id=4, tech_tags=["robotics"], is_visible=True),
    ]
    session.add_all(devs)
    await session.commit()
    return {d.github_login: d.developer_id for d in devs}


@pytest.mark.asyncio
async def test_multi_element_filter_is_any_of(test_session: AsyncSession) -> None:
    """Keyword/list path: filtering by [models, security] returns devs
    tagged with ANY of the two — not only those tagged with both."""
    await _seed(test_session)
    repo = OpenSourceRepository(test_session)

    items, total = await repo.list_developers(
        filters={"tech_elements": ["models", "security"]}, page_size=50
    )

    assert {d.github_login for d in items} == {"alice", "bob", "carol"}
    assert total == 3


@pytest.mark.asyncio
async def test_single_element_filter_still_works(test_session: AsyncSession) -> None:
    await _seed(test_session)
    repo = OpenSourceRepository(test_session)

    items, _ = await repo.list_developers(filters={"tech_elements": ["models"]}, page_size=50)

    assert {d.github_login for d in items} == {"alice", "carol"}


@pytest.mark.asyncio
@pytest.mark.requires_pgvector
async def test_vector_search_multi_element_filter_is_any_of(
    test_session: AsyncSession,
) -> None:
    """The semantic-search path shares the same OR semantics."""
    ids = await _seed(test_session)
    repo = OpenSourceRepository(test_session)
    vec = [0.1] * 1536  # column is vector(1536)
    for login, dev_id in ids.items():
        await repo.upsert_embedding(dev_id, vec, "test-model", f"hash-{login}")
    await test_session.commit()

    devs, total = await repo.search_by_vector_similarity(
        query_embedding=vec,
        similarity_threshold=0.0,
        filters={"tech_elements": ["models", "security"]},
        limit=50,
    )

    assert {d.github_login for d in devs} == {"alice", "bob", "carol"}
    assert total == 3
