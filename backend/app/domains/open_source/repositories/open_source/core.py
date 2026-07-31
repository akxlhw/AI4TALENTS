"""
Open Source Repository.

Encapsulates all database queries related to open-source talent.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import and_, cast, exists, func, or_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import array as pg_array

from app.domains.open_source.models.open_source import (
    OSCollectTask,
    OSContribution,
    OSDeveloper,
    OSEmbedding,
    OSFavourite,
    OSLanguageSkill,
    OSPoolMember,
    OSRawDeveloper,
    OSRepoConfig,
    OSRepository,
    OSTalentPool,
)

logger = logging.getLogger(__name__)


class OpenSourceCoreRepository:
    """Core CRUD operations for open-source talent."""

    def __init__(self, session):
        self.session = session

    async def list_repo_configs(
        self,
        filters: dict[str, Any] | None = None,
        sort_by: str = "id_desc",
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[OSRepoConfig], int]:
        """List repo configs with filters and pagination."""
        filters = filters or {}
        conditions = []

        tech_elements = filters.get("tech_elements")
        is_active = filters.get("is_active")
        collect_enabled = filters.get("collect_enabled")
        collected_only = filters.get("collected_only", False)
        q = filters.get("q")

        if tech_elements:
            conditions.append(OSRepoConfig.tech_element.in_(tech_elements))
        if is_active is not None:
            conditions.append(OSRepoConfig.is_active == is_active)
        if collect_enabled is not None:
            conditions.append(OSRepoConfig.collect_enabled == collect_enabled)
        if q:
            pattern = f"%{q}%"
            conditions.append(
                or_(
                    OSRepoConfig.repo_full_name.ilike(pattern),
                    OSRepoConfig.display_name.ilike(pattern),
                    OSRepoConfig.description.ilike(pattern),
                )
            )

        stmt = select(OSRepoConfig).where(and_(*conditions)) if conditions else select(OSRepoConfig)

        if collected_only:
            stmt = stmt.where(
                select(OSCollectTask)
                .where(
                    OSCollectTask.task_name == OSRepoConfig.repo_full_name,
                    OSCollectTask.status == "completed",
                )
                .exists()
            )

        total = await self.session.scalar(select(func.count()).select_from(stmt.subquery())) or 0

        if sort_by == "stars":
            stmt = stmt.order_by(OSRepoConfig.stars_count.desc().nullslast())
        else:
            stmt = stmt.order_by(OSRepoConfig.repo_config_id.desc())

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_repo_config(
        self,
        repo_config_id: int,
    ) -> OSRepoConfig | None:
        """Get repo config by ID."""
        result = await self.session.execute(
            select(OSRepoConfig).where(OSRepoConfig.repo_config_id == repo_config_id)
        )
        return result.scalar_one_or_none()

    async def create_repo_config(
        self,
        data: dict[str, Any],
    ) -> OSRepoConfig:
        """Create a new repo config."""
        config = OSRepoConfig(**data)
        self.session.add(config)
        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(config)
        return config

    async def update_repo_config(
        self,
        repo_config_id: int,
        data: dict[str, Any],
    ) -> OSRepoConfig | None:
        """Update repo config by ID."""
        config = await self.get_repo_config(repo_config_id)
        if config is None:
            return None
        for field, value in data.items():
            setattr(config, field, value)
        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(config)
        return config

    async def delete_repo_config(
        self,
        repo_config_id: int,
    ) -> bool:
        """Delete repo config by ID."""
        config = await self.get_repo_config(repo_config_id)
        if config:
            await self.session.delete(config)
            await self.session.flush()
            await self.session.commit()
            return True
        return False

    async def get_repo_config_by_full_name(
        self,
        repo_full_name: str,
    ) -> OSRepoConfig | None:
        """Get repo config by full name."""
        result = await self.session.execute(
            select(OSRepoConfig).where(OSRepoConfig.repo_full_name == repo_full_name)
        )
        return result.scalar_one_or_none()

    # ========== CollectTask ==========

    async def list_collect_tasks(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[OSCollectTask], int]:
        """List collect tasks with pagination."""
        stmt = select(OSCollectTask).order_by(OSCollectTask.created_at.desc())
        total = await self.session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_collect_task(
        self,
        task_id: int,
    ) -> OSCollectTask | None:
        """Get collect task by ID."""
        result = await self.session.execute(
            select(OSCollectTask).where(OSCollectTask.task_id == task_id)
        )
        return result.scalar_one_or_none()

    async def create_collect_task(
        self,
        data: dict[str, Any],
    ) -> OSCollectTask:
        """Create a new collect task."""
        task = OSCollectTask(**data)
        self.session.add(task)
        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def get_active_collect_task(
        self,
        repo_full_name: str,
    ) -> OSCollectTask | None:
        """Get active (pending or running) collect task by repo full name."""
        result = await self.session.execute(
            select(OSCollectTask).where(
                OSCollectTask.task_name == repo_full_name,
                OSCollectTask.status.in_(["pending", "running"]),
            )
        )
        return result.scalar_one_or_none()

    # ========== Developer ==========

    async def list_developers(
        self,
        filters: dict[str, Any] | None = None,
        sort_by: str = "stars_desc",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[OSDeveloper], int]:
        """List developers with filters and pagination."""
        filters = filters or {}
        conditions = [OSDeveloper.is_visible.is_(True)]

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
        order_map = {
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
        return result.scalar_one_or_none()

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
        return list(result.all())

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
        return result.scalar_one_or_none()

    async def get_repository_by_full_name(self, full_name: str) -> OSRepository | None:
        """Get a repository by its full name (owner/repo)."""
        result = await self.session.execute(
            select(OSRepository)
            .where(OSRepository.full_name == full_name)
            .order_by(OSRepository.stars_count.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

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
        return list(result.all()), total

    async def count_repository_contributors(self, repo_id: int) -> int:
        """Count distinct contributors for a repository."""
        result = await self.session.scalar(
            select(func.count(func.distinct(OSContribution.developer_id))).where(
                OSContribution.repo_id == repo_id
            )
        )
        return result or 0

    # ========== Favourite ==========

    async def list_favourites(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        keyword: str | None = None,
    ) -> tuple[list[OSFavourite], int]:
        """List favourites for a user with optional keyword filter."""
        stmt = (
            select(OSFavourite)
            .join(OSDeveloper, OSFavourite.developer_id == OSDeveloper.developer_id)
            .where(OSFavourite.user_id == user_id, OSFavourite.is_active.is_(True))
        )

        if keyword:
            pattern = f"%{keyword}%"
            stmt = stmt.where(
                or_(
                    OSDeveloper.name.ilike(pattern),
                    OSDeveloper.github_login.ilike(pattern),
                )
            )

        total = await self.session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        stmt = (
            stmt.order_by(OSFavourite.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_favourite_ids(
        self,
        user_id: int,
    ) -> list[int]:
        """Get favourite developer IDs for a user."""
        result = await self.session.execute(
            select(OSFavourite.developer_id).where(
                OSFavourite.user_id == user_id, OSFavourite.is_active.is_(True)
            )
        )
        return list(result.scalars().all())

    async def get_favourite(
        self,
        user_id: int,
        developer_id: int,
    ) -> OSFavourite | None:
        """Get a specific favourite record."""
        result = await self.session.execute(
            select(OSFavourite).where(
                OSFavourite.user_id == user_id, OSFavourite.developer_id == developer_id
            )
        )
        return result.scalar_one_or_none()

    async def create_favourite(
        self,
        user_id: int,
        developer_id: int,
        notes: str | None = None,
    ) -> OSFavourite:
        """Create a new favourite."""
        favourite = OSFavourite(
            user_id=user_id,
            developer_id=developer_id,
            notes=notes,
        )
        self.session.add(favourite)
        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(favourite)
        return favourite

    async def update_favourite(
        self,
        favourite: OSFavourite,
        data: dict[str, Any],
    ) -> OSFavourite:
        """Update an existing favourite."""
        for field, value in data.items():
            setattr(favourite, field, value)
        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(favourite)
        return favourite

    async def delete_favourite(
        self,
        favourite: OSFavourite,
    ) -> None:
        """Soft-delete a favourite by setting is_active=False."""
        favourite.is_active = False
        await self.session.flush()
        await self.session.commit()

    # ========== TalentPool ==========

    async def list_talent_pools(
        self,
        user_id: int | None = None,
    ) -> list[OSTalentPool]:
        """List talent pools, optionally filtered by owner."""
        stmt = select(OSTalentPool)
        if user_id is not None:
            stmt = stmt.where(OSTalentPool.owner_user_id == user_id)
        stmt = stmt.order_by(OSTalentPool.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_talent_pool(
        self,
        pool_id: int,
    ) -> OSTalentPool | None:
        """Get talent pool by ID."""
        result = await self.session.execute(
            select(OSTalentPool).where(OSTalentPool.pool_id == pool_id)
        )
        return result.scalar_one_or_none()

    async def create_talent_pool(
        self,
        data: dict[str, Any],
    ) -> OSTalentPool:
        """Create a new talent pool."""
        pool = OSTalentPool(**data)
        self.session.add(pool)
        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(pool)
        return pool

    async def update_talent_pool(
        self,
        pool_id: int,
        data: dict[str, Any],
    ) -> OSTalentPool | None:
        """Update talent pool by ID."""
        pool = await self.get_talent_pool(pool_id)
        if pool is None:
            return None
        for field, value in data.items():
            setattr(pool, field, value)
        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(pool)
        return pool

    async def delete_talent_pool(
        self,
        pool_id: int,
    ) -> None:
        """Delete talent pool by ID."""
        pool = await self.get_talent_pool(pool_id)
        if pool:
            await self.session.delete(pool)
            await self.session.flush()
            await self.session.commit()

    async def get_pool_member(
        self,
        pool_id: int,
        developer_id: int,
    ) -> OSPoolMember | None:
        """Get a specific pool member."""
        result = await self.session.execute(
            select(OSPoolMember).where(
                OSPoolMember.pool_id == pool_id,
                OSPoolMember.developer_id == developer_id,
            )
        )
        return result.scalar_one_or_none()

    async def add_pool_member(
        self,
        pool_id: int,
        developer_id: int,
    ) -> OSPoolMember:
        """Add a developer to a talent pool."""
        member = OSPoolMember(pool_id=pool_id, developer_id=developer_id)
        self.session.add(member)
        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(member)
        return member

    async def remove_pool_member(
        self,
        member: OSPoolMember,
    ) -> None:
        """Remove a member from a talent pool."""
        await self.session.delete(member)
        await self.session.flush()
        await self.session.commit()

    async def list_pool_members(
        self,
        pool_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[OSPoolMember], int]:
        """List members of a talent pool with pagination."""
        stmt = (
            select(OSPoolMember)
            .join(OSDeveloper, OSPoolMember.developer_id == OSDeveloper.developer_id)
            .where(OSPoolMember.pool_id == pool_id)
        )
        total = await self.session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    # ========== Stats / Embedding ==========

    async def cancel_collect_task(self, task_id: int) -> OSCollectTask | None:
        """Cancel a collect task by setting status to cancelled."""
        task = await self.get_collect_task(task_id)
        if task is None:
            return None
        task.status = "cancelled"
        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def delete_collect_task(self, task_id: int) -> bool:
        """Delete a collect task permanently."""
        task = await self.get_collect_task(task_id)
        if task is None:
            return False
        await self.session.delete(task)
        await self.session.flush()
        await self.session.commit()
        return True

    async def get_missing_developer_ids(
        self,
        developer_ids: list[int],
        model_name: str | None = None,
        vector_type: str | None = None,
    ) -> list[int]:
        """Get developer IDs that do not have embeddings."""
        if not developer_ids:
            return []

        BATCH_SIZE = 5000
        existing_ids: set[int] = set()

        for i in range(0, len(developer_ids), BATCH_SIZE):
            batch_ids = developer_ids[i : i + BATCH_SIZE]
            query = select(OSEmbedding.developer_id).where(OSEmbedding.developer_id.in_(batch_ids))
            if model_name:
                query = query.where(OSEmbedding.model_name == model_name)
            if vector_type:
                query = query.where(OSEmbedding.vector_type == vector_type)
            result = await self.session.execute(query)
            for row in result.fetchall():
                existing_ids.add(row[0])

        return [did for did in developer_ids if did not in existing_ids]

    async def get_visible_developer_ids(self) -> list[int]:
        """Get all visible developer IDs."""
        result = await self.session.execute(
            select(OSDeveloper.developer_id)
            .where(OSDeveloper.is_visible.is_(True))
            .order_by(OSDeveloper.developer_id)
        )
        return [row[0] for row in result.fetchall()]

    async def get_repositories_for_developers(
        self,
        developer_ids: list[int],
    ) -> dict[int, list[OSRepository]]:
        """Batch get repositories for multiple developers, ordered by stars desc."""
        if not developer_ids:
            return {}
        result = await self.session.execute(
            select(OSRepository)
            .where(OSRepository.developer_id.in_(developer_ids))
            .order_by(OSRepository.developer_id, OSRepository.stars_count.desc())
        )
        mapping: dict[int, list[OSRepository]] = {}
        for repo in result.scalars().all():
            if repo.developer_id not in mapping:
                mapping[repo.developer_id] = []
            mapping[repo.developer_id].append(repo)
        return mapping

    async def get_raw_developers_by_logins(
        self,
        github_logins: list[str],
    ) -> dict[str, dict[str, Any]]:
        """Batch get raw developer data by GitHub logins."""
        if not github_logins:
            return {}
        result = await self.session.execute(
            select(OSRawDeveloper).where(OSRawDeveloper.github_login.in_(github_logins))
        )
        mapping: dict[str, dict[str, Any]] = {}
        for raw in result.scalars().all():
            mapping[raw.github_login] = raw.raw_data or {}
        return mapping

    async def get_collected_repos_for_developers(
        self,
        developer_ids: list[int],
    ) -> dict[int, list[str]]:
        """Get collected repo full_names that the developers have contributed to.
        Only includes repos configured in OSRepoConfig (system-collected sources),
        excluding personal repos that were fetched alongside contributor profiles.
        """
        if not developer_ids:
            return {}
        result = await self.session.execute(
            select(OSContribution.developer_id, OSRepository.full_name)
            .join(OSRepository, OSContribution.repo_id == OSRepository.repo_id)
            .join(OSRepoConfig, OSRepository.full_name == OSRepoConfig.repo_full_name)
            .where(
                OSContribution.developer_id.in_(developer_ids),
                OSRepoConfig.is_active.is_(True),
            )
            .distinct()
            .order_by(OSContribution.developer_id, OSRepository.full_name)
        )
        mapping: dict[int, list[str]] = {}
        for dev_id, full_name in result.all():
            if dev_id not in mapping:
                mapping[dev_id] = []
            mapping[dev_id].append(full_name)
        return mapping
