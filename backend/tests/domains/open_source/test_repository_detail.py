"""Regression tests for repository detail tech_element type.

tech_element migrated to a JSON array (list[str]) in v2; the repository
detail response schema still declared `str`, so FastAPI response validation
raised ResponseValidationError (500) for any repo whose config carries a
list value. These tests pin the detail contract to list[str].
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.open_source.models.open_source import (
    OSDeveloper,
    OSRepoConfig,
    OSRepository,
)
from app.domains.open_source.schemas.open_source import OSRepositoryDetailResponse
from app.domains.open_source.services.open_source_service import OpenSourceService

FULL_NAME = "torvalds/linux"


async def _seed_repo(
    session: AsyncSession,
    tech_element: object = ...,
) -> None:
    owner = OSDeveloper(github_login="torvalds", name="torvalds", avatar_url="", tech_tags=[])
    session.add(owner)
    await session.flush()
    session.add(
        OSRepository(
            full_name=FULL_NAME,
            name="linux",
            developer_id=owner.developer_id,
            stars_count=100,
            forks_count=10,
        )
    )
    if tech_element is not ...:
        session.add(OSRepoConfig(repo_full_name=FULL_NAME, tech_element=tech_element))
    await session.flush()


@pytest.mark.asyncio
async def test_detail_tech_element_list_passes_validation(test_session: AsyncSession) -> None:
    """Config with list tech_element must survive response validation (was 500)."""
    await _seed_repo(test_session, tech_element=["systems", "ai"])
    detail = await OpenSourceService(test_session).get_repository_detail(FULL_NAME)
    validated = OSRepositoryDetailResponse.model_validate(detail)
    assert validated.tech_element == ["systems", "ai"]


@pytest.mark.asyncio
async def test_detail_normalizes_legacy_string_tech_element(
    test_session: AsyncSession,
) -> None:
    """Legacy scalar tech_element rows are normalized to a single-item list."""
    await _seed_repo(test_session, tech_element="systems")
    detail = await OpenSourceService(test_session).get_repository_detail(FULL_NAME)
    validated = OSRepositoryDetailResponse.model_validate(detail)
    assert validated.tech_element == ["systems"]


@pytest.mark.asyncio
async def test_detail_without_config_returns_empty_list(test_session: AsyncSession) -> None:
    """Repos without a config row fall back to an empty list, not a string."""
    await _seed_repo(test_session)
    detail = await OpenSourceService(test_session).get_repository_detail(FULL_NAME)
    validated = OSRepositoryDetailResponse.model_validate(detail)
    assert validated.tech_element == []
