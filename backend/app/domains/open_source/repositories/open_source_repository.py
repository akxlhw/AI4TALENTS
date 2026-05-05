"""
Open Source Repository.

Encapsulates all database queries related to open-source talent.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import and_, cast, func, or_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.open_source.models.open_source import (
    OSCollectTask,
    OSContribution,
    OSDeveloper,
    OSEmbedding,
    OSFavourite,
    OSLanguageSkill,
    OSPoolMember,
    OSRepoConfig,
    OSRepository,
    OSTalentPool,
)


class OpenSourceRepository:
    """Repository for open-source talent database queries."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ========== RepoConfig ==========

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

        tech_element = filters.get("tech_element")
        is_active = filters.get("is_active")
        collect_enabled = filters.get("collect_enabled")
        collected_only = filters.get("collected_only", False)

        if tech_element:
            conditions.append(OSRepoConfig.tech_element == tech_element)
        if is_active is not None:
            conditions.append(OSRepoConfig.is_active == is_active)
        if collect_enabled is not None:
            conditions.append(OSRepoConfig.collect_enabled == collect_enabled)

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
                OSDeveloper.primary_languages.cast(JSONB).op("@>")(cast(languages, JSONB))
            )
        if location:
            conditions.append(OSDeveloper.location.ilike(f"%{location}%"))
        if company:
            conditions.append(OSDeveloper.company.ilike(f"%{company}%"))
        if min_stars is not None:
            conditions.append(OSDeveloper.total_stars_received >= min_stars)

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
        return [(c, full_name) for c, full_name in result.all()]

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
        stmt = stmt.order_by(OSFavourite.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size)
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
        return [r for r in result.scalars().all()]

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
        await self.session.refresh(favourite)
        return favourite

    async def delete_favourite(
        self,
        favourite: OSFavourite,
    ) -> None:
        """Soft-delete a favourite by setting is_active=False."""
        favourite.is_active = False
        await self.session.flush()

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
        await self.session.refresh(member)
        return member

    async def remove_pool_member(
        self,
        member: OSPoolMember,
    ) -> None:
        """Remove a member from a talent pool."""
        await self.session.delete(member)
        await self.session.flush()

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

    async def get_stats(
        self,
    ) -> dict[str, Any]:
        """Return aggregated open-source statistics."""
        total_devs = await self.session.scalar(
            select(func.count()).select_from(OSDeveloper).where(OSDeveloper.is_visible.is_(True))
        )
        total_repos = await self.session.scalar(select(func.count()).select_from(OSRepository))
        total_orgs = await self.session.scalar(
            select(func.count(func.distinct(OSDeveloper.company))).where(
                OSDeveloper.company.isnot(None)
            )
        )

        lang_result = await self.session.execute(
            select(OSLanguageSkill.language, func.count(OSLanguageSkill.developer_id))
            .group_by(OSLanguageSkill.language)
            .order_by(func.count(OSLanguageSkill.developer_id).desc())
        )
        language_distribution = {lang: cnt for lang, cnt in lang_result.all()}

        tech_result = await self.session.execute(
            select(OSRepoConfig.tech_element, func.count(OSRepoConfig.repo_config_id))
            .where(OSRepoConfig.is_active.is_(True))
            .group_by(OSRepoConfig.tech_element)
        )
        tech_element_distribution = {tech: cnt for tech, cnt in tech_result.all()}

        return {
            "total_developers": total_devs or 0,
            "total_repositories": total_repos or 0,
            "total_organizations": total_orgs or 0,
            "active_developers_30d": 0,
            "language_distribution": language_distribution,
            "tech_element_distribution": tech_element_distribution,
        }

    async def get_embedding_status(
        self,
    ) -> dict[str, int]:
        """Return embedding coverage status."""
        total = await self.session.scalar(
            select(func.count()).select_from(OSDeveloper).where(OSDeveloper.is_visible.is_(True))
        )
        embedded = await self.session.scalar(select(func.count()).select_from(OSEmbedding))
        return {
            "total_developers": total or 0,
            "embedded_count": embedded or 0,
            "pending_count": (total or 0) - (embedded or 0),
        }

    async def cancel_collect_task(self, task_id: int) -> OSCollectTask | None:
        """Cancel a collect task by setting status to cancelled."""
        task = await self.get_collect_task(task_id)
        if task is None:
            return None
        task.status = "cancelled"
        await self.session.flush()
        await self.session.refresh(task)
        return task

    async def search_developers(
        self,
        req: Any,
    ) -> tuple[list[OSDeveloper], int]:
        """Search developers (delegates to list_developers for now)."""
        # Simple keyword search fallback
        q = getattr(req, "query", "")
        page = getattr(req, "page", 1)
        page_size = getattr(req, "page_size", 20)
        return await self.list_developers(
            filters={"q": q} if q else None,
            page=page,
            page_size=page_size,
        )

    async def jd_match(
        self,
        jd_text: str,
        filters: Any | None = None,
        top_k: int = 20,
    ) -> dict[str, Any]:
        """JD matching placeholder."""
        return {"matches": [], "total": 0}

    async def generate_embeddings(self, batch_size: int = 50) -> dict[str, Any]:
        """Generate embeddings placeholder."""
        return {"generated": 0, "batch_size": batch_size}
