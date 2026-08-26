"""GitHub business API - endpoint wrappers over the transport layer.

One method per GitHub REST endpoint used by the collection pipeline. All
request execution (throttling, token rotation, retry, breaker) is delegated
to ``github_transport.GitHubTransport``; this module holds only endpoint
knowledge (paths, pagination shapes, response shaping).
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, cast

from app.core.config import settings
from app.domains.open_source.services.github_transport import (
    GitHubTransport,
    HTTPStatusError,
    RateLimitExhaustedError,
)
from app.domains.shared.services.common.circuit_breaker import CircuitBreakerOpenError

logger = logging.getLogger(__name__)


class GitHubApi:
    """GitHub REST endpoint wrappers."""

    def __init__(self, transport: GitHubTransport) -> None:
        self.transport = transport

    async def get_repo(self, owner: str, repo: str) -> dict[str, Any]:
        """Fetch repository details."""
        return cast(dict[str, Any], await self.transport.get(f"/repos/{owner}/{repo}"))

    async def search_repositories(
        self,
        query: str,
        sort: str = "stars",
        order: str = "desc",
        per_page: int = 20,
    ) -> dict[str, Any]:
        """Search repositories. Returns {"items": [...], "total_count": N}.

        Note: the Search API has a separate rate limit (30 req/min
        authenticated, 10 unauthenticated) — callers must throttle between
        searches. The shared token rotation / 429 retry infra still applies.
        """
        return cast(
            dict[str, Any],
            await self.transport.get(
                "/search/repositories",
                {"q": query, "sort": sort, "order": order, "per_page": per_page},
            ),
        )

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
                await self.transport.get(
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

    async def count_contributors(self, owner: str, repo: str) -> int:
        """Approximate the contributor count via Link-header pagination.

        Requests a single contributor per page; GitHub's Link response header
        exposes the last page number, which equals the contributor count.
        This is 1 lightweight API call regardless of repo size (paging the
        full list instead triggers abuse-detection 403s on huge repos).

        Returns -1 when the count cannot be determined (404, or the 403
        "list too large" GitHub gives for mega repos like the linux kernel)
        so callers can fail open.
        """
        try:
            response = await self.transport.do_get_full(
                f"/repos/{owner}/{repo}/contributors",
                {"per_page": 1, "anon": "false"},
            )
        except HTTPStatusError as e:
            logger.warning(
                "Contributor count unavailable for %s/%s: HTTP %s",
                owner,
                repo,
                e.response.status_code,
            )
            return -1
        if response is None:
            return -1
        data = response.json()
        if not data:
            return 0
        link = response.headers.get("link", "")
        match = re.search(r"[?&]page=(\d+)>; rel=\"last\"", link)
        return int(match.group(1)) if match else 1

    async def get_user(self, login: str) -> dict[str, Any]:
        """Fetch user profile."""
        return cast(dict[str, Any], await self.transport.get(f"/users/{login}"))

    async def list_user_repos(self, login: str, per_page: int = 100) -> list[dict[str, Any]]:
        """Fetch user's public repositories.

        GitHub API max per_page is 100. Single-page fetch to minimize
        rate limit consumption; covers the vast majority of users.
        """
        return cast(
            list[dict[str, Any]],
            await self.transport.get(
                f"/users/{login}/repos",
                params={"per_page": per_page, "page": 1, "sort": "updated"},
            ),
        )

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
        return cast(
            list[dict[str, Any]], await self.transport.get(f"/repos/{owner}/{repo}/commits", params)
        )

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
                if isinstance(commits, RateLimitExhaustedError):
                    # Token pool exhausted: abort the traversal fast instead of
                    # grinding through hundreds of futile pages.
                    raise commits
                if isinstance(commits, CircuitBreakerOpenError):
                    # Transport breaker OPEN: same fast-abort contract — every
                    # further page would be rejected instantly anyway.
                    raise commits
                if isinstance(commits, BaseException):
                    logger.warning(
                        f"Failed to fetch commits page {page_num} for {owner}/{repo}: {commits}"
                    )
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

                    # Committer (GitHub user who actually committed the code)
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
                    f"Commits API pagination capped at {max_pages} pages " f"for {owner}/{repo}"
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
