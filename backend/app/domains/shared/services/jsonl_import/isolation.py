"""Row-level SAVEPOINT isolation for per-row upsert loops.

One row's DB error (constraint violation, unserializable JSON, ...) rolls that
row back alone and is reported as a skip; all surviving rows still commit in
the caller's outer transaction. This is the import boundary where exceptions
are converted into per-row skip reasons (error-handling contract).
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Max length of the DB error message embedded in a skip reason.
DB_ERROR_REASON_MAX_LEN = 200

T = TypeVar("T")


@dataclass(frozen=True)
class RowOutcome(Generic[T]):
    """Result of one SAVEPOINT-isolated row upsert.

    Exactly one of the two states applies: success (``error is None``,
    ``value`` holds the handler result) or failure (``error`` holds the skip
    reason, the row's SAVEPOINT was rolled back).
    """

    value: T | None = None
    error: str | None = None


async def run_row_isolated(
    session: AsyncSession,
    work: Callable[[], Awaitable[T]],
    *,
    on_error: Callable[[Exception], None] | None = None,
) -> RowOutcome[T]:
    """Run ``work()`` under a SAVEPOINT so one row cannot abort the batch.

    On success returns ``RowOutcome(value=...)``. On any exception the row's
    SAVEPOINT is rolled back, ``on_error`` (if given) is invoked with the raw
    exception for domain-specific logging, and the row is reported as
    ``RowOutcome(error="db error: <msg>")`` instead of raising.
    """
    try:
        async with session.begin_nested():
            return RowOutcome(value=await work())
    except Exception as e:  # intentional boundary: convert to a per-row skip
        if on_error is not None:
            on_error(e)
        else:
            logger.warning("[JsonlImport] row DB error, row skipped: %s", e)
        return RowOutcome(error=f"db error: {str(e)[:DB_ERROR_REASON_MAX_LEN]}")
