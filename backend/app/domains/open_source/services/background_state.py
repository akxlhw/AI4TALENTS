"""Background task state for open-source domain.

Centralises mutable state that was previously scattered across API and
Service layers as module-level globals.  Keeping it in a dedicated module
avoids circular imports (service → api) and makes the state accessible
from any layer.

IMPORTANT: This module is only safe for single-process deployments.
If the backend runs with multiple workers (e.g. gunicorn -w N), this
state will NOT be shared across workers.  For multi-worker deployments,
migrate to Redis-backed state.
"""

from __future__ import annotations

# ---- Collection task cancellation ----
# Set of task IDs that have been requested to cancel.
# The background collector polls this set and stops when its task_id appears.
cancelled_task_ids: set[int] = set()

# ---- Embedding generation progress ----
# Dict tracking the current embedding generation batch.
# Updated by the background coroutine; read by the progress endpoint.
embedding_progress: dict = {
    "status": "idle",
    "processed": 0,
    "total": 0,
    "failed": 0,
    "started_at": None,
    "completed_at": None,
    "error_message": None,
}
