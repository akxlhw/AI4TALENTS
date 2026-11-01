"""Talent detail endpoint: linkedin_search_url fallback injection."""

from __future__ import annotations

from urllib.parse import unquote_plus

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.academic.models.talent import Talent


async def _seed(session: AsyncSession, **overrides) -> Talent:
    defaults = dict(
        name="王伟",
        name_en="Wei Wang",
        role_type="professor",
        is_visible=True,
    )
    defaults.update(overrides)
    talent = Talent(**defaults)
    session.add(talent)
    await session.commit()
    return talent


@pytest.mark.asyncio
async def test_detail_contains_search_url_with_english_name(
    client: AsyncClient, test_session: AsyncSession
) -> None:
    talent = await _seed(test_session)
    r = await client.get(f"/api/v1/talents/{talent.talent_id}")
    assert r.status_code == 200
    url = r.json()["linkedin_search_url"]
    assert url.startswith("https://www.google.com/search?q=")
    q = unquote_plus(url.split("q=")[1])
    # English name preferred over Chinese; linkedin keyword present
    assert '"Wei Wang"' in q and "linkedin" in q
    assert "王伟" not in q


@pytest.mark.asyncio
async def test_falls_back_to_chinese_name_without_english(
    client: AsyncClient, test_session: AsyncSession
) -> None:
    talent = await _seed(test_session, name_en=None)
    r = await client.get(f"/api/v1/talents/{talent.talent_id}")
    q = unquote_plus(r.json()["linkedin_search_url"].split("q=")[1])
    assert '"王伟"' in q and "linkedin" in q
