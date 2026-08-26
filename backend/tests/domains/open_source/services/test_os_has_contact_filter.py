"""Tests for the has_contact filter on developer list/search queries.

有效联系方式判定：个人主页（blog_url）、个人邮箱（email）、
社交媒体链接（social_links）三者至少其一；空字符串与空 JSON 对象视为无效。
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.open_source.models.open_source import OSDeveloper
from app.domains.open_source.repositories.open_source import OpenSourceRepository
from app.domains.open_source.schemas.open_source import OSSearchFilters, OSSearchRequest


def _make_developer(
    github_login: str,
    github_id: int,
    blog_url: str | None = None,
    email: str | None = None,
    social_links: dict[str, str] | None = None,
) -> OSDeveloper:
    return OSDeveloper(
        github_login=github_login,
        github_id=github_id,
        name=github_login,
        total_stars_received=0,
        primary_languages=["Python"],
        tech_tags=["ai"],
        is_visible=True,
        blog_url=blog_url,
        email=email,
        social_links=social_links,
    )


async def _seed(test_session: AsyncSession) -> None:
    test_session.add_all(
        [
            _make_developer("blog_dev", 201, blog_url="https://blog.example.com"),
            _make_developer("email_dev", 202, email="dev@example.com"),
            _make_developer("social_dev", 203, social_links={"twitter": "https://x.com/dev"}),
            # 显式 None：social_links 会落库为 JSON 'null'
            _make_developer("json_null_dev", 204),
            # 空字符串 / 空 JSON 对象，均视为无效联系方式
            _make_developer("empty_contact_dev", 205, blog_url="", email="", social_links={}),
            # 字段未赋值：落库为 SQL NULL
            OSDeveloper(
                github_login="sql_null_dev",
                github_id=206,
                name="sql_null_dev",
                total_stars_received=0,
                primary_languages=["Python"],
                tech_tags=["ai"],
                is_visible=True,
            ),
        ]
    )
    await test_session.commit()


_NO_CONTACT_LOGINS = {"json_null_dev", "empty_contact_dev", "sql_null_dev"}


@pytest.mark.asyncio
async def test_list_developers_filter_has_contact_true(test_session: AsyncSession) -> None:
    await _seed(test_session)
    repo = OpenSourceRepository(test_session)

    items, total = await repo.list_developers(filters={"has_contact": True})

    assert total == 3
    assert {d.github_login for d in items} == {"blog_dev", "email_dev", "social_dev"}


@pytest.mark.asyncio
async def test_list_developers_filter_has_contact_false(test_session: AsyncSession) -> None:
    await _seed(test_session)
    repo = OpenSourceRepository(test_session)

    items, total = await repo.list_developers(filters={"has_contact": False})

    assert total == 3
    assert {d.github_login for d in items} == _NO_CONTACT_LOGINS


@pytest.mark.asyncio
async def test_list_developers_no_contact_filter_returns_all(test_session: AsyncSession) -> None:
    await _seed(test_session)
    repo = OpenSourceRepository(test_session)

    _items, total = await repo.list_developers()

    assert total == 6


@pytest.mark.asyncio
async def test_keyword_search_passes_has_contact_filter(test_session: AsyncSession) -> None:
    """POST /search keyword path must honor filters.has_contact."""
    await _seed(test_session)
    repo = OpenSourceRepository(test_session)

    req = OSSearchRequest(q="", mode="keyword", filters=OSSearchFilters(has_contact=True))
    items, total = await repo.search_developers(req)

    assert total == 3
    assert {d.github_login for d in items} == {"blog_dev", "email_dev", "social_dev"}


@pytest.mark.asyncio
async def test_keyword_search_has_contact_false(test_session: AsyncSession) -> None:
    await _seed(test_session)
    repo = OpenSourceRepository(test_session)

    req = OSSearchRequest(q="", mode="keyword", filters=OSSearchFilters(has_contact=False))
    _items, total = await repo.search_developers(req)

    assert total == 3
