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

import time

# ---- Collection task cancellation ----
# Set of task IDs that have been requested to cancel.
# The background collector polls this set and stops when its task_id appears.
cancelled_task_ids: set[int] = set()

# ---- Token-pool circuit breaker ----
# Epoch seconds until which the shared GitHub token pool is considered
# exhausted. Rate limits are ACCOUNT-scoped but each background task owns a
# private GitHubClient, so exhaustion discovered by one client is invisible
# to the others: without this flag every queued task re-discovers the
# exhaustion by failing. When any client raises RateLimitExhaustedError the
# handler stamps a resume deadline here; queued tasks check it before
# starting and go straight to rate_limited instead of burning a failure.
token_pool_resume_at: float | None = None


def is_token_pool_exhausted() -> bool:
    """True while the global token-pool circuit breaker is open."""
    return token_pool_resume_at is not None and time.time() < token_pool_resume_at


def mark_token_pool_exhausted(retry_after: int) -> None:
    """Open the circuit breaker for ``retry_after`` seconds (last write wins)."""
    global token_pool_resume_at
    token_pool_resume_at = time.time() + max(1, retry_after)


def clear_token_pool_breaker() -> None:
    """Close the breaker (used by the auto-resume loop once the window passes)."""
    global token_pool_resume_at
    token_pool_resume_at = None


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
