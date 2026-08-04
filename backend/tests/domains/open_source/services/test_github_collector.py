"""Tests for honest failure reporting in GitHubCollector.

Regression tests for the audit finding: contributor-stage failures were
swallowed and the task was marked "completed" with zero output.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.domains.open_source.models.open_source import OSCollectTask
from app.domains.open_source.services.collectors.github_collector import (
    CollectContext,
    GitHubCollector,
)
from app.domains.open_source.services.github_client import RateLimitExhaustedError
from app.domains.open_source.services.os_collection_service import (
    OSCollectionService,
    _get_repo_lock,
)


class _FailingClient:
    """GitHub client stub whose per-user calls always fail."""

    async def get_repo(self, owner: str, repo: str) -> dict:
        return {
            "id": 1,
            "stargazers_count": 1,
            "forks_count": 0,
            "language": "Python",
            "topics": [],
            "fork": False,
        }

    async def list_contributors(self, owner: str, repo: str, max_count: int) -> list[dict]:
        return [{"login": "ghost", "contributions": 5, "is_committer": True}]

    async def get_user(self, login: str) -> dict:
        raise RuntimeError("GitHub API down")

    async def list_user_repos(self, login: str, per_page: int = 100) -> list[dict]:
        return []


class _NotFoundClient(_FailingClient):
    """GitHub client stub where the user simply does not exist (soft skip)."""

    async def get_user(self, login: str) -> None:
        return None


async def _make_task(test_session: AsyncSession) -> OSCollectTask:
    task = OSCollectTask(task_name="collect o/r", status="pending")
    test_session.add(task)
    await test_session.commit()
    await test_session.refresh(task)
    return task


def _make_context(task_id: int) -> CollectContext:
    return CollectContext(
        task_id=task_id,
        repo_config_id=1,
        repo_full_name="o/r",
        tech_element="ai",
        contributors_per_repo=10,
    )


async def _read_task(task_id: int) -> OSCollectTask:
    async with AsyncSessionLocal() as session:
        task = await session.get(OSCollectTask, task_id)
        assert task is not None
        return task


@pytest.mark.asyncio
async def test_all_contributors_failed_marks_task_failed(test_session: AsyncSession) -> None:
    """Zero-output run must be marked failed, not completed (no fake success)."""
    task = await _make_task(test_session)
    collector = GitHubCollector(_FailingClient())  # type: ignore[arg-type]

    await collector.collect(_make_context(task.task_id))

    updated = await _read_task(task.task_id)
    assert updated.status == "failed"
    assert updated.error_message is not None
    assert "1/1" in updated.error_message


@pytest.mark.asyncio
async def test_not_found_user_is_soft_skip_not_failure(test_session: AsyncSession) -> None:
    """A missing user (404) is a soft skip, not a failure — task completes cleanly."""
    task = await _make_task(test_session)
    collector = GitHubCollector(_NotFoundClient())  # type: ignore[arg-type]

    await collector.collect(_make_context(task.task_id))

    updated = await _read_task(task.task_id)
    assert updated.status == "completed"
    assert updated.error_message is None


class _RateLimitedClient(_FailingClient):
    """GitHub client stub whose per-user calls hit an exhausted token pool."""

    async def get_user(self, login: str) -> dict:
        raise RateLimitExhaustedError("all tokens exhausted", retry_after=42)


@pytest.mark.asyncio
async def test_rate_limit_aborts_run_fast(test_session: AsyncSession) -> None:
    """RateLimitExhaustedError is not a per-contributor failure: the run aborts."""
    task = await _make_task(test_session)
    collector = GitHubCollector(_RateLimitedClient())  # type: ignore[arg-type]
    ctx = _make_context(task.task_id)

    with pytest.raises(RateLimitExhaustedError):
        await collector.collect(ctx)

    assert ctx.rate_limited is not None
    assert ctx.rate_limited.retry_after == 42
    assert ctx.failed_contributors == 0  # not counted as contributor failures


@pytest.mark.asyncio
async def test_background_marks_task_rate_limited(
    test_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Task layer: rate-limited run marks the task rate_limited with retry_after."""
    task = await _make_task(test_session)

    async def _boom(self: GitHubCollector, ctx: CollectContext) -> None:
        raise RateLimitExhaustedError("all tokens exhausted", retry_after=42)

    monkeypatch.setattr(GitHubCollector, "collect", _boom)

    service = OSCollectionService(test_session)
    await service.run_repo_collection_background(
        task_id=task.task_id,
        repo_config_id=1,
        repo_full_name="o/r",
        tech_element="ai",
        contributors_per_repo=10,
    )

    updated = await _read_task(task.task_id)
    assert updated.status == "rate_limited"
    assert updated.error_message is not None
    assert "42" in updated.error_message


@pytest.mark.asyncio
async def test_repo_locks_are_per_repository() -> None:
    """Same repo serializes on one lock; different repos get different locks."""
    lock_a1 = await _get_repo_lock("o/a")
    lock_a2 = await _get_repo_lock("o/a")
    lock_b = await _get_repo_lock("o/b")

    assert lock_a1 is lock_a2
    assert lock_a1 is not lock_b
