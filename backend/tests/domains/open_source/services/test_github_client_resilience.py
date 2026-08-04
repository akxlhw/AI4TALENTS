"""Resilience tests for GitHubClient: 401 token blacklisting and rate pacing."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock

import httpx
import pytest

from app.core.config import settings
from app.domains.open_source.services.github_client import (
    GitHubClient,
    RateLimitExhaustedError,
)


def _make_response(
    status_code: int, headers: dict[str, str] | None = None, payload: dict | None = None
) -> httpx.Response:
    request = httpx.Request("GET", "https://api.github.com/x")
    return httpx.Response(status_code, headers=headers or {}, json=payload or {}, request=request)


def test_min_interval_derived_from_config() -> None:
    """Throttle interval must come from GITHUB_RATE_LIMIT and token pool size."""
    client = GitHubClient(token="t1")
    assert client._min_interval == pytest.approx(3600.0 / settings.GITHUB_RATE_LIMIT)

    pooled = GitHubClient(token="t1,t2,t3,t4,t5")
    assert pooled._min_interval == pytest.approx(3600.0 / (settings.GITHUB_RATE_LIMIT * 5))


@pytest.mark.asyncio
async def test_401_blacklists_token_and_rotates(monkeypatch: pytest.MonkeyPatch) -> None:
    """On 401 the bad token is blacklisted and the request retried with a fresh one."""
    client = GitHubClient(token="bad,good")
    responses = [
        _make_response(401),
        _make_response(200, payload={"ok": True}),
    ]
    request_token_idxs: list[int] = []

    async def fake_request(path: str, params: dict | None = None) -> httpx.Response:
        request_token_idxs.append(client.current_token_idx)
        return responses.pop(0)

    monkeypatch.setattr(client, "_do_get_request", fake_request)
    monkeypatch.setattr(client, "_rebuild_client", AsyncMock())

    result = await client._do_get("/x")

    assert result == {"ok": True}
    assert client._token_remaining[0] == 0  # bad token blacklisted
    assert client.current_token_idx == 1  # rotated to the fresh token
    assert request_token_idxs == [0, 1]

    # The blacklisted token is never selected again
    client._pick_best_token()
    assert client.current_token_idx == 1


@pytest.mark.asyncio
async def test_401_single_token_raises_without_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """401 with no alternative token raises immediately (no pointless reset sleep)."""
    client = GitHubClient(token="only")
    reset_at = str(int(time.time()) + 1800)
    monkeypatch.setattr(
        client,
        "_do_get_request",
        AsyncMock(return_value=_make_response(401, headers={"X-RateLimit-Reset": reset_at})),
    )
    sleep_mock = AsyncMock()
    monkeypatch.setattr("app.domains.open_source.services.github_client.asyncio.sleep", sleep_mock)

    with pytest.raises(httpx.HTTPStatusError):
        await client._do_get("/x")

    sleep_mock.assert_not_called()
    assert client._token_remaining[0] == 0


@pytest.mark.asyncio
async def test_rate_limit_exhausted_fails_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    """All tokens exhausted (403 + reset): fail fast with Retry-After info, never sleep."""
    client = GitHubClient(token="only")
    reset_at = str(int(time.time()) + 1800)
    monkeypatch.setattr(
        client,
        "_do_get_request",
        AsyncMock(
            return_value=_make_response(
                403,
                headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": reset_at},
            )
        ),
    )
    sleep_mock = AsyncMock()
    monkeypatch.setattr("app.domains.open_source.services.github_client.asyncio.sleep", sleep_mock)

    with pytest.raises(RateLimitExhaustedError) as exc_info:
        await client._do_get("/x")

    sleep_mock.assert_not_called()
    assert exc_info.value.retry_after is not None
    assert 1700 < exc_info.value.retry_after <= 1801


@pytest.mark.asyncio
async def test_rate_limit_exhausted_is_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    """RateLimitExhaustedError must propagate through tenacity on first attempt."""
    client = GitHubClient(token="only")
    calls = 0

    async def fake_do_get(path: str, params: dict | None = None) -> None:
        nonlocal calls
        calls += 1
        raise RateLimitExhaustedError("exhausted", retry_after=100)

    monkeypatch.setattr(client, "_do_get", fake_do_get)

    with pytest.raises(RateLimitExhaustedError):
        await client._get_with_retry("/x")

    assert calls == 1


@pytest.mark.asyncio
async def test_commits_traversal_aborts_on_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_contributors_via_commits re-raises RateLimitExhaustedError instead of
    grinding through hundreds of futile pages."""
    client = GitHubClient(token="only")

    async def fake_list_commits(*args: object, **kwargs: object) -> None:
        raise RateLimitExhaustedError("exhausted", retry_after=100)

    monkeypatch.setattr(client, "list_commits", fake_list_commits)

    with pytest.raises(RateLimitExhaustedError):
        await client.list_contributors_via_commits("o", "r")
