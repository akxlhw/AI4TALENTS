"""
Tests for Retry-After handling on the aiohttp (OpenAlex) fetch path.

Covers:
- Retry-After header parsing (delta-seconds / HTTP-date / garbage / missing)
- tenacity wait strategy honoring Retry-After with an upper cap
- 429 responses producing RetryableError carrying retry_after end-to-end
"""

from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from unittest.mock import MagicMock

import pytest

from app.domains.academic.services.data_fetchers import (
    RETRY_AFTER_MAX_WAIT,
    RetryableError,
    WorkFetcher,
    _parse_retry_after,
    _rate_limited_error,
    _wait_honoring_retry_after,
)


class TestParseRetryAfter:
    """Retry-After 头解析"""

    @pytest.mark.unit
    def test_delta_seconds(self):
        assert _parse_retry_after("30") == 30.0

    @pytest.mark.unit
    def test_delta_seconds_with_whitespace(self):
        assert _parse_retry_after(" 15 ") == 15.0

    @pytest.mark.unit
    def test_negative_clamped_to_zero(self):
        assert _parse_retry_after("-5") == 0.0

    @pytest.mark.unit
    def test_none_and_empty(self):
        assert _parse_retry_after(None) is None
        assert _parse_retry_after("") is None

    @pytest.mark.unit
    def test_garbage_returns_none(self):
        assert _parse_retry_after("not-a-date") is None

    @pytest.mark.unit
    def test_http_date_future(self):
        future = datetime.now(timezone.utc) + timedelta(seconds=120)
        result = _parse_retry_after(format_datetime(future))
        assert result is not None
        assert 100 < result <= 120

    @pytest.mark.unit
    def test_http_date_past_clamped_to_zero(self):
        past = datetime.now(timezone.utc) - timedelta(seconds=60)
        assert _parse_retry_after(format_datetime(past)) == 0.0


class TestRateLimitedError:
    """429 响应构造 RetryableError"""

    @pytest.mark.unit
    def test_reads_retry_after_header(self):
        response = MagicMock()
        response.headers = {"Retry-After": "12"}
        err = _rate_limited_error(response)
        assert isinstance(err, RetryableError)
        assert err.retry_after == 12.0

    @pytest.mark.unit
    def test_missing_header_gives_none(self):
        response = MagicMock()
        response.headers = {}
        err = _rate_limited_error(response)
        assert err.retry_after is None


def _make_retry_state(exc: Exception, attempt_number: int = 2) -> MagicMock:
    """Duck-typed RetryCallState for the wait strategy."""
    state = MagicMock()
    state.outcome.exception.return_value = exc
    state.attempt_number = attempt_number
    return state


class TestWaitHonoringRetryAfter:
    """重试等待策略：优先尊重 Retry-After，封顶 RETRY_AFTER_MAX_WAIT"""

    @pytest.mark.unit
    def test_retry_after_honored(self):
        wait = _wait_honoring_retry_after(min_wait=1.0, max_wait=60.0)
        assert wait(_make_retry_state(RetryableError("x", retry_after=12.0))) == 12.0

    @pytest.mark.unit
    def test_retry_after_overrides_shorter_backoff_cap(self):
        # Retry-After 不受指数退避 max_wait 限制（只受 RETRY_AFTER_MAX_WAIT 封顶）
        wait = _wait_honoring_retry_after(min_wait=1.0, max_wait=30.0)
        assert wait(_make_retry_state(RetryableError("x", retry_after=120.0))) == 120.0

    @pytest.mark.unit
    def test_retry_after_capped(self):
        wait = _wait_honoring_retry_after(min_wait=1.0, max_wait=60.0)
        assert (
            wait(_make_retry_state(RetryableError("x", retry_after=99999.0)))
            == RETRY_AFTER_MAX_WAIT
        )

    @pytest.mark.unit
    def test_fallback_to_exponential_without_hint(self):
        wait = _wait_honoring_retry_after(min_wait=1.0, max_wait=60.0)
        state = _make_retry_state(RetryableError("x"), attempt_number=3)
        assert wait(state) == 4.0  # 1 * 2^(3-1)

    @pytest.mark.unit
    def test_fallback_for_non_retryable(self):
        wait = _wait_honoring_retry_after(min_wait=1.0, max_wait=60.0)
        state = _make_retry_state(ValueError("boom"), attempt_number=2)
        assert wait(state) == 2.0


class _Fake429Response:
    """Minimal aiohttp response double: always HTTP 429 with Retry-After."""

    status = 429

    def __init__(self, retry_after: str):
        self.headers = {"Retry-After": retry_after}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class _FakeSession:
    def __init__(self, retry_after: str):
        self._retry_after = retry_after

    def get(self, *args, **kwargs):
        return _Fake429Response(self._retry_after)


class TestFetchPageRetryAfter:
    """端到端：429 + Retry-After 头透传到重试层"""

    @pytest.mark.unit
    async def test_retry_after_propagates(self, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "CIRCUIT_BREAKER_ENABLED", False)
        fetcher = WorkFetcher(session=MagicMock())
        http_session = _FakeSession(retry_after="0.01")

        with pytest.raises(RetryableError) as exc_info:
            await fetcher._fetch_page_with_retry(http_session, "http://example.com", {}, {})

        assert exc_info.value.retry_after == pytest.approx(0.01)

    @pytest.mark.unit
    async def test_no_header_retry_after_is_none(self, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "CIRCUIT_BREAKER_ENABLED", False)
        fetcher = WorkFetcher(session=MagicMock())

        class _NoHeaderSession:
            def get(self, *args, **kwargs):
                resp = _Fake429Response("0.01")
                resp.headers = {}
                return resp

        with pytest.raises(RetryableError) as exc_info:
            await fetcher._fetch_page_with_retry(_NoHeaderSession(), "http://example.com", {}, {})

        assert exc_info.value.retry_after is None
