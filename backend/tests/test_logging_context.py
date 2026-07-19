"""Tests for task_id log-context propagation (structured collection logs)."""

from __future__ import annotations

import logging

from app.core.logging_config import TaskIdPrefixFilter
from app.core.logging_context import current_task_id


def _make_record(msg: str) -> logging.LogRecord:
    return logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0, msg=msg, args=(), exc_info=None
    )


def test_filter_prefixes_message_within_task_context() -> None:
    token = current_task_id.set(42)
    try:
        record = _make_record("phase failed")
        TaskIdPrefixFilter().filter(record)
        assert record.msg == "[task_id=42] phase failed"
    finally:
        current_task_id.reset(token)


def test_filter_passes_message_without_task_context() -> None:
    record = _make_record("plain message")
    TaskIdPrefixFilter().filter(record)
    assert record.msg == "plain message"


def test_context_resets_between_tasks() -> None:
    token = current_task_id.set(1)
    current_task_id.reset(token)
    assert current_task_id.get() is None
