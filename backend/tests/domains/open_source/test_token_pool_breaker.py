"""Tests for the token-pool circuit breaker in collect-task background runs.

Bug (production): batch-starting 100+ collections — when one running task
exhausted ALL GitHub tokens, queued tasks each woke a FRESH GitHubClient
(token state is per-instance, rate limits are account-scoped) and
re-discovered the exhaustion by failing. The breaker makes the discovery
global: once any task hits RateLimitExhaustedError, tasks that have not
started yet defer to rate_limited without touching GitHub.
"""

from __future__ import annotations

import time

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.open_source.models.open_source import OSCollectTask
from app.domains.open_source.services import background_state
from app.domains.open_source.services.os_collection_service import OSCollectionService


@pytest.fixture(autouse=True)
def _reset_breaker():
    background_state.clear_token_pool_breaker()
    yield
    background_state.clear_token_pool_breaker()


async def _make_pending_task(session: AsyncSession, name: str = "breaker/repo") -> OSCollectTask:
    task = OSCollectTask(task_name=name, status="pending", config_json={})
    session.add(task)
    await session.commit()
    return task


@pytest.mark.asyncio
async def test_breaker_functions(test_session: AsyncSession) -> None:
    """Unit: mark/exhausted/clear behave as a time-window flag."""
    assert background_state.is_token_pool_exhausted() is False
    background_state.mark_token_pool_exhausted(600)
    assert background_state.is_token_pool_exhausted() is True
    background_state.clear_token_pool_breaker()
    assert background_state.is_token_pool_exhausted() is False
    # Expired timestamp counts as closed
    background_state.mark_token_pool_exhausted(-1)  # max(1,..) clamps to 1s; use past stamp
    background_state.token_pool_resume_at = time.time() - 1
    assert background_state.is_token_pool_exhausted() is False


@pytest.mark.asyncio
async def test_queued_task_defers_when_breaker_open(
    test_session: AsyncSession,
) -> None:
    """A pending task that acquires a slot while the breaker is open goes
    straight to rate_limited — no GitHubClient is created, no request made."""
    task = await _make_pending_task(test_session)
    background_state.mark_token_pool_exhausted(600)

    service = OSCollectionService(test_session)
    await service.run_repo_collection_background(
        task_id=task.task_id,
        repo_config_id=1,
        repo_full_name="breaker/repo",
        tech_element=["models"],
        contributors_per_repo=0,
    )

    await test_session.refresh(task)
    assert task.status == "rate_limited"
    assert task.current_step == "rate_limited"
    assert task.resume_at is not None
    assert "circuit breaker" in (task.error_message or "")


@pytest.mark.asyncio
async def test_breaker_not_open_task_runs_normally(
    test_session: AsyncSession,
) -> None:
    """With the breaker closed, the task proceeds to the normal path (flips
    to running, then fails on network since no real GitHub is reachable in
    tests — the point is it did NOT defer)."""
    task = await _make_pending_task(test_session, "normal/repo")
    assert background_state.is_token_pool_exhausted() is False

    service = OSCollectionService(test_session)
    await service.run_repo_collection_background(
        task_id=task.task_id,
        repo_config_id=1,
        repo_full_name="normal/repo",
        tech_element=["models"],
        contributors_per_repo=0,
    )

    await test_session.refresh(task)
    # Breaker-deferred would be rate_limited; here the task actually ran
    assert task.status != "rate_limited"
    assert task.status == "failed"  # network unreachable in test env
    assert task.started_at is not None  # it really started


@pytest.mark.asyncio
async def test_rate_limit_error_opens_breaker_globally(
    test_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When a running task hits RateLimitExhaustedError, the breaker opens —
    verified indirectly: a SECOND task submitted afterwards defers."""
    # Force the collector to raise the rate-limit error on first GitHub call
    import app.domains.open_source.services.collectors.github_collector as gc_mod
    from app.domains.open_source.services.github_client import RateLimitExhaustedError

    async def _explode(self, ctx):  # noqa: ANN001
        raise RateLimitExhaustedError("all tokens exhausted", retry_after=1200)

    monkeypatch.setattr(gc_mod.GitHubCollector, "collect", _explode)

    first = await _make_pending_task(test_session, "boom/one")
    second = await _make_pending_task(test_session, "boom/two")

    service = OSCollectionService(test_session)
    # Run first task to completion of its error path
    await service.run_repo_collection_background(
        task_id=first.task_id,
        repo_config_id=1,
        repo_full_name="boom/one",
        tech_element=["models"],
        contributors_per_repo=0,
    )
    assert background_state.is_token_pool_exhausted() is True

    # Second (queued) task should now defer WITHOUT calling collect
    await service.run_repo_collection_background(
        task_id=second.task_id,
        repo_config_id=1,
        repo_full_name="boom/two",
        tech_element=["models"],
        contributors_per_repo=0,
    )
    await test_session.refresh(second)
    assert second.status == "rate_limited"
    assert "circuit breaker" in (second.error_message or "")


@pytest.mark.asyncio
async def test_resume_loop_closes_stale_breaker(test_session: AsyncSession) -> None:
    """The auto-resume loop clears a breaker whose window has passed."""
    background_state.token_pool_resume_at = time.time() - 5  # expired
    service = OSCollectionService(test_session)
    resumed = await service.resume_due_rate_limited_tasks()
    assert resumed == 0
    assert background_state.token_pool_resume_at is None
