"""Context propagation for structured logging fields.

Currently provides `current_task_id`: set by the collection orchestrator at
task start so every downstream log record (phases, fetchers, normalizers) can
carry a uniform task_id without changing any call signatures.
"""

import contextvars

current_task_id: contextvars.ContextVar[int | None] = contextvars.ContextVar(
    "current_task_id", default=None
)
