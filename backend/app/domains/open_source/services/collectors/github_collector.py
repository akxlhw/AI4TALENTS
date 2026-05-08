"""Single-repository GitHub collector for open-source talent.

Collects contributors from a single repository, fetches their profiles,
repositories, and language statistics, then persists to the database.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
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
            started_at=datetime.utcnow(),
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

        stars = repo_info.get("stargazers_count", 0) or 0
        forks = repo_info.get("forks_count", 0) or 0
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

        # Step 3-5: Process each contributor serially
        # Each contributor uses an independent transaction to ensure failure isolation.
        for idx, contributor in enumerate(contributors, 1):
            if await self._is_cancelled(ctx):
                return

            login = contributor.get("login")
            if not login:
                continue

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

            # Small delay between contributors to avoid rate limiting
            if idx < total:
                await asyncio.sleep(0.5)

            # Update progress every contributor
            progress = 20 + int((idx / total) * 70)
            await self._update_task(ctx.task_id, processed_records=idx, progress_percent=min(progress, 90))

        # Step 6: Done
        await self._update_task(
            ctx.task_id,
            status="completed",
            progress_percent=100,
            current_step="completed",
            completed_at=datetime.utcnow(),
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
        """Process a single contributor: profile → repos → languages → sync."""
        try:
            # Fetch profile
            user = await self.client.get_user(login)
            if not user:
                logger.warning(f"User not found: {login}")
                return

            # Build developer data
            dev_data = self._build_developer_data(user, ctx.tech_element)
            dev = await sync.upsert_developer(dev_data)

            # Fetch user's repos (GitHub max 100 per page, single fetch)
            user_repos = await self.client.list_user_repos(login, per_page=100)
            if await self._is_cancelled(ctx):
                return

            # Aggregate languages across repos using 'language' field from list_user_repos
            # (avoiding per-repo get_repo_languages API calls which consume rate limit heavily)
            lang_stats: dict[str, dict[str, Any]] = {}
            total_stars = 0
            total_forks = 0

            # Step 1: Create contribution for the TARGET repo (always, regardless of whether
            # it appears in the user's own repo list). This is where role detection lives.
            target_full_name = repo_info.get("full_name", "")
            if repo_info and target_full_name:
                target_owner, target_repo_name = target_full_name.split("/", 1)
                target_repo_data = {
                    "github_repo_id": repo_info.get("id"),
                    "full_name": target_full_name,
                    "name": target_repo_name,
                    "language": repo_info.get("language"),
                    "stars_count": repo_info.get("stargazers_count", 0) or 0,
                    "forks_count": repo_info.get("forks_count", 0) or 0,
                    "topics": repo_info.get("topics", []),
                    "is_fork": repo_info.get("fork", False),
                }
                target_repo_obj = await sync.upsert_repository(dev.developer_id, target_repo_data)

                # Role detection for target repo only
                is_owner = target_owner == login
                is_committer = contributor.get("is_committer", False)

                await sync.upsert_contribution(
                    dev.developer_id,
                    target_repo_obj.repo_id,
                    {
                        "commits_count": contributor.get("contributions", 0),
                        "prs_count": 0,
                        "issues_count": 0,
                        "code_reviews_count": 0,
                        "is_owner": is_owner,
                        "is_maintainer": False,
                        "is_committer": is_committer,
                    },
                )

            # Step 2: Process user's OWN repos (no roles, just stats)
            for ur in user_repos:
                if await self._is_cancelled(ctx):
                    return

                # Skip target repo if it happens to be in the user's repo list
                # (already handled above with correct roles)
                if ur.get("full_name") == target_full_name:
                    continue

                # Language stats from repo's primary language
                lang = ur.get("language")
                if lang:
                    if lang not in lang_stats:
                        lang_stats[lang] = {"repo_count": 0}
                    lang_stats[lang]["repo_count"] += 1

                total_stars += ur.get("stargazers_count", 0) or 0
                total_forks += ur.get("forks_count", 0) or 0

                owner_name = ur.get("owner", {}).get("login", "")
                repo_name = ur.get("name", "")
                if not owner_name or not repo_name:
                    continue

                # Upsert repository
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
                repo_obj = await sync.upsert_repository(dev.developer_id, repo_data)

                # No role detection for user's own repos
                await sync.upsert_contribution(
                    dev.developer_id,
                    repo_obj.repo_id,
                    {
                        "commits_count": 0,
                        "prs_count": 0,
                        "issues_count": 0,
                        "code_reviews_count": 0,
                        "is_owner": False,
                        "is_maintainer": False,
                        "is_committer": False,
                    },
                )

            # Update developer totals
            dev.total_stars_received = total_stars
            dev.total_forks_received = total_forks
            dev.primary_languages = list(lang_stats.keys())[:5]
            await sync.session.flush()

            # Calculate and upsert language skills (proficiency based on repo count proportion)
            total_repos_with_lang = sum(s["repo_count"] for s in lang_stats.values())
            for lang, stats in lang_stats.items():
                proportion = stats["repo_count"] / total_repos_with_lang if total_repos_with_lang > 0 else 0
                proficiency = min(proportion * 10, 10.0)  # Cap at 10.0
                skill_data = {
                    "repo_count": stats["repo_count"],
                    "total_commits": 0,
                    "proficiency_score": round(proficiency, 2),
                }
                await sync.upsert_language_skill(dev.developer_id, lang, skill_data)

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
            "followers_count": user.get("followers", 0) or 0,
            "following_count": user.get("following", 0) or 0,
            "public_repos_count": user.get("public_repos", 0) or 0,
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
