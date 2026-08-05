"""
Open Source Repository - developers queries.

Split from core.py; methods are mixed into OpenSourceCoreRepository.
"""

from __future__ import annotations

from typing import Any
from typing import cast as tcast

from sqlalchemy import and_, cast, exists, func, or_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import array as pg_array
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.open_source.models.open_source import (
    OSContribution,
    OSDeveloper,
    OSLanguageSkill,
    OSRepository,
)


class DevelopersMixin:
    """Developer and repository query operations."""

    session: AsyncSession

    async def list_developers(
        self,
        filters: dict[str, Any] | None = None,
        sort_by: str = "stars_desc",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[OSDeveloper], int]:
        """List developers with filters and pagination."""
        filters = filters or {}
        conditions: list[Any] = [OSDeveloper.is_visible.is_(True)]

        q = filters.get("q")
        tech_elements = filters.get("tech_elements")
        languages = filters.get("languages")
        location = filters.get("location")
        company = filters.get("company")
        min_stars = filters.get("min_stars")

        if q:
            pattern = f"%{q}%"
            conditions.append(
                or_(
                    OSDeveloper.name.ilike(pattern),
                    OSDeveloper.bio.ilike(pattern),
                    OSDeveloper.company.ilike(pattern),
                    OSDeveloper.location.ilike(pattern),
                    OSDeveloper.github_login.ilike(pattern),
                )
            )
        if tech_elements:
            conditions.append(
                OSDeveloper.tech_tags.cast(JSONB).op("@>")(cast(tech_elements, JSONB))
            )
        if languages:
            conditions.append(
                OSDeveloper.primary_languages.cast(JSONB).op("?|")(pg_array(languages))
            )
        if location:
            conditions.append(OSDeveloper.location.ilike(f"%{location}%"))
        if company:
            conditions.append(OSDeveloper.company.ilike(f"%{company}%"))
        if min_stars is not None:
            conditions.append(OSDeveloper.total_stars_received >= min_stars)

        is_committer = filters.get("is_committer")
        if is_committer:
            conditions.append(
                exists().where(
                    OSContribution.developer_id == OSDeveloper.developer_id,
                    OSContribution.is_committer.is_(True),
                )
            )

        is_student = filters.get("is_student")
        if is_student is not None:
            conditions.append(OSDeveloper.is_student.is_(bool(is_student)))

        repo_full_names = filters.get("repo_full_names")
        if repo_full_names:
            conditions.append(
                exists().where(
                    OSContribution.developer_id == OSDeveloper.developer_id,
                    OSContribution.repo_id == OSRepository.repo_id,
                    OSRepository.full_name.in_(repo_full_names),
                )
            )

        stmt = select(OSDeveloper).where(and_(*conditions))
        order_map: dict[str, Any] = {
            "stars_desc": OSDeveloper.total_stars_received.desc(),
            "stars_asc": OSDeveloper.total_stars_received.asc(),
            "name_asc": OSDeveloper.name.asc(),
        }
        stmt = stmt.order_by(order_map.get(sort_by, OSDeveloper.total_stars_received.desc()))

        total = await self.session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_developer(
        self,
        developer_id: int,
    ) -> OSDeveloper | None:
        """Get developer by ID."""
        result = await self.session.execute(
            select(OSDeveloper).where(OSDeveloper.developer_id == developer_id)
        )
        return tcast(OSDeveloper | None, result.scalar_one_or_none())

    async def get_developer_repositories(
        self,
        developer_id: int,
    ) -> list[OSRepository]:
        """Get repositories for a developer, ordered by stars desc."""
        result = await self.session.execute(
            select(OSRepository)
            .where(OSRepository.developer_id == developer_id)
            .order_by(OSRepository.stars_count.desc())
        )
        return list(result.scalars().all())

    async def get_developer_contributions(
        self,
        developer_id: int,
    ) -> list[tuple[OSContribution, str]]:
        """Get contributions for a developer with repo full names."""
        result = await self.session.execute(
            select(OSContribution, OSRepository.full_name)
            .join(OSRepository, OSContribution.repo_id == OSRepository.repo_id)
            .where(OSContribution.developer_id == developer_id)
        )
        return tcast("list[tuple[OSContribution, str]]", list(result.all()))

    async def get_contribution_roles_for_developers(
        self,
        developer_ids: list[int],
    ) -> dict[int, list[str]]:
        """Batch aggregate contribution role tags (Owner/Committer) for developers.

        Single grouped query to avoid per-developer N+1 lookups in list views.
        """
        if not developer_ids:
            return {}
        result = await self.session.execute(
            select(
                OSContribution.developer_id,
                func.bool_or(OSContribution.is_owner),
                func.bool_or(OSContribution.is_committer),
            )
            .where(OSContribution.developer_id.in_(developer_ids))
            .group_by(OSContribution.developer_id)
        )
        roles_map: dict[int, list[str]] = {}
        for dev_id, is_owner, is_committer in result.all():
            roles: list[str] = []
            if is_committer:
                roles.append("Committer")
            if is_owner:
                roles.append("Owner")
            roles_map[dev_id] = roles
        return roles_map

    async def get_developer_languages(
        self,
        developer_id: int,
    ) -> list[OSLanguageSkill]:
        """Get language skills for a developer, ordered by proficiency desc."""
        result = await self.session.execute(
            select(OSLanguageSkill)
            .where(OSLanguageSkill.developer_id == developer_id)
            .order_by(OSLanguageSkill.proficiency_score.desc())
        )
        return list(result.scalars().all())

    async def get_similar_developers(
        self,
        developer_id: int,
        limit: int = 5,
    ) -> list[OSDeveloper]:
        """Get similar developers (random sampling for now)."""
        result = await self.session.execute(
            select(OSDeveloper)
            .where(OSDeveloper.developer_id != developer_id, OSDeveloper.is_visible.is_(True))
            .order_by(func.random())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_developers_by_ids(
        self,
        developer_ids: list[int],
    ) -> list[OSDeveloper]:
        """Get multiple developers by IDs."""
        if not developer_ids:
            return []
        result = await self.session.execute(
            select(OSDeveloper).where(OSDeveloper.developer_id.in_(developer_ids))
        )
        return list(result.scalars().all())

    # ========== Repository (Project) ==========

    async def get_repository_by_id(self, repo_id: int) -> OSRepository | None:
        """Get a repository by its ID."""
        result = await self.session.execute(
            select(OSRepository).where(OSRepository.repo_id == repo_id)
        )
        return tcast(OSRepository | None, result.scalar_one_or_none())

    async def get_repository_by_full_name(self, full_name: str) -> OSRepository | None:
        """Get a repository by its full name (owner/repo)."""
        result = await self.session.execute(
            select(OSRepository)
            .where(OSRepository.full_name == full_name)
            .order_by(OSRepository.stars_count.desc())
            .limit(1)
        )
        return tcast(OSRepository | None, result.scalar_one_or_none())

    async def get_repository_contributors(
        self,
        repo_id: int,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[tuple[OSDeveloper, OSContribution]], int]:
        """Get contributors for a repository with their contribution records, ordered by commits desc."""
        stmt = (
            select(OSDeveloper, OSContribution)
            .join(OSContribution, OSDeveloper.developer_id == OSContribution.developer_id)
            .where(OSContribution.repo_id == repo_id)
            .order_by(OSContribution.commits_count.desc())
        )
        total = await self.session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        return tcast("list[tuple[OSDeveloper, OSContribution]]", list(result.all())), total

    async def count_repository_contributors(self, repo_id: int) -> int:
        """Count distinct contributors for a repository."""
        result = await self.session.scalar(
            select(func.count(func.distinct(OSContribution.developer_id))).where(
                OSContribution.repo_id == repo_id
            )
        )
        return result or 0

    # ========== Favourite ==========
