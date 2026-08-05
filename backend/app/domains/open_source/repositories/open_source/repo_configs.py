"""
Open Source Repository - repo configs queries.

Split from core.py; methods are mixed into OpenSourceCoreRepository.
"""

from __future__ import annotations

from typing import Any
from typing import cast as tcast

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.open_source.models.open_source import (
    OSCollectTask,
    OSRepoConfig,
)


class RepoConfigsMixin:
    """Repo config CRUD operations."""

    session: AsyncSession

    async def list_repo_configs(
        self,
        filters: dict[str, Any] | None = None,
        sort_by: str = "id_desc",
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[OSRepoConfig], int]:
        """List repo configs with filters and pagination."""
        filters = filters or {}
        conditions: list[Any] = []

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
        return tcast(OSRepoConfig | None, result.scalar_one_or_none())

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
        return tcast(OSRepoConfig | None, result.scalar_one_or_none())
