"""GitHub API client for open-source talent collection.

Provides authenticated access to GitHub REST API with retry,
rate-limit handling, multi-token rotation, request throttling,
and proxy support.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, cast

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.services.common.http_client import HttpClientFactory

logger = logging.getLogger(__name__)


class GitHubClient:
    """Async GitHub REST API client with rate-limit awareness."""

    def __init__(self, token: str | None = None, base_url: str | None = None) -> None:
        self.base_url = (base_url or settings.GITHUB_BASE_URL).rstrip("/")
        self.tokens = self._parse_tokens(token)
        self.current_token_idx = 0
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "AI4TALENTS/2.0.0",
        }
        self._client: httpx.AsyncClient | None = None
        self._last_request_time: float = 0.0
        self._min_interval: float = 0.2  # 200ms between requests

    @staticmethod
    def _parse_tokens(token: str | None) -> list[str]:
        if token:
            return [t.strip() for t in token.split(",") if t.strip()]
        tokens = settings.GITHUB_TOKENS
        if tokens:
            return [t.strip() for t in tokens.split(",") if t.strip()]
        return []

    def _current_token(self) -> str | None:
        if not self.tokens:
            return None
        return self.tokens[self.current_token_idx % len(self.tokens)]

    def _switch_token(self) -> bool:
        if len(self.tokens) <= 1:
            return False
        self.current_token_idx = (self.current_token_idx + 1) % len(self.tokens)
        self._update_auth_header()
        return True

    def _update_auth_header(self) -> None:
        token = self._current_token()
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
        elif "Authorization" in self.headers:
            del self.headers["Authorization"]

    async def __aenter__(self) -> GitHubClient:
        self._update_auth_header()
        self._client = HttpClientFactory.create_client_for_url(
            target_url=self.base_url,
            timeout=30.0,
            headers=self.headers,
            follow_redirects=True,
        )
        logger.info(
            f"GitHubClient initialized with {len(self.tokens)} token(s), "
            f"base_url={self.base_url}"
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()

    async def _throttle(self) -> None:
        """Ensure minimum interval between requests."""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self._min_interval:
            await asyncio.sleep(self._min_interval - elapsed)

    async def _rebuild_client(self) -> None:
        """Rebuild httpx client with updated auth headers."""
        if self._client:
            await self._client.aclose()
        self._client = HttpClientFactory.create_client_for_url(
            target_url=self.base_url,
            timeout=30.0,
            headers=self.headers,
            follow_redirects=True,
        )

    async def _do_get(
        self, path: str, params: dict[str, Any] | None = None
    ) -> httpx.Response:
        """Execute GET request with throttling."""
        await self._throttle()
        if not self._client:
            raise RuntimeError("Client not initialized. Use async with.")
        url = f"{self.base_url}{path}"
        response = await self._client.get(url, params=params)
        self._last_request_time = time.time()
        return response

    @retry(
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.NetworkError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Generic GET with rate-limit handling, token rotation, and retry."""
        response = await self._do_get(path, params)

        if response.status_code == 404:
            logger.warning(f"GitHub API 404: {path}")
            return {}

        if response.status_code in (403, 429):
            reset_at = response.headers.get("X-RateLimit-Reset")
            remaining = response.headers.get("X-RateLimit-Remaining")
            logger.warning(
                f"GitHub rate limit hit for {path}, remaining={remaining}, "
                f"reset_at={reset_at}, token_idx={self.current_token_idx}"
            )

            # Try switching to next token
            if self._switch_token():
                logger.info(f"Switched to token #{self.current_token_idx + 1}")
                await self._rebuild_client()
                response = await self._do_get(path, params)
            elif reset_at:
                # No more tokens; wait until rate limit resets
                wait_seconds = max(0, int(reset_at) - int(time.time()) + 1)
                wait_seconds = min(wait_seconds, 3600)  # Cap at 1 hour
                logger.warning(
                    f"All tokens exhausted. Waiting {wait_seconds}s for rate limit reset."
                )
                await asyncio.sleep(wait_seconds)
                response = await self._do_get(path, params)

        response.raise_for_status()
        return response.json()

    async def get_repo(self, owner: str, repo: str) -> dict[str, Any]:
        """Fetch repository details."""
        return cast(dict[str, Any], await self._get(f"/repos/{owner}/{repo}"))

    async def list_contributors(
        self, owner: str, repo: str, max_count: int = 30
    ) -> list[dict[str, Any]]:
        """Fetch repository contributors with pagination.

        GitHub API max per_page is 100. Iterates pages until *max_count*
        contributors are collected or no more pages exist.

        Pass ``max_count=0`` to collect **all** contributors the API
        exposes (hard-capped at 500 by GitHub).
        """
        all_contributors: list[dict[str, Any]] = []
        page = 1
        per_page = min(100, max_count) if max_count > 0 else 100
        while max_count <= 0 or len(all_contributors) < max_count:
            batch = cast(
                list[dict[str, Any]],
                await self._get(
                    f"/repos/{owner}/{repo}/contributors",
                    params={"per_page": per_page, "page": page},
                ),
            )
            if not batch:
                break
            all_contributors.extend(batch)
            if len(batch) < per_page:
                break
            page += 1
        return all_contributors[:max_count] if max_count > 0 else all_contributors

    async def count_contributors(self, owner: str, repo: str) -> tuple[int, bool]:
        """Quickly count total contributors, detecting the 500 API cap.

        Returns:
            (count, is_capped): *count* is the number of contributors
            actually visible through the API; *is_capped* is ``True``
            when the 500-person hard limit was hit.

        Cost: 1 API call for small repos (<100), up to 5 calls for
        large repos that hit the 500 cap.
        """
        count = 0
        page = 1
        per_page = 100
        while True:
            batch = cast(
                list[dict[str, Any]],
                await self._get(
                    f"/repos/{owner}/{repo}/contributors",
                    params={"per_page": per_page, "page": page},
                ),
            )
            if not batch:
                break
            count += len(batch)
            if len(batch) < per_page:
                break
            if count >= 500:
                return count, True
            page += 1
        return count, False

    async def get_user(self, login: str) -> dict[str, Any]:
        """Fetch user profile."""
        return cast(dict[str, Any], await self._get(f"/users/{login}"))

    async def list_user_repos(
        self, login: str, per_page: int = 100
    ) -> list[dict[str, Any]]:
        """Fetch user's public repositories.

        GitHub API max per_page is 100. Single-page fetch to minimize
        rate limit consumption; covers the vast majority of users.
        """
        return cast(list[dict[str, Any]], await self._get(
            f"/users/{login}/repos",
            params={"per_page": per_page, "page": 1, "sort": "updated"},
        ))

    async def get_repo_languages(self, owner: str, repo: str) -> dict[str, int]:
        """Fetch repository language breakdown."""
        return cast(dict[str, int], await self._get(f"/repos/{owner}/{repo}/languages"))

    async def list_commits(
        self, owner: str, repo: str, sha: str | None = None, per_page: int = 100, page: int = 1
    ) -> list[dict[str, Any]]:
        """Fetch repository commits with pagination.

        Commits are returned in reverse chronological order (newest first).
        Each commit contains ``author.login`` when the commit email is linked
        to a GitHub account; otherwise ``author`` is ``None``.
        """
        params: dict[str, Any] = {"per_page": per_page, "page": page}
        if sha:
            params["sha"] = sha
        return cast(list[dict[str, Any]], await self._get(f"/repos/{owner}/{repo}/commits", params))

    async def list_contributors_via_commits(
        self, owner: str, repo: str, max_count: int = 1000
    ) -> list[dict[str, Any]]:
        """Fetch contributors by traversing the commits API.

        This bypasses the hard 500-contributor limit of the ``/contributors``
        endpoint by counting commits per GitHub login across the entire
        commit history, then returning the top *max_count* contributors
        sorted by commit count (descending).

        Pass ``max_count=0`` to collect **all** contributors found in the
        commit history (subject to the 250k commits API cap).

        **Trade-offs vs. contributors API:**
        - ✅ No 500-person cap; works for any repository size.
        - ✅ Returns approximate contribution ranking (by commit count).
        - ❌ Requires more API calls (~N/100 for N commits).
        - ❌ Misses contributors whose commit email is not linked to a
             GitHub account (``author`` is ``None`` in the commit payload).

        GitHub caps the commits API at ~250,000 results; we enforce a
        2,500-page safety limit (250k commits / 100 per_page).
        """
        commit_counts: dict[str, int] = {}
        page = 1
        per_page = 100
        max_pages = 2500  # Safety cap: 2500 * 100 = 250k commits

        while True:
            commits = await self.list_commits(owner, repo, per_page=per_page, page=page)
            if not commits:
                break

            for commit in commits:
                author = commit.get("author")
                if author and isinstance(author, dict) and author.get("login"):
                    login = author["login"]
                    commit_counts[login] = commit_counts.get(login, 0) + 1

            if len(commits) < per_page:
                break

            page += 1
            if page > max_pages:
                logger.warning(
                    f"Commits API pagination capped at {max_pages} pages "
                    f"for {owner}/{repo}"
                )
                break

        # Sort by commit count descending and shape like contributors API response
        sorted_items = sorted(commit_counts.items(), key=lambda x: x[1], reverse=True)
        limit = max_count if max_count > 0 else None
        return [
            {"login": login, "contributions": count}
            for login, count in sorted_items[:limit]
        ]
