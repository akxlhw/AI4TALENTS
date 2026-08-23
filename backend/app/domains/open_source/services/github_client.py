"""GitHub API client for open-source talent collection.

Composition facade over three focused layers (2026-08 cohesion refactor):

- ``github_token_pool.GitHubTokenPool`` — token state machine (rotation,
  rate-limit bookkeeping, 401 blacklisting); pure, no IO
- ``github_transport.GitHubTransport`` — httpx lifecycle via HttpClientFactory,
  request throttling, tenacity retry, circuit breaker,
  ``RateLimitExhaustedError`` fail-fast
- ``github_api.GitHubApi`` — REST endpoint wrappers

The public surface is unchanged: construct with ``GitHubClient(token=...)``,
use as an async context manager, call the endpoint methods. All production
call sites keep importing from this module.
"""

from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.domains.open_source.services.github_api import GitHubApi
from app.domains.open_source.services.github_token_pool import GitHubTokenPool
from app.domains.open_source.services.github_transport import (
    GitHubTransport,
    RateLimitExhaustedError,
)

__all__ = ["GitHubClient", "RateLimitExhaustedError"]


class GitHubClient:
    """Async GitHub REST API client with rate-limit awareness."""

    def __init__(self, token: str | None = None, base_url: str | None = None) -> None:
        self.pool = GitHubTokenPool(token)
        self.transport = GitHubTransport(
            base_url=base_url or settings.GITHUB_BASE_URL, token_pool=self.pool
        )
        self.api = GitHubApi(self.transport)

    async def __aenter__(self) -> GitHubClient:
        await self.transport.__aenter__()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.transport.__aexit__(*args)

    async def get_repo(self, owner: str, repo: str) -> dict[str, Any]:
        """Fetch repository details."""
        return await self.api.get_repo(owner, repo)

    async def search_repositories(
        self,
        query: str,
        sort: str = "stars",
        order: str = "desc",
        per_page: int = 20,
    ) -> dict[str, Any]:
        """Search repositories. Returns {"items": [...], "total_count": N}."""
        return await self.api.search_repositories(query, sort=sort, order=order, per_page=per_page)

    async def list_contributors(
        self, owner: str, repo: str, max_count: int = 30
    ) -> list[dict[str, Any]]:
        """Fetch repository contributors with pagination."""
        return await self.api.list_contributors(owner, repo, max_count=max_count)

    async def count_contributors(self, owner: str, repo: str) -> int:
        """Approximate the contributor count via Link-header pagination."""
        return await self.api.count_contributors(owner, repo)

    async def get_user(self, login: str) -> dict[str, Any]:
        """Fetch user profile."""
        return await self.api.get_user(login)

    async def list_user_repos(self, login: str, per_page: int = 100) -> list[dict[str, Any]]:
        """Fetch user's public repositories."""
        return await self.api.list_user_repos(login, per_page=per_page)

    async def list_commits(
        self, owner: str, repo: str, sha: str | None = None, per_page: int = 100, page: int = 1
    ) -> list[dict[str, Any]]:
        """Fetch repository commits with pagination."""
        return await self.api.list_commits(owner, repo, sha=sha, per_page=per_page, page=page)

    async def list_contributors_via_commits(
        self, owner: str, repo: str, max_count: int = 1000
    ) -> list[dict[str, Any]]:
        """Fetch contributors by traversing the commits API."""
        return await self.api.list_contributors_via_commits(owner, repo, max_count=max_count)
