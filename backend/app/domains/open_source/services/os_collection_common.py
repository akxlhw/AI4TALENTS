"""
OS Collection 公共辅助 - 仓库输入解析与按仓库串行锁

从 os_collection_service.py 拆出的共享辅助，供各采集 Mixin 使用；
原路径 os_collection_service 仍 re-export 这些名字，调用方零改动。
"""

from __future__ import annotations

import asyncio
import logging
import re

logger = logging.getLogger(__name__)

# Regex to extract owner/repo from various GitHub URL formats or plain owner/repo
_REPO_URL_RE = re.compile(
    r"(?:https?://github\.com/)?"  # optional URL prefix
    r"([\w.-]+)/([\w.-]+?)"  # owner/repo (non-greedy repo to allow trailing path)
    r"(?:\.git)?(?:/.*)?$"  # optional .git suffix and/or trailing path (/tree/main, /blob/...)
)


def parse_repo_input(raw: str) -> str | None:
    """Parse a user-provided repo input into 'owner/repo' format.

    Accepts:
      https://github.com/owner/repo
      https://github.com/owner/repo.git
      https://github.com/owner/repo/tree/main
      owner/repo
      owner/repo.git

    Returns 'owner/repo' or None if the input cannot be parsed.
    """
    raw = raw.strip()
    if not raw:
        return None
    m = _REPO_URL_RE.match(raw)
    if m:
        return f"{m.group(1)}/{m.group(2)}"
    return None


REPO_FULL_NAME_PATTERN = re.compile(r"^[\w.-]+/[\w.-]+$")

# Per-repository collection locks: the same repo collects serially, different
# repos may run in parallel. (Previously a single global Semaphore(1) forced
# all collections to serialize; combined with in-request rate-limit sleeps
# that deadlocked the whole pipeline. Rate-limit waits now fail fast, so
# parallel repos are safe — the token pool itself throttles aggregate load.)
_REPO_LOCKS: dict[str, asyncio.Lock] = {}
_REPO_LOCKS_GUARD = asyncio.Lock()


async def _get_repo_lock(repo_full_name: str) -> asyncio.Lock:
    """Get (or create) the lock serializing collection of one repository."""
    async with _REPO_LOCKS_GUARD:
        lock = _REPO_LOCKS.get(repo_full_name)
        if lock is None:
            lock = asyncio.Lock()
            _REPO_LOCKS[repo_full_name] = lock
        return lock
