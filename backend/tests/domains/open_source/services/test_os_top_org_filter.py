"""Tests for the top_org filter on developer list/search queries.

来源知名企业/院校判定：company 字段命中词表（全球头部大厂 / 国内头部互联网 /
知名 AI 初创 / 知名院校），词元边界正则匹配。见 open_source/constants/top_orgs.py。
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
    company: str | None = None,
) -> OSDeveloper:
    return OSDeveloper(
        github_login=github_login,
        github_id=github_id,
        name=github_login,
        company=company,
        total_stars_received=0,
        primary_languages=["Python"],
        tech_tags=["ai"],
        is_visible=True,
    )


async def _seed(test_session: AsyncSession) -> None:
    test_session.add_all(
        [
            # 全球大厂
            _make_developer("google_dev", 401, "@Google"),
            _make_developer("msft_dev", 402, "Microsoft"),
            # 国内头部
            _make_developer("bytedance_dev", 403, "字节跳动"),
            _make_developer("tencent_dev", 404, "Tencent 腾讯"),
            # AI 初创
            _make_developer("openai_dev", 405, "OpenAI"),
            _make_developer("deepseek_dev", 406, "DeepSeek (深度求索)"),
            # 知名院校（GitHub 资料常把学校写进 company）
            _make_developer("tsinghua_dev", 407, "Tsinghua University"),
            _make_developer("mit_dev", 408, "MIT CSAIL"),
            _make_developer("pku_dev", 409, "北京大学"),
            # 不命中：普通公司 / 个人 / 无公司
            _make_developer("small_co", 410, "SomeSmallStartup Inc."),
            _make_developer("freelance", 411, "Freelance"),
            _make_developer("no_company", 412),
            # 不命中：词元边界保护（submit 不应误中 mit）
            _make_developer("submit_dev", 413, "submitHub"),
        ]
    )
    await test_session.commit()


_TOP_ORG_LOGINS = {
    "google_dev",
    "msft_dev",
    "bytedance_dev",
    "tencent_dev",
    "openai_dev",
    "deepseek_dev",
    "tsinghua_dev",
    "mit_dev",
    "pku_dev",
}


@pytest.mark.asyncio
async def test_list_developers_filter_top_org(test_session: AsyncSession) -> None:
    await _seed(test_session)
    repo = OpenSourceRepository(test_session)

    items, total = await repo.list_developers(filters={"top_org": True})

    assert total == len(_TOP_ORG_LOGINS)
    assert {d.github_login for d in items} == _TOP_ORG_LOGINS


@pytest.mark.asyncio
async def test_list_developers_no_top_org_filter_returns_all(test_session: AsyncSession) -> None:
    await _seed(test_session)
    repo = OpenSourceRepository(test_session)

    _items, total = await repo.list_developers()

    assert total == 13


@pytest.mark.asyncio
async def test_keyword_search_passes_top_org_filter(test_session: AsyncSession) -> None:
    """POST /search keyword path must honor filters.top_org."""
    await _seed(test_session)
    repo = OpenSourceRepository(test_session)

    req = OSSearchRequest(q="", mode="keyword", filters=OSSearchFilters(top_org=True))
    items, total = await repo.search_developers(req)

    assert total == len(_TOP_ORG_LOGINS)
    assert {d.github_login for d in items} == _TOP_ORG_LOGINS
