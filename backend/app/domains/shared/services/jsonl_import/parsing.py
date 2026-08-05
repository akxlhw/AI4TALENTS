"""Tolerant JSONL line parsing shared by the import services."""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

INVALID_JSON_REASON = "invalid JSON"


@dataclass(frozen=True)
class JsonlLine:
    """One non-blank line of a JSONL payload.

    ``record`` holds the parsed JSON value (``None`` when ``error`` is set);
    ``error`` holds the skip reason when the line could not be parsed.
    """

    lineno: int
    record: Any
    error: str | None


def iter_jsonl_records(content: str) -> Iterator[JsonlLine]:
    """Yield one JsonlLine per non-blank line, tolerating bad lines.

    A line that fails ``json.loads`` is yielded with ``error`` set instead of
    raising, so callers record a per-line skip (with line number) and continue.
    """
    for lineno, raw_line in enumerate(content.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            yield JsonlLine(lineno=lineno, record=json.loads(line), error=None)
        except json.JSONDecodeError:
            yield JsonlLine(lineno=lineno, record=None, error=INVALID_JSON_REASON)


def count_jsonl_lines(content: str, *, skip_blank: bool = False) -> int:
    """Line count of a JSONL payload; ``skip_blank=True`` counts non-blank lines only."""
    if not skip_blank:
        return len(content.splitlines())
    return sum(1 for line in content.splitlines() if line.strip())
