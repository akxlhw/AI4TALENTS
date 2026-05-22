"""Sliding-window circuit breaker for external API calls.

Provides asyncio-safe circuit breaker with three states:
  CLOSED   -> normal operation, all calls pass through
  OPEN     -> failing fast, calls are rejected immediately
  HALF_OPEN -> probe mode, next call determines recovery

No external dependencies; uses pure asyncio + collections.deque.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from collections.abc import Callable
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerOpenError(Exception):
    """Raised when the circuit breaker is OPEN and a call is attempted."""

    pass


class CircuitBreaker:
    """Async sliding-window circuit breaker.

    Tracks the most recent *window_size* calls in a deque.  A call is
    considered a failure if it raises any exception.  The breaker
    trips when **either**:

    * consecutive_failures >= failure_threshold, or
    * at least *window_size* calls have been recorded and the number
      of failures in the window >= failure_threshold.

    After tripping, the circuit stays OPEN for *recovery_timeout*
    seconds, then transitions to HALF_OPEN.  A single successful call
    in HALF_OPEN resets the breaker to CLOSED; a failure re-opens it.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        window_size: int = 10,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.window_size = window_size

        self._state = CircuitState.CLOSED
        self._lock = asyncio.Lock()
        self._window: deque[bool] = deque(maxlen=window_size)
        self._opened_at: float = 0.0
        self._consecutive_failures = 0

    @property
    def state(self) -> CircuitState:
        return self._state

    def _should_trip(self) -> bool:
        """Check whether current metrics warrant tripping the breaker."""
        if self._consecutive_failures >= self.failure_threshold:
            return True
        if len(self._window) >= self.window_size:
            failures = sum(1 for ok in self._window if not ok)
            if failures >= self.failure_threshold:
                return True
        return False

    async def _can_execute(self) -> bool:
        """Return True if the call should be allowed through."""
        if self._state == CircuitState.CLOSED:
            return True
        if self._state == CircuitState.HALF_OPEN:
            return True
        # OPEN – check if recovery timeout has elapsed
        if time.time() - self._opened_at >= self.recovery_timeout:
            self._state = CircuitState.HALF_OPEN
            self._consecutive_failures = 0
            logger.warning(
                f"Circuit breaker '{self.name}' entering HALF_OPEN after timeout"
            )
            return True
        return False

    async def _record_success(self) -> None:
        async with self._lock:
            self._window.append(True)
            self._consecutive_failures = 0
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.CLOSED
                self._window.clear()
                logger.info(f"Circuit breaker '{self.name}' CLOSED (recovered)")

    async def _record_failure(self) -> None:
        async with self._lock:
            self._window.append(False)
            self._consecutive_failures += 1

            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                self._opened_at = time.time()
                logger.error(
                    f"Circuit breaker '{self.name}' OPEN (probe failed)"
                )
            elif self._should_trip():
                self._state = CircuitState.OPEN
                self._opened_at = time.time()
                logger.error(
                    f"Circuit breaker '{self.name}' OPEN "
                    f"(consecutive={self._consecutive_failures}, "
                    f"window_failures={sum(1 for ok in self._window if not ok)}/{len(self._window)})"
                )

    async def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """Execute *func* if the circuit allows it.

        Args:
            func: Async callable to invoke.
            *args, **kwargs: Arguments forwarded to *func*.

        Raises:
            CircuitBreakerOpenError: When the circuit is OPEN.
            Exception: Any exception raised by *func* (after recording failure).
        """
        async with self._lock:
            if not await self._can_execute():
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is OPEN"
                )

        try:
            result = await func(*args, **kwargs)
            await self._record_success()
            return result
        except Exception:
            await self._record_failure()
            raise

    def __call__(self, func: Callable) -> Callable:
        """Decorator form: ``@breaker`` on an async function."""

        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await self.call(func, *args, **kwargs)

        return wrapper
