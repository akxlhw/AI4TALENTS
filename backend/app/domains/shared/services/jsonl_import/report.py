"""Shared import-report shape for the JSONL import services.

Each domain keeps its own report schema (``LabImportReport`` /
``CompImportReport`` / ``IndustryImportReport``), but all of them embed the
same ``SkipReason`` entry shape and cap the reported list to keep payloads
bounded. Domain schema modules import ``SkipReason`` from here.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypeVar

from pydantic import BaseModel

# Cap on skip_reasons embedded in an import report, to avoid huge payloads.
SKIP_REASONS_REPORT_CAP = 50

SkipReasonT = TypeVar("SkipReasonT", bound="SkipReason")


class SkipReason(BaseModel):
    """Reason a JSONL line was skipped during import."""

    line: int
    reason: str


def cap_skip_reasons(skips: Sequence[SkipReasonT]) -> list[SkipReasonT]:
    """First ``SKIP_REASONS_REPORT_CAP`` skip entries, for embedding in a report."""
    return list(skips[:SKIP_REASONS_REPORT_CAP])
