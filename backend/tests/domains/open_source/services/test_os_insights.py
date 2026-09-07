"""Tests for OS developer search insights aggregation (repo layer)."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.open_source.models.open_source import (
    OSContribution,
    OSDeveloper,
    OSRepoConfig,
    OSRepository,
)
from app.domains.open_source.repositories.open_source import OpenSourceRepository


def _dev(
    github_login: str,
    github_id: int,
    *,
    name: str | None = None,
    company: str | None = None,
    tech_tags: list[str] | None = None,
    email: str | None = None,
) -> OSDeveloper:
    return OSDeveloper(
        github_login=github_login,
        github_id=github_id,
        name=name or github_login,
        company=company,
        tech_tags=tech_tags or ["ai"],
        primary_languages=["Python"],
        total_stars_received=0,
        email=email,
        is_visible=True,
    )


async def _seed(test_session: AsyncSession) -> None:
    test_session.add(
        OSRepoConfig(repo_config_id=1, repo_full_name="pytorch/pytorch", tech_element=["ai"])
    )
    devs = [
        _dev("d1", 501, company="Google", tech_tags=["ai", "systems"], email="a@b.com"),
        _dev("d2", 502, company="Google", tech_tags=["ai"]),
        _dev("d3", 503, company="SomeSmallCo", tech_tags=["robotics"], email="c@d.com"),
    ]
    test_session.add_all(devs)
    await test_session.flush()
    dev_ids = {d.github_login: d.developer_id for d in devs}
    repo = OSRepository(developer_id=dev_ids["d1"], full_name="pytorch/pytorch", name="pytorch")
    test_session.add(repo)
    await test_session.flush()
    # d1、d2 对 pytorch/pytorch 有贡献；d3 没有
    test_session.add_all(
        [
            OSContribution(developer_id=dev_ids["d1"], repo_id=repo.repo_id, commits_count=10),
            OSContribution(developer_id=dev_ids["d2"], repo_id=repo.repo_id, commits_count=5),
        ]
    )
    await test_session.commit()


@pytest.mark.asyncio
async def test_insights_distributions(test_session: AsyncSession) -> None:
    await _seed(test_session)
    repo = OpenSourceRepository(test_session)

    result = await repo.get_developer_insights({})

    assert result["total"] == 3
    assert result["contactable"] == 2  # d1、d3 有 email
    assert result["tech_element_distribution"] == {"ai": 2, "robotics": 1, "systems": 1}
    assert result["repo_distribution"] == [
        {"repo_full_name": "pytorch/pytorch", "developer_count": 2}
    ]
    assert result["company_distribution"] == {"Google": 2, "SomeSmallCo": 1}


@pytest.mark.asyncio
async def test_insights_follow_filters(test_session: AsyncSession) -> None:
    await _seed(test_session)
    repo = OpenSourceRepository(test_session)

    result = await repo.get_developer_insights({"company": "Google"})

    assert result["total"] == 2
    assert result["contactable"] == 1
    assert result["company_distribution"] == {"Google": 2}
    assert result["repo_distribution"][0]["developer_count"] == 2
