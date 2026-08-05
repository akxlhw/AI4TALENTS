"""Field-value helpers shared by the JSONL import services."""

from __future__ import annotations

from typing import Any


def trimmed_str(value: Any, max_len: int) -> str | None:
    """Trimmed string truncated to max_len, or None when absent/blank."""
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()[:max_len]
