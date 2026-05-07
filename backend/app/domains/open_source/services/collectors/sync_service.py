"""Database sync service for open-source collection results.

Handles upsert of developers, repositories, contributions, and language skills.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.open_source.models.open_source import (
    OSContribution,
    OSDeveloper,
    OSLanguageSkill,
    OSRepository,
)

logger = logging.getLogger(__name__)


class SyncService:
    """Sync collected GitHub data into the database."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_developer(self, data: dict[str, Any]) -> OSDeveloper:
        """Upsert a developer by github_id (primary) or github_login (fallback)."""
        github_id = data.get("github_id")
        login = data.get("github_login")
        dev: OSDeveloper | None = None

        # Primary lookup by github_id (stable across login renames)
        if github_id:
            stmt = select(OSDeveloper).where(OSDeveloper.github_id == github_id)
            result = await self.session.execute(stmt)
            dev = result.scalar_one_or_none()

        # Fallback lookup by github_login
        if dev is None and login:
            stmt = select(OSDeveloper).where(OSDeveloper.github_login == login)
            result = await self.session.execute(stmt)
            dev = result.scalar_one_or_none()

        if dev is None:
            dev = OSDeveloper(github_login=login or "")
            self.session.add(dev)

        # Update fields
        for key in [
            "github_id", "name", "bio", "location", "company",
            "blog_url", "email", "avatar_url", "followers_count",
            "following_count", "public_repos_count", "total_stars_received",
            "total_forks_received", "primary_languages", "tech_tags", "is_visible",
        ]:
            if key in data and data[key] is not None:
                setattr(dev, key, data[key])

        await self.session.flush()
        return dev

    async def upsert_repository(
        self, developer_id: int, data: dict[str, Any]
    ) -> OSRepository:
        """Upsert a repository by full_name for a given developer."""
        full_name = data["full_name"]
        stmt = select(OSRepository).where(OSRepository.full_name == full_name)
        result = await self.session.execute(stmt)
        repo = result.scalar_one_or_none()

        if repo is None:
            repo = OSRepository(full_name=full_name)
            self.session.add(repo)

        repo.developer_id = developer_id
        for key in [
            "github_repo_id", "name", "language", "stars_count",
            "forks_count", "topics", "is_fork",
        ]:
            if key in data and data[key] is not None:
                setattr(repo, key, data[key])

        await self.session.flush()
        return repo

    async def upsert_contribution(
        self, developer_id: int, repo_id: int, data: dict[str, Any]
    ) -> OSContribution:
        """Upsert a contribution record."""
        stmt = select(OSContribution).where(
            OSContribution.developer_id == developer_id,
            OSContribution.repo_id == repo_id,
        )
        result = await self.session.execute(stmt)
        contrib = result.scalar_one_or_none()

        if contrib is None:
            contrib = OSContribution(developer_id=developer_id, repo_id=repo_id)
            self.session.add(contrib)

        for key in [
            "commits_count", "prs_count", "issues_count",
            "code_reviews_count", "is_owner", "is_maintainer", "is_committer",
        ]:
            if key in data and data[key] is not None:
                setattr(contrib, key, data[key])

        await self.session.flush()
        return contrib

    async def upsert_language_skill(
        self, developer_id: int, language: str, data: dict[str, Any]
    ) -> OSLanguageSkill:
        """Upsert a language skill record."""
        stmt = select(OSLanguageSkill).where(
            OSLanguageSkill.developer_id == developer_id,
            OSLanguageSkill.language == language,
        )
        result = await self.session.execute(stmt)
        skill = result.scalar_one_or_none()

        if skill is None:
            skill = OSLanguageSkill(developer_id=developer_id, language=language)
            self.session.add(skill)

        for key in ["repo_count", "total_commits", "proficiency_score"]:
            if key in data and data[key] is not None:
                setattr(skill, key, data[key])

        await self.session.flush()
        return skill
