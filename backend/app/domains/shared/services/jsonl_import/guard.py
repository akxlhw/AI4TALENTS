"""The 0-valid-row hard guard shared by the JSONL import services.

An empty or fully-invalid file must never delete/replace existing data, and
must surface as an explicit aborted report rather than a silent success.
The decision is shared; the aborted report itself stays domain-specific.
"""

from __future__ import annotations

from collections.abc import Callable, Collection
from typing import Any, TypeVar

ReportT = TypeVar("ReportT")


def abort_if_empty(rows: Collection[Any], on_abort: Callable[[], ReportT]) -> ReportT | None:
    """0-valid-row hard guard.

    Returns ``None`` when ``rows`` is non-empty — the import proceeds. When
    empty, invokes ``on_abort`` (which logs the domain-specific warning and
    builds the domain's aborted report) and returns that report; the caller
    returns it immediately without touching the database.
    """
    if rows:
        return None
    return on_abort()
