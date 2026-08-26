"""Shared helpers for open-api import endpoints."""

from __future__ import annotations

from fastapi import Request

MAX_JSONL_BYTES = 20 * 1024 * 1024


async def read_jsonl_body(request: Request) -> tuple[str, str | None]:
    """Read the raw JSONL request body. Returns (content, error_msg)."""
    raw = await request.body()
    if len(raw) > MAX_JSONL_BYTES:
        return "", f"Body too large ({len(raw)} bytes, max {MAX_JSONL_BYTES})"
    try:
        return raw.decode("utf-8"), None
    except UnicodeDecodeError:
        return "", "Body is not valid UTF-8"
