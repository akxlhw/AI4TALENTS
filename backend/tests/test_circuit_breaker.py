"""Tests for the sliding-window circuit breaker."""

from __future__ import annotations

import asyncio

import pytest

from app.domains.shared.services.common.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
)


class TestCircuitBreaker:
    """Unit tests for CircuitBreaker state transitions."""

    @pytest.fixture
    def breaker(self) -> CircuitBreaker:
        return CircuitBreaker(
            name="test",
            failure_threshold=3,
            recovery_timeout=0.1,
            window_size=5,
        )

    async def test_starts_closed(self, breaker: CircuitBreaker) -> None:
        assert breaker.state == CircuitState.CLOSED

    async def test_success_keeps_closed(self, breaker: CircuitBreaker) -> None:
        async def ok() -> str:
            return "ok"

        result = await breaker.call(ok)
        assert result == "ok"
        assert breaker.state == CircuitState.CLOSED

    async def test_opens_after_consecutive_failures(self, breaker: CircuitBreaker) -> None:
        async def fail() -> None:
            raise RuntimeError("boom")

        for _ in range(3):
            with pytest.raises(RuntimeError):
                await breaker.call(fail)

        assert breaker.state == CircuitState.OPEN

        with pytest.raises(CircuitBreakerOpenError):
            await breaker.call(fail)

    async def test_half_open_after_timeout(self, breaker: CircuitBreaker) -> None:
        async def fail() -> None:
            raise RuntimeError("boom")

        for _ in range(3):
            with pytest.raises(RuntimeError):
                await breaker.call(fail)

        assert breaker.state == CircuitState.OPEN

        await asyncio.sleep(0.15)

        async def ok() -> str:
            return "recovered"

        result = await breaker.call(ok)
        assert result == "recovered"
        assert breaker.state == CircuitState.CLOSED

    async def test_half_open_failure_reopens(self, breaker: CircuitBreaker) -> None:
        async def fail() -> None:
            raise RuntimeError("boom")

        for _ in range(3):
            with pytest.raises(RuntimeError):
                await breaker.call(fail)

        assert breaker.state == CircuitState.OPEN
        await asyncio.sleep(0.15)

        with pytest.raises(RuntimeError):
            await breaker.call(fail)

        assert breaker.state == CircuitState.OPEN

    async def test_window_failure_rate_trips(self) -> None:
        breaker = CircuitBreaker(
            name="window_test",
            failure_threshold=3,
            recovery_timeout=30.0,
            window_size=5,
        )

        async def fail() -> None:
            raise RuntimeError("boom")

        async def ok() -> str:
            return "ok"

        # 2 failures + 2 successes = still closed (below threshold)
        with pytest.raises(RuntimeError):
            await breaker.call(fail)
        with pytest.raises(RuntimeError):
            await breaker.call(fail)
        result = await breaker.call(ok)
        assert result == "ok"
        result = await breaker.call(ok)
        assert result == "ok"
        assert breaker.state == CircuitState.CLOSED

        # 3rd failure within window = trip
        with pytest.raises(RuntimeError):
            await breaker.call(fail)
        assert breaker.state == CircuitState.OPEN

    async def test_decorator_form(self) -> None:
        breaker = CircuitBreaker(
            name="decorator_test",
            failure_threshold=2,
            recovery_timeout=30.0,
            window_size=5,
        )

        @breaker
        async def flaky() -> str:
            raise ConnectionError("network down")

        with pytest.raises(ConnectionError):
            await flaky()
        with pytest.raises(ConnectionError):
            await flaky()

        with pytest.raises(CircuitBreakerOpenError):
            await flaky()
