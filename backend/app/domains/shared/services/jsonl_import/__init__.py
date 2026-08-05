"""Shared skeleton for JSONL admin-upload importers (lab / competition / industry).

Building blocks, not a forced unified pipeline — each domain keeps its own
import semantics (competition: per-contest full replace; lab: per-lab full
replace; industry: incremental upsert) and composes these pieces:

- ``iter_jsonl_records`` / ``count_jsonl_lines`` — tolerant line parsing:
  blank lines skipped, unparseable lines surface as per-line errors
  (``"invalid JSON"`` with the 1-based line number) instead of aborting.
- ``run_row_isolated`` — row-level SAVEPOINT isolation: one row's DB error
  rolls that row back alone and is reported, never aborts the whole batch.
- ``abort_if_empty`` — the 0-valid-row hard guard: an empty/fully-invalid
  file must never delete or replace existing data nor report silent success.
- ``SkipReason`` / ``cap_skip_reasons`` — the shared report shape used by all
  three domains (``line`` + ``reason``; domain reports cap the list).
- ``trimmed_str`` — the ``_str`` helper previously duplicated verbatim.
"""

from app.domains.shared.services.jsonl_import.guard import abort_if_empty
from app.domains.shared.services.jsonl_import.isolation import (
    DB_ERROR_REASON_MAX_LEN,
    RowOutcome,
    run_row_isolated,
)
from app.domains.shared.services.jsonl_import.parsing import (
    JsonlLine,
    count_jsonl_lines,
    iter_jsonl_records,
)
from app.domains.shared.services.jsonl_import.report import (
    SKIP_REASONS_REPORT_CAP,
    SkipReason,
    cap_skip_reasons,
)
from app.domains.shared.services.jsonl_import.values import trimmed_str

__all__ = [
    "DB_ERROR_REASON_MAX_LEN",
    "SKIP_REASONS_REPORT_CAP",
    "JsonlLine",
    "RowOutcome",
    "SkipReason",
    "abort_if_empty",
    "cap_skip_reasons",
    "count_jsonl_lines",
    "iter_jsonl_records",
    "run_row_isolated",
    "trimmed_str",
]
