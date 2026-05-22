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
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.domains.shared.services.common.circuit_breaker import CircuitBreaker
from app.domains.shared.services.common.http_client import HttpClientFactory

_github_breaker = CircuitBreaker(
    name="github",
    failure_threshold=settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
    recovery_timeout=settings.CIRCUIT_BREAKER_RECOVERY_TIMEOUT,
    window_size=settings.CIRCUIT_BREAKER_WINDOW_SIZE,
)

logger = logging.getLogger(__name__)


def _is_retryable(exc: BaseException) -> bool:
    """Determine if an exception is worth retrying.

    - Network/timeout errors: always retry
    - 429 (rate limit): retry (token may refresh or reset window passes)
    - 5xx (server error): retry (transient)
    - 4xx client errors (401, 403, 404, etc.): do NOT retry
    """
    if isinstance(exc, (httpx.NetworkError, httpx.TimeoutException)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code == 429 or exc.response.status_code >= 500
    return False


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
        # Track per-token rate limit state for intelligent token selection
        self._token_remaining: dict[int, int] = {}
        self._token_reset_at: dict[int, int] = {}

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
        """Rotate to the next token (legacy round-robin). Kept for compatibility."""
        if len(self.tokens) <= 1:
            return False
        self.current_token_idx = (self.current_token_idx + 1) % len(self.tokens)
        self._update_auth_header()
        return True

    def _record_rate_limit(self, headers: httpx.Headers) -> None:
        """Update per-token rate limit state from response headers."""
        remaining = headers.get("X-RateLimit-Remaining")
        reset_at = headers.get("X-RateLimit-Reset")
        if remaining is not None:
            try:
                self._token_remaining[self.current_token_idx] = int(remaining)
            except ValueError:
                pass
        if reset_at is not None:
            try:
                self._token_reset_at[self.current_token_idx] = int(reset_at)
            except ValueError:
                pass

    def _pick_best_token(self) -> None:
        """Switch to the token with the highest remaining quota before making a request."""
        if len(self.tokens) <= 1:
            return
        best_idx = max(
            range(len(self.tokens)),
            key=lambda i: self._token_remaining.get(i, 5000),
        )
        if best_idx != self.current_token_idx:
            self.current_token_idx = best_idx
            self._update_auth_header()

    def _switch_to_best_alternative(self) -> bool:
        """After hitting 403/429, switch to the healthiest alternative token."""
        if len(self.tokens) <= 1:
            return False
        best_idx = max(
            (i for i in range(len(self.tokens)) if i != self.current_token_idx),
            key=lambda i: self._token_remaining.get(i, 5000),
            default=None,
        )
        if best_idx is None:
            return False
        # Only switch if the alternative has meaningful quota left
        if self._token_remaining.get(best_idx, 0) <= 0:
            return False
        self.current_token_idx = best_idx
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
            timeout=settings.HTTP_TIMEOUT_DEFAULT,
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

    async def _do_get_request(
        self, path: str, params: dict[str, Any] | None = None
    ) -> httpx.Response:
        """Execute raw GET request with throttling."""
        await self._throttle()
        if not self._client:
            raise RuntimeError("Client not initialized. Use async with.")
        url = f"{self.base_url}{path}"
        response = await self._client.get(url, params=params)
        self._last_request_time = time.time()
        return response

    async def _do_get(
        self, path: str, params: dict[str, Any] | None = None
    ) -> Any:
        """Core GET logic with rate-limit handling and token rotation."""
        # Proactively pick the healthiest token before each request
        self._pick_best_token()

        response = await self._do_get_request(path, params)

        # Record rate limit state from every response (not just errors)
        self._record_rate_limit(response.headers)

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

            # Try switching to the best alternative token (not round-robin)
            if self._switch_to_best_alternative():
                logger.info(
                    f"Switched to token #{self.current_token_idx + 1} "
                    f"(remaining={self._token_remaining.get(self.current_token_idx, '?')})"
                )
                await self._rebuild_client()
                response = await self._do_get_request(path, params)
            elif reset_at:
                # No more tokens; wait until rate limit resets
                wait_seconds = max(0, int(reset_at) - int(time.time()) + 1)
                wait_seconds = min(wait_seconds, 3600)  # Cap at 1 hour
                logger.warning(
                    f"All tokens exhausted. Waiting {wait_seconds}s for rate limit reset."
                )
                await asyncio.sleep(wait_seconds)
                response = await self._do_get_request(path, params)

        response.raise_for_status()
        return response.json()

    @retry(
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def _get_with_retry(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Retry wrapper around the core request logic."""
        return await self._do_get(path, params)

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Generic GET with circuit breaker, rate-limit handling, token rotation, and retry."""
        if not settings.CIRCUIT_BREAKER_ENABLED:
            return await self._get_with_retry(path, params)
        return await _github_breaker.call(self._get_with_retry, path, params)

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
        per_page = settings.GITHUB_PER_PAGE
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
        committers: set[str] = set()  # Track who has committed (not just authored)
        per_page = settings.GITHUB_PER_PAGE
        max_pages = 2500  # Safety cap: 2500 * 100 = 250k commits
        batch_size = settings.GITHUB_BATCH_SIZE
        current_page = 1

        while current_page <= max_pages:
            batch_end = min(current_page + batch_size - 1, max_pages)
            pages = list(range(current_page, batch_end + 1))

            # Fetch pages concurrently (capped at 5 to stay under abuse thresholds)
            results = await asyncio.gather(
                *[self.list_commits(owner, repo, per_page=per_page, page=p) for p in pages],
                return_exceptions=True,
            )

            should_stop = False
            for i, commits in enumerate(results):
                page_num = current_page + i
                if isinstance(commits, Exception):
                    logger.warning(f"Failed to fetch commits page {page_num} for {owner}/{repo}: {commits}")
                    continue

                if not commits:
                    should_stop = True
                    break

                for commit in commits:
                    # Author (existing logic)
                    author = commit.get("author")
                    if author and isinstance(author, dict) and author.get("login"):
                        login = author["login"]
                        commit_counts[login] = commit_counts.get(login, 0) + 1

                    # Committer (new: GitHub user who actually committed the code)
                    committer = commit.get("committer")
                    if committer and isinstance(committer, dict) and committer.get("login"):
                        committers.add(committer["login"])

                # If this page returned fewer than per_page, we've reached the end
                if len(commits) < per_page:
                    should_stop = True
                    break

            if should_stop:
                break

            current_page = batch_end + 1

            # Cooldown between batches to avoid triggering GitHub abuse detection
            await asyncio.sleep(0.5)

            if current_page > max_pages:
                logger.warning(
                    f"Commits API pagination capped at {max_pages} pages "
                    f"for {owner}/{repo}"
                )
                break

        # Sort by commit count descending and shape like contributors API response
        sorted_items = sorted(commit_counts.items(), key=lambda x: x[1], reverse=True)
        limit = max_count if max_count > 0 else None
        return [
            {
                "login": login,
                "contributions": count,
                "is_committer": login in committers,
            }
            for login, count in sorted_items[:limit]
        ]
