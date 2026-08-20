"""Tests that re-collection preserves multi-repo union tech_tags.

Bug: the collector writes tech_tags = [this repo's element] during
contributor upserts (a single-repo snapshot). A developer contributing to
configured repos A and B lost B's element whenever A was re-collected
(and vice versa), because nothing recomputed the union after collection.
Fix: after collector.collect() returns, the task mixin recomputes the
union for every developer involved with the repo.
"""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.domains.open_source.services.collectors.github_collector as gc_mod
from app.core.database import AsyncSessionLocal
from app.domains.open_source.models.open_source import (
    OSCollectTask,
    OSContribution,
    OSDeveloper,
    OSRepoConfig,
    OSRepository,
)
from app.domains.open_source.services.os_collection_service import OSCollectionService
from app.domains.open_source.services.os_tech_tag_sync_mixin import TechTagSyncMixin


async def _seed_union_scenario(session: AsyncSession) -> None:
    """bob contributes to configured repos a/repo (models) and b/repo
    (security). His tags reflect the union established by b's config edit."""
    session.add(OSRepoConfig(repo_full_name="a/repo", tech_element=["models"]))
    session.add(OSRepoConfig(repo_full_name="b/repo", tech_element=["security"]))

    bob = OSDeveloper(github_login="bob", github_id=1, tech_tags=["security"])
    session.add(bob)
    await session.flush()

    repo_b = OSRepository(full_name="b/repo", name="repo", developer_id=bob.developer_id)
    session.add(repo_b)
    await session.flush()
    session.add(OSContribution(developer_id=bob.developer_id, repo_id=repo_b.repo_id))
    await session.commit()


def _install_stub_collector(monkeypatch: pytest.MonkeyPatch, task_id: int) -> None:
    """Replace the real collector with one that mimics its side effects:
    upsert bob with THIS repo's element only (the clobber), create his
    contribution to a/repo, and mark the task completed."""

    async def _stub_collect(self: Any, ctx: Any) -> None:  # noqa: ANN001
        async with AsyncSessionLocal() as s:
            bob = await s.scalar(select(OSDeveloper).where(OSDeveloper.github_login == "bob"))
            assert bob is not None
            bob.tech_tags = list(ctx.tech_element)  # single-repo clobber
            repo_a = OSRepository(full_name="a/repo", name="repo", developer_id=bob.developer_id)
            s.add(repo_a)
            await s.flush()
            s.add(OSContribution(developer_id=bob.developer_id, repo_id=repo_a.repo_id))

            task = await s.scalar(select(OSCollectTask).where(OSCollectTask.task_id == task_id))
            if task:
                task.status = "completed"
            await s.commit()

    monkeypatch.setattr(gc_mod.GitHubCollector, "collect", _stub_collect)


async def _run_collection(service: OSCollectionService, task_id: int) -> None:
    await service.run_repo_collection_background(
        task_id=task_id,
        repo_config_id=1,
        repo_full_name="a/repo",
        tech_element=["models"],
        contributors_per_repo=0,
    )


@pytest.mark.asyncio
async def test_recollection_preserves_union_tech_tags(
    test_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Re-collecting a/repo must not drop bob's 'security' tag from b/repo."""
    await _seed_union_scenario(test_session)

    task = OSCollectTask(task_name="union/repo", status="pending", config_json={})
    test_session.add(task)
    await test_session.commit()
    _install_stub_collector(monkeypatch, task.task_id)

    service = OSCollectionService(test_session)
    await _run_collection(service, task.task_id)

    bob = await test_session.scalar(select(OSDeveloper).where(OSDeveloper.github_login == "bob"))
    await test_session.refresh(bob)
    assert set(bob.tech_tags) == {"models", "security"}


@pytest.mark.asyncio
async def test_union_sync_failure_keeps_task_completed(
    test_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The post-collection union sync is best-effort: if it fails, the
    collection result (completed) stands."""

    async def _boom(self: Any, repo_full_name: str) -> int:
        raise RuntimeError("union sync exploded")

    monkeypatch.setattr(TechTagSyncMixin, "sync_developer_tech_tags", _boom)

    await _seed_union_scenario(test_session)
    task = OSCollectTask(task_name="boom-union/repo", status="pending", config_json={})
    test_session.add(task)
    await test_session.commit()
    _install_stub_collector(monkeypatch, task.task_id)

    service = OSCollectionService(test_session)
    await _run_collection(service, task.task_id)

    await test_session.refresh(task)
    assert task.status == "completed"
