"""Resilience tests for the GitHub client stack: token-pool blacklisting,
rate pacing, fail-fast exhaustion, and wire-level auth rotation.

Layer mapping after the cohesion refactor (github_client is a composition
facade): pool state machine = ``client.pool`` (github_token_pool),
request execution = ``client.transport`` (github_transport), endpoints =
``client.api`` (github_api).
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock

import httpx
import pytest

from app.core.config import settings
from app.domains.open_source.services.github_client import GitHubClient
from app.domains.open_source.services.github_token_pool import GitHubTokenPool
from app.domains.open_source.services.github_transport import RateLimitExhaustedError


def _make_response(
    status_code: int, headers: dict[str, str] | None = None, payload: dict | None = None
) -> httpx.Response:
    request = httpx.Request("GET", "https://api.github.com/x")
    return httpx.Response(status_code, headers=headers or {}, json=payload or {}, request=request)


def test_min_interval_derived_from_config() -> None:
    """Throttle interval must come from GITHUB_RATE_LIMIT and token pool size."""
    client = GitHubClient(token="t1")
    assert client.transport._min_interval == pytest.approx(3600.0 / settings.GITHUB_RATE_LIMIT)

    pooled = GitHubClient(token="t1,t2,t3,t4,t5")
    assert pooled.transport._min_interval == pytest.approx(
        3600.0 / (settings.GITHUB_RATE_LIMIT * 5)
    )


def test_token_pool_blacklists_and_picks_healthiest_alternative() -> None:
    """Pure state machine: 401 blacklisting zeroes quota; rotation skips it."""
    pool = GitHubTokenPool("a,b,c")
    assert pool.current_token() == "a"
    pool._token_remaining.update({0: 10, 1: 4000, 2: 50})

    pool.blacklist_current()  # simulate 401 on token #a
    assert pool._token_remaining[0] == 0

    assert pool.switch_to_best_alternative() is True
    assert pool.current_token_idx == 1  # healthiest alternative selected

    pool.pick_best()
    assert pool.current_token_idx == 1  # blacklisted token never re-selected

    # Nothing healthy left -> no switch possible
    pool._token_remaining.update({1: 0, 2: 0})
    assert pool.switch_to_best_alternative() is False

    # Single-token pools can neither rotate nor blacklist-switch
    solo = GitHubTokenPool("only")
    assert solo.switch_to_best_alternative() is False


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
        request_token_idxs.append(client.pool.current_token_idx)
        return responses.pop(0)

    monkeypatch.setattr(client.transport, "do_get_request", fake_request)

    result = await client.transport.get_json("/x")

    assert result == {"ok": True}
    assert client.pool._token_remaining[0] == 0  # bad token blacklisted
    assert client.pool.current_token_idx == 1  # rotated to the fresh token
    assert request_token_idxs == [0, 1]

    # The blacklisted token is never selected again
    client.pool.pick_best()
    assert client.pool.current_token_idx == 1


@pytest.mark.asyncio
async def test_401_single_token_raises_without_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """401 with no alternative token raises immediately (no pointless reset sleep)."""
    client = GitHubClient(token="only")
    reset_at = str(int(time.time()) + 1800)
    monkeypatch.setattr(
        client.transport,
        "do_get_request",
        AsyncMock(return_value=_make_response(401, headers={"X-RateLimit-Reset": reset_at})),
    )
    sleep_mock = AsyncMock()
    monkeypatch.setattr(
        "app.domains.open_source.services.github_transport.asyncio.sleep", sleep_mock
    )

    with pytest.raises(httpx.HTTPStatusError):
        await client.transport.get_json("/x")

    sleep_mock.assert_not_called()
    assert client.pool._token_remaining[0] == 0


@pytest.mark.asyncio
async def test_rate_limit_exhausted_fails_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    """All tokens exhausted (403 + reset): fail fast with Retry-After info, never sleep."""
    client = GitHubClient(token="only")
    reset_at = str(int(time.time()) + 1800)
    monkeypatch.setattr(
        client.transport,
        "do_get_request",
        AsyncMock(
            return_value=_make_response(
                403,
                headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": reset_at},
            )
        ),
    )
    sleep_mock = AsyncMock()
    monkeypatch.setattr(
        "app.domains.open_source.services.github_transport.asyncio.sleep", sleep_mock
    )

    with pytest.raises(RateLimitExhaustedError) as exc_info:
        await client.transport.get_json("/x")

    sleep_mock.assert_not_called()
    assert exc_info.value.retry_after is not None
    assert 1700 < exc_info.value.retry_after <= 1801


@pytest.mark.asyncio
async def test_rate_limit_exhausted_is_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    """RateLimitExhaustedError must propagate through tenacity on first attempt."""
    client = GitHubClient(token="only")
    calls = 0

    async def fake_get_json(path: str, params: dict | None = None) -> None:
        nonlocal calls
        calls += 1
        raise RateLimitExhaustedError("exhausted", retry_after=100)

    monkeypatch.setattr(client.transport, "get_json", fake_get_json)

    with pytest.raises(RateLimitExhaustedError):
        await client.transport.get_with_retry("/x")

    assert calls == 1


@pytest.mark.asyncio
async def test_remote_protocol_error_is_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    """Server-disconnect (RemoteProtocolError) is transient: retried, and the
    request succeeds once the transport recovers — instead of feeding the
    circuit breaker on every blip."""
    client = GitHubClient(token="only")
    calls = 0

    async def flaky_get_json(path: str, params: dict | None = None) -> dict:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.RemoteProtocolError("Server disconnected without sending a response.")
        return {"ok": True}

    monkeypatch.setattr(client.transport, "get_json", flaky_get_json)
    sleep_mock = AsyncMock()
    monkeypatch.setattr(
        "app.domains.open_source.services.github_transport.asyncio.sleep", sleep_mock
    )

    result = await client.transport.get_with_retry("/x")

    assert result == {"ok": True}
    assert calls == 2


@pytest.mark.asyncio
async def test_commits_traversal_aborts_on_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_contributors_via_commits re-raises RateLimitExhaustedError instead of
    grinding through hundreds of futile pages."""
    client = GitHubClient(token="only")

    async def fake_list_commits(*args: object, **kwargs: object) -> None:
        raise RateLimitExhaustedError("exhausted", retry_after=100)

    monkeypatch.setattr(client.api, "list_commits", fake_list_commits)

    with pytest.raises(RateLimitExhaustedError):
        await client.list_contributors_via_commits("o", "r")


@pytest.mark.asyncio
async def test_rotation_changes_auth_header_on_the_wire() -> None:
    """Regression: token rotation must change the Authorization header actually
    sent (httpx snapshots client headers at creation, so per-request headers
    are required)."""
    client = GitHubClient(token="tokA,tokB")
    sent_auth: list[str | None] = []
    responses = [
        _make_response(
            403, headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "9999999999"}
        ),
        _make_response(200, payload={"ok": True}),
    ]

    class _StubClient:
        async def get(self, url: str, params: dict | None = None, headers: dict | None = None):
            sent_auth.append((headers or {}).get("Authorization"))
            return responses.pop(0)

    client.transport._client = _StubClient()  # type: ignore[assignment]
    client.transport._min_interval = 0  # no throttle delay in test

    result = await client.transport.get_json("/x")

    assert result == {"ok": True}
    assert sent_auth == ["Bearer tokA", "Bearer tokB"]
    assert client.pool.current_token_idx == 1
