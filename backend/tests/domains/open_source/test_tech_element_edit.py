"""Tests for multi-value repo tech_element and developer tech_tags sync.

Covers: editing a repo's tech_element (now a JSON array) recalculates
affected developers' tech_tags as the union across ALL their configured
repos (not just the edited one).
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.open_source.models.open_source import (
    OSContribution,
    OSDeveloper,
    OSRepoConfig,
    OSRepository,
)
from app.domains.open_source.services.os_collection_service import (
    OSCollectionService,
    parse_repo_input,
)


async def _add_repo_config(
    session: AsyncSession, full_name: str, elements: list[str]
) -> OSRepoConfig:
    config = OSRepoConfig(repo_full_name=full_name, tech_element=elements)
    session.add(config)
    await session.flush()
    return config


async def _add_developer(session: AsyncSession, login: str) -> OSDeveloper:
    dev = OSDeveloper(github_login=login, name=login, avatar_url="", tech_tags=[])
    session.add(dev)
    await session.flush()
    return dev


async def _add_repository(session: AsyncSession, full_name: str, owner_id: int) -> OSRepository:
    repo = OSRepository(
        full_name=full_name,
        name=full_name.split("/")[-1],
        developer_id=owner_id,
        stars_count=0,
    )
    session.add(repo)
    await session.flush()
    return repo


async def _link(session: AsyncSession, developer_id: int, repo_id: int) -> None:
    session.add(
        OSContribution(
            developer_id=developer_id,
            repo_id=repo_id,
            commits_count=1,
            prs_count=0,
            issues_count=0,
        )
    )
    await session.flush()


# ============ parse_repo_input ============


def test_parse_repo_input_url() -> None:
    assert parse_repo_input("https://github.com/openai/whisper") == "openai/whisper"


def test_parse_repo_input_url_git_suffix() -> None:
    assert parse_repo_input("https://github.com/openai/whisper.git") == "openai/whisper"


def test_parse_repo_input_url_tree_path() -> None:
    assert parse_repo_input("https://github.com/openai/whisper/tree/main") == "openai/whisper"


def test_parse_repo_input_plain() -> None:
    assert parse_repo_input("microsoft/DeepSpeed") == "microsoft/DeepSpeed"


def test_parse_repo_input_invalid() -> None:
    assert parse_repo_input("not a repo") is None
    assert parse_repo_input("") is None


# ============ tech_element validation ============


@pytest.mark.asyncio
async def test_update_repo_tech_element_multiple(test_session: AsyncSession) -> None:
    """Editing a repo's tech_element to multiple values succeeds."""
    service = OSCollectionService(test_session)
    config = await service.create_repo_config("org/test-repo", "models")

    updated = await service.update_repo_config(
        config.repo_config_id, {"tech_element": ["models", "training"]}
    )
    assert updated is not None
    assert sorted(updated.tech_element) == ["models", "training"]


@pytest.mark.asyncio
async def test_invalid_tech_element_rejected(test_session: AsyncSession) -> None:
    """Invalid tech_element codes raise BadRequestError."""
    from app.core.exceptions import BadRequestError

    service = OSCollectionService(test_session)
    config = await service.create_repo_config("org/invalid-test", "models")

    with pytest.raises(BadRequestError):
        await service.update_repo_config(config.repo_config_id, {"tech_element": ["ai", "bogus"]})


# ============ developer tech_tags sync (union semantics) ============


@pytest.mark.asyncio
async def test_sync_exclusive_developer(test_session: AsyncSession) -> None:
    """Developer linked to only one repo: tags = that repo's new elements."""
    service = OSCollectionService(test_session)

    # Setup: repo A (ai), developer contributes to A only
    await _add_repo_config(test_session, "org/repo-a", ["models"])
    dev = await _add_developer(test_session, "solo-dev")
    repo_a = await _add_repository(test_session, "org/repo-a", dev.developer_id)
    await _link(test_session, dev.developer_id, repo_a.repo_id)
    await test_session.commit()

    # Edit: repo A tech_element → [ai, security]
    config = await service.repo.get_repo_config_by_full_name("org/repo-a")
    await service.update_repo_config(config.repo_config_id, {"tech_element": ["models", "sys_sec"]})
    await test_session.commit()

    # Verify developer tags = [ai, security]
    await test_session.refresh(dev)
    assert sorted(dev.tech_tags) == ["models", "sys_sec"]


