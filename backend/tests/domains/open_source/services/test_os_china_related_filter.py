"""Tests for the china_related filter on developer list/search queries.

中国背景判定（满足其一）：姓名含中文 / 姓名首末词元命中百家姓拼音 /
地区命中中国相关词。见 open_source/constants/china_markers.py。
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
    name: str,
    location: str | None = None,
) -> OSDeveloper:
    return OSDeveloper(
        github_login=github_login,
        github_id=github_id,
        name=name,
        location=location,
        total_stars_received=0,
        primary_languages=["Python"],
        tech_tags=["ai"],
        is_visible=True,
    )


async def _seed(test_session: AsyncSession) -> None:
    test_session.add_all(
        [
            # 地区命中
            _make_developer("loc_china", 301, "someone", location="Beijing, China"),
            _make_developer("loc_city", 302, "someone else", location="Hangzhou"),
            _make_developer("loc_zh", 303, "another", location="中国 上海"),
            # 百家姓命中（首词 / 末词）
            _make_developer("surname_first", 304, "Zhang Wei"),
            _make_developer("surname_last", 305, "Wei Zhang"),
            # 中文名命中
            _make_developer("cjk_name", 306, "张伟"),
            # 不命中：英文名 + 海外地区
            _make_developer("us_dev", 307, "John Smith", location="San Francisco, US"),
            # 不命中：单词登录名（无词元边界，姓氏规则不应误伤）
            _make_developer("mono", 308, "Li"),
            # 不命中：无姓名无地区
            _make_developer("ghost", 309, "ghost"),
        ]
    )
    await test_session.commit()


_CHINA_LOGINS = {
    "loc_china",
    "loc_city",
    "loc_zh",
    "surname_first",
    "surname_last",
    "cjk_name",
}


@pytest.mark.asyncio
async def test_list_developers_filter_china_related(test_session: AsyncSession) -> None:
    await _seed(test_session)
    repo = OpenSourceRepository(test_session)

    items, total = await repo.list_developers(filters={"china_related": True})

    assert total == len(_CHINA_LOGINS)
    assert {d.github_login for d in items} == _CHINA_LOGINS


@pytest.mark.asyncio
async def test_list_developers_no_china_filter_returns_all(test_session: AsyncSession) -> None:
    await _seed(test_session)
    repo = OpenSourceRepository(test_session)

    _items, total = await repo.list_developers()

    assert total == 9


@pytest.mark.asyncio
async def test_keyword_search_passes_china_related_filter(test_session: AsyncSession) -> None:
    """POST /search keyword path must honor filters.china_related."""
    await _seed(test_session)
    repo = OpenSourceRepository(test_session)

    req = OSSearchRequest(q="", mode="keyword", filters=OSSearchFilters(china_related=True))
    items, total = await repo.search_developers(req)

    assert total == len(_CHINA_LOGINS)
    assert {d.github_login for d in items} == _CHINA_LOGINS
