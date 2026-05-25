"""Single-repository GitHub collector for open-source talent.

Collects contributors from a single repository, fetches their profiles,
repositories, and language statistics, then persists to the database.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.core.database import AsyncSessionLocal
from app.domains.open_source.models.open_source import OSCollectTask
from app.domains.open_source.services.collectors.sync_service import SyncService
from app.domains.open_source.services.github_client import GitHubClient

logger = logging.getLogger(__name__)


@dataclass
class CollectContext:
    """Shared context for a single collection run."""

    task_id: int
    repo_config_id: int
    repo_full_name: str
    tech_element: str
    contributors_per_repo: int
    cancelled: asyncio.Event = field(default_factory=asyncio.Event)


class GitHubCollector:
    """Collect open-source talent data from a single GitHub repository."""

    def __init__(self, client: GitHubClient) -> None:
        self.client = client

    # ============= Step helpers =============

    async def _update_task(
        self, task_id: int, **kwargs: Any
    ) -> None:
        """Update task progress in the database."""
        async with AsyncSessionLocal() as session:
            task = await session.get(OSCollectTask, task_id)
            if task:
                for key, value in kwargs.items():
                    if hasattr(task, key):
                        setattr(task, key, value)
                await session.commit()

    async def _is_cancelled(self, ctx: CollectContext) -> bool:
        if ctx.cancelled.is_set():
            await self._update_task(ctx.task_id, status="cancelled")
            return True
        return False

    # ============= Main flow =============

    async def collect(self, ctx: CollectContext) -> None:
        """Run the full collection pipeline for a single repository."""
        logger.info(f"Starting collection for repo {ctx.repo_full_name}, task={ctx.task_id}")
        await self._update_task(
            ctx.task_id,
            status="running",
            current_step="fetch_repo",
            started_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )

        try:
            owner, repo_name = ctx.repo_full_name.split("/", 1)
        except ValueError as err:
            raise ValueError(f"Invalid repo_full_name: {ctx.repo_full_name}") from err

        # Step 1: Fetch repo details & sync stars to config
        repo_info = await self.client.get_repo(owner, repo_name)
        if await self._is_cancelled(ctx):
            return
        if not repo_info:
            raise ValueError(f"Repository not found: {ctx.repo_full_name}")

        stars = repo_info.get("stargazers_count") or 0
        forks = repo_info.get("forks_count") or 0
        logger.info(f"Repo {ctx.repo_full_name}: stars={stars}, forks={forks}")

        # Update os_repo_config stars_count so Trending list stays current
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select

            from app.domains.open_source.models.open_source import OSRepoConfig
            config = await session.scalar(
                select(OSRepoConfig).where(OSRepoConfig.repo_full_name == ctx.repo_full_name)
            )
            if config:
                config.stars_count = stars
                await session.commit()

        await self._update_task(ctx.task_id, current_step="fetch_contributors", progress_percent=10)

        # Step 2: Fetch contributors
        # Strategy:
        #   - contributors_per_repo <= 0 : collect ALL (commits API, no limit)
        #   - contributors_per_repo > 500 : collect specified count via commits API
        #   - 1 <= contributors_per_repo <= 500 : collect via contributors API
        if ctx.contributors_per_repo <= 0:
            logger.info(f"Collect-all mode for {ctx.repo_full_name}")
            contributors = await self.client.list_contributors_via_commits(
                owner, repo_name, max_count=0
            )
        elif ctx.contributors_per_repo > 500:
            logger.info(
                f"Requesting {ctx.contributors_per_repo} contributors (>500 cap); "
                f"switching to commits API traversal for {ctx.repo_full_name}"
            )
            contributors = await self.client.list_contributors_via_commits(
                owner, repo_name, ctx.contributors_per_repo
            )
        else:
            contributors = await self.client.list_contributors(
                owner, repo_name, ctx.contributors_per_repo
            )
        if await self._is_cancelled(ctx):
            return
        total = len(contributors)
        logger.info(f"Fetched {total} contributors from {ctx.repo_full_name}")
        await self._update_task(ctx.task_id, total_records=total, current_step="fetch_profiles", progress_percent=20)

        # Step 3-5: Process contributors concurrently with semaphore
        # Each contributor uses an independent transaction to ensure failure isolation.
        sem = asyncio.Semaphore(5)
        processed = 0

        async def _process_one(contributor: dict[str, Any]) -> None:
            nonlocal processed
            if await self._is_cancelled(ctx):
                return

            login = contributor.get("login")
            if not login:
                return

            async with sem:
                try:
                    async with AsyncSessionLocal() as session:
                        sync = SyncService(session)
                        await self._process_contributor(
                            ctx, login, sync, repo_info, contributor
                        )
                        await session.commit()
                except Exception as e:
                    logger.exception(f"Failed to process contributor {login}: {e}")
                    # Continue with next contributor; partial failures are logged but not fatal.

                processed += 1
                # Update progress every contributor
                progress = 20 + int((processed / total) * 70)
                await self._update_task(
                    ctx.task_id,
                    processed_records=processed,
                    progress_percent=min(progress, 90),
                )

        await asyncio.gather(*[_process_one(c) for c in contributors])

        # Step 6: Done
        await self._update_task(
            ctx.task_id,
            status="completed",
            progress_percent=100,
            current_step="completed",
            completed_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        logger.info(f"Collection completed for repo {ctx.repo_full_name}, task={ctx.task_id}")

    async def _process_contributor(
        self,
        ctx: CollectContext,
        login: str,
        sync: SyncService,
        repo_info: dict[str, Any],
        contributor: dict[str, Any],
    ) -> None:
        """Process a single contributor: profile → repos → languages → sync.

        Optimized for batch DB operations with minimal flushes:
        1. Concurrent API calls (get_user + list_user_repos)
        2. Collect all repo/contribution data in memory
        3. Batch upsert repos → single flush → batch upsert contributions → single flush
        4. Batch upsert language skills → single flush
        """
        try:
            # P1: Concurrent API calls — get_user and list_user_repos have no data dependency
            user_task = self.client.get_user(login)
            repos_task = self.client.list_user_repos(login, per_page=100)
            user, user_repos = await asyncio.gather(user_task, repos_task)

            if not user:
                logger.warning(f"User not found: {login}")
                return
            if await self._is_cancelled(ctx):
                return

            # Build developer data and upsert (defer flush)
            dev_data = self._build_developer_data(user, ctx.tech_element)
            dev = await sync.upsert_developer(dev_data, auto_flush=False)

            # Flush once if developer is new (need developer_id for foreign keys)
            if dev.developer_id is None:
                await sync.session.flush()

            # Aggregate languages and totals while collecting repo operations
            lang_stats: dict[str, dict[str, Any]] = {}
            total_stars = 0
            total_forks = 0
            repo_ops: list[tuple[str, dict[str, Any], dict[str, Any]]] = []

            # Step 1: Target repo contribution (always create, role detection lives here)
            # Use ctx.repo_full_name (the configured name) instead of repo_info["full_name"]
            # to handle GitHub repo renames/redirects. The configured name is the stable
            # identifier that users see and click on.
            target_full_name = ctx.repo_full_name
            target_owner, target_repo_name = target_full_name.split("/", 1)
            target_repo_data = {
                "github_repo_id": repo_info.get("id"),
                "full_name": target_full_name,
                "name": target_repo_name,
                "language": repo_info.get("language"),
                "stars_count": repo_info.get("stargazers_count") or 0,
                "forks_count": repo_info.get("forks_count") or 0,
                "topics": repo_info.get("topics", []),
                "is_fork": repo_info.get("fork", False),
            }
            is_owner = target_owner == login
            is_committer = contributor.get("is_committer", False)
            target_contrib_data = {
                "commits_count": contributor.get("contributions", 0),
                "prs_count": 0,
                "issues_count": 0,
                "code_reviews_count": 0,
                "is_owner": is_owner,
                "is_maintainer": False,
                "is_committer": is_committer,
            }
            repo_ops.append(("target", target_repo_data, target_contrib_data))

            # Step 2: Collect user's OWN repos (no roles, just stats)
            for ur in user_repos:
                if await self._is_cancelled(ctx):
                    return

                if ur.get("full_name") == target_full_name:
                    continue

                lang = ur.get("language")
                if lang:
                    if lang not in lang_stats:
                        lang_stats[lang] = {"repo_count": 0}
                    lang_stats[lang]["repo_count"] += 1

                total_stars += ur.get("stargazers_count") or 0
                total_forks += ur.get("forks_count") or 0

                owner_name = ur.get("owner", {}).get("login", "")
                repo_name = ur.get("name", "")
                if not owner_name or not repo_name:
                    continue

                repo_data = {
                    "github_repo_id": ur.get("id"),
                    "full_name": ur.get("full_name", f"{owner_name}/{repo_name}"),
                    "name": repo_name,
                    "language": lang,
                    "stars_count": ur.get("stargazers_count", 0) or 0,
                    "forks_count": ur.get("forks_count", 0) or 0,
                    "topics": ur.get("topics", []),
                    "is_fork": ur.get("fork", False),
                }
                contrib_data = {
                    "commits_count": 0,
                    "prs_count": 0,
                    "issues_count": 0,
                    "code_reviews_count": 0,
                    "is_owner": False,
                    "is_maintainer": False,
                    "is_committer": False,
                }
                repo_ops.append(("own", repo_data, contrib_data))

            # Batch upsert all repos (defer flush)
            repo_results: list[tuple[str, Any, dict[str, Any]]] = []
            for kind, repo_data, contrib_data in repo_ops:
                repo_obj = await sync.upsert_repository(dev.developer_id, repo_data, auto_flush=False)
                repo_results.append((kind, repo_obj, contrib_data))

            # Flush ①: allocate repo_ids for newly inserted repos
            await sync.session.flush()

            # Batch upsert all contributions (defer flush)
            for _kind, repo_obj, contrib_data in repo_results:
                await sync.upsert_contribution(dev.developer_id, repo_obj.repo_id, contrib_data, auto_flush=False)

            # Flush ②: persist contributions
            await sync.session.flush()

            # Update developer totals
            dev.total_stars_received = total_stars
            dev.total_forks_received = total_forks
            dev.primary_languages = list(lang_stats.keys())[:5]

            # Flush ③: persist totals
            await sync.session.flush()

            # Batch upsert language skills (defer flush)
            total_repos_with_lang = sum(s["repo_count"] for s in lang_stats.values())
            for lang, stats in lang_stats.items():
                proportion = stats["repo_count"] / total_repos_with_lang if total_repos_with_lang > 0 else 0
                proficiency = min(proportion * 10, 10.0)
                skill_data = {
                    "repo_count": stats["repo_count"],
                    "total_commits": 0,
                    "proficiency_score": round(proficiency, 2),
                }
                await sync.upsert_language_skill(dev.developer_id, lang, skill_data, auto_flush=False)

            # Flush ④: persist language skills
            await sync.session.flush()

        except Exception as e:
            logger.exception(f"Failed to process contributor {login}: {e}")
            # Continue with next contributor; individual failures should not stop the whole task

    @staticmethod
    def _build_developer_data(user: dict[str, Any], tech_element: str) -> dict[str, Any]:
        """Build OSDeveloper fields from GitHub user API response with normalization."""
        raw_name = user.get("name") or user.get("login") or ""
        name = raw_name.strip()[:100] if raw_name else ""

        raw_company = user.get("company") or ""
        company = GitHubCollector._normalize_company(raw_company)

        raw_location = user.get("location") or ""
        location = raw_location.strip()[:100] if raw_location else ""

        raw_blog = user.get("blog") or ""
        blog_url = GitHubCollector._normalize_url(raw_blog)

        raw_email = user.get("email") or ""
        email = raw_email.strip().lower()[:255] if raw_email else ""

        raw_bio = user.get("bio") or ""
        bio = raw_bio.strip()[:500] if raw_bio else ""

        raw_twitter = user.get("twitter_username") or ""
        twitter = raw_twitter.strip().lstrip("@")[:50] if raw_twitter else ""

        return {
            "github_login": user.get("login", ""),
            "github_id": user.get("id"),
            "name": name,
            "bio": bio,
            "location": location,
            "company": company,
            "blog_url": blog_url,
            "email": email,
            "avatar_url": user.get("avatar_url", ""),
            "twitter_username": twitter,
            "followers_count": user.get("followers") or 0,
            "following_count": user.get("following") or 0,
            "public_repos_count": user.get("public_repos") or 0,
            "total_stars_received": 0,
            "total_forks_received": 0,
            "primary_languages": [],
            "tech_tags": [tech_element],
            "is_visible": True,
        }

    @staticmethod
    def _normalize_company(raw: str) -> str:
        """Normalize company name: strip @, URLs, common suffixes."""
        if not raw:
            return ""
        company = raw.strip()
        # Remove @ prefix
        if company.startswith("@"):
            company = company[1:]
        # Remove URL prefix if present
        if company.lower().startswith("http"):
            from urllib.parse import urlparse
            parsed = urlparse(company)
            company = parsed.netloc or parsed.path
            if company.lower().startswith("www."):
                company = company[4:]
        # Remove common suffixes
        for suffix in [" Inc.", " Inc", " Ltd.", " Ltd", " Corp.", " Corp", " LLC", " GmbH", " Co.", " Co"]:
            if company.endswith(suffix):
                company = company[: -len(suffix)]
                break
        return company.strip()[:100]

    @staticmethod
    def _normalize_url(raw: str) -> str:
        """Normalize URL: add https:// prefix, strip trailing slash."""
        if not raw:
            return ""
        url = raw.strip()
        if url and not url.lower().startswith(("http://", "https://")):
            url = "https://" + url
        return url.rstrip("/")[:255]