@pytest.mark.asyncio
async def test_sync_developer_tags_union(test_session: AsyncSession) -> None:
    """Developer contributes to 2 configured repos: tags = union of both."""
    service = OSCollectionService(test_session)

    # Setup: dev owns repo-a, contributes to repo-b
    await _add_repo_config(test_session, "org/repo-a", ["models"])
    await _add_repo_config(test_session, "org/repo-b", ["cloud_native"])
    dev = await _add_developer(test_session, "multi-dev")
    repo_a = await _add_repository(test_session, "org/repo-a", dev.developer_id)
    other = await _add_developer(test_session, "other-owner")
    repo_b = await _add_repository(test_session, "org/repo-b", other.developer_id)
    await _link(test_session, dev.developer_id, repo_a.repo_id)
    await _link(test_session, dev.developer_id, repo_b.repo_id)
    await test_session.commit()

    # Edit repo-a: [ai] → [ai, data_science]
    config_a = await service.repo.get_repo_config_by_full_name("org/repo-a")
    await service.update_repo_config(
        config_a.repo_config_id, {"tech_element": ["models", "training"]}
    )
    await test_session.commit()

    # dev tags should be union: {ai, data_science} ∪ {systems}
    await test_session.refresh(dev)
    assert sorted(dev.tech_tags) == ["cloud_native", "models", "training"]


@pytest.mark.asyncio
async def test_unconfigured_repo_not_counted(test_session: AsyncSession) -> None:
    """Contributions to repos WITHOUT a config don't count in the union."""
    service = OSCollectionService(test_session)

    # Only repo-a is configured; repo-unconfigured has no config row
    await _add_repo_config(test_session, "org/repo-a", ["models"])
    dev = await _add_developer(test_session, "pick-dev")
    repo_a = await _add_repository(test_session, "org/repo-a", dev.developer_id)
    other = await _add_developer(test_session, "uc-owner")
    repo_uc = await _add_repository(test_session, "org/repo-unconfigured", other.developer_id)
    await _link(test_session, dev.developer_id, repo_a.repo_id)
    await _link(test_session, dev.developer_id, repo_uc.repo_id)
    await test_session.commit()

    # Trigger sync via edit
    config_a = await service.repo.get_repo_config_by_full_name("org/repo-a")
    await service.update_repo_config(config_a.repo_config_id, {"tech_element": ["sys_sec"]})
    await test_session.commit()

    # dev tags = only configured repo's element (unconfigured ignored)
    await test_session.refresh(dev)
    assert dev.tech_tags == ["sys_sec"]


@pytest.mark.asyncio
async def test_batch_update_tech_element(test_session: AsyncSession) -> None:
    """Batch update sets the same elements on multiple repos and syncs tags."""
    service = OSCollectionService(test_session)

    # Two repos, one shared developer contributing to both
    await _add_repo_config(test_session, "org/batch-a", ["models"])
    await _add_repo_config(test_session, "org/batch-b", ["cloud_native"])
    dev = await _add_developer(test_session, "batch-dev")
    repo_a = await _add_repository(test_session, "org/batch-a", dev.developer_id)
    other = await _add_developer(test_session, "batch-other")
    repo_b = await _add_repository(test_session, "org/batch-b", other.developer_id)
    await _link(test_session, dev.developer_id, repo_a.repo_id)
    await _link(test_session, dev.developer_id, repo_b.repo_id)
    await test_session.commit()

    config_a = await service.repo.get_repo_config_by_full_name("org/batch-a")
    config_b = await service.repo.get_repo_config_by_full_name("org/batch-b")

    # Batch update both repos to [robotics, security]
    result = await service.batch_update_tech_element(
        [config_a.repo_config_id, config_b.repo_config_id], ["robot_control", "sec_ops"]
    )
    await test_session.commit()

    assert result["updated"] == 2
    assert result["failed"] == []

    # Both configs now carry the same elements
    await test_session.refresh(config_a)
    await test_session.refresh(config_b)
    assert sorted(config_a.tech_element) == ["robot_control", "sec_ops"]
    assert sorted(config_b.tech_element) == ["robot_control", "sec_ops"]

    # Shared developer's tags = union = same set (both repos identical now)
    await test_session.refresh(dev)
    assert sorted(dev.tech_tags) == ["robot_control", "sec_ops"]


@pytest.mark.asyncio
async def test_batch_update_nonexistent_id_goes_to_failed(
    test_session: AsyncSession,
) -> None:
    """A nonexistent repo_config_id lands in failed, not fatal."""
    service = OSCollectionService(test_session)
    config = await service.create_repo_config("org/real-one", ["models"])
    await test_session.commit()

    result = await service.batch_update_tech_element([config.repo_config_id, 999999], ["sys_sec"])
    await test_session.commit()

    assert result["updated"] == 1
    assert len(result["failed"]) == 1
    assert result["failed"][0]["repo_input"] == "999999"
