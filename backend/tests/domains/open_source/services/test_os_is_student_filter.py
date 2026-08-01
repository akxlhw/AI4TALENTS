"""Tests for the is_student filter on developer list/search queries."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.open_source.models.open_source import OSDeveloper
from app.domains.open_source.repositories.open_source import OpenSourceRepository
from app.domains.open_source.schemas.open_source import OSSearchFilters, OSSearchRequest


def _make_developer(
    github_login: str,
    github_id: int,
    is_student: bool,
) -> OSDeveloper:
    return OSDeveloper(
        github_login=github_login,
        github_id=github_id,
        name=github_login,
        total_stars_received=0,
        primary_languages=["Python"],
        tech_tags=["ai"],
        is_visible=True,
        is_student=is_student,
    )


async def _seed(test_session: AsyncSession) -> None:
    test_session.add_all(
        [
            _make_developer("stu1", 101, True),
            _make_developer("stu2", 102, True),
            _make_developer("pro1", 103, False),
        ]
    )
    await test_session.commit()


@pytest.mark.asyncio
async def test_list_developers_filter_is_student_true(test_session: AsyncSession) -> None:
    await _seed(test_session)
    repo = OpenSourceRepository(test_session)

    items, total = await repo.list_developers(filters={"is_student": True})

    assert total == 2
    assert {d.github_login for d in items} == {"stu1", "stu2"}


@pytest.mark.asyncio
async def test_list_developers_filter_is_student_false(test_session: AsyncSession) -> None:
    await _seed(test_session)
    repo = OpenSourceRepository(test_session)

    items, total = await repo.list_developers(filters={"is_student": False})

    assert total == 1
    assert [d.github_login for d in items] == ["pro1"]


@pytest.mark.asyncio
async def test_list_developers_no_filter_returns_all(test_session: AsyncSession) -> None:
    await _seed(test_session)
    repo = OpenSourceRepository(test_session)

    _items, total = await repo.list_developers()

    assert total == 3


@pytest.mark.asyncio
async def test_keyword_search_passes_is_student_filter(test_session: AsyncSession) -> None:
    """POST /search keyword path must honor filters.is_student."""
    await _seed(test_session)
    repo = OpenSourceRepository(test_session)

    req = OSSearchRequest(q="", mode="keyword", filters=OSSearchFilters(is_student=True))
    items, total = await repo.search_developers(req)

    assert total == 2
    assert {d.github_login for d in items} == {"stu1", "stu2"}


@pytest.mark.asyncio
async def test_keyword_search_is_student_false(test_session: AsyncSession) -> None:
    await _seed(test_session)
    repo = OpenSourceRepository(test_session)

    req = OSSearchRequest(q="", mode="keyword", filters=OSSearchFilters(is_student=False))
    _items, total = await repo.search_developers(req)

    assert total == 1
