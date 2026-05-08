"""
Open Source Repository.

Encapsulates all database queries related to open-source talent.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from sqlalchemy import and_, cast, exists, func, or_, select, text
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

logger = logging.getLogger(__name__)

# Global cache for database type
_is_postgres_cache: bool | None = None


def _is_postgres(session: AsyncSession) -> bool:
    """Check if the database is PostgreSQL."""
    global _is_postgres_cache
    if _is_postgres_cache is not None:
        return _is_postgres_cache
    try:
        bind = session.get_bind()
        _is_postgres_cache = bind.dialect.name == "postgresql"
        return _is_postgres_cache
    except Exception:
        return True


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
                OSDeveloper.primary_languages.cast(JSONB).op("@>")(cast(languages, JSONB))
            )
        if location:
            conditions.append(OSDeveloper.location.ilike(f"%{location}%"))
        if company:
            conditions.append(OSDeveloper.company.ilike(f"%{company}%"))
        if min_stars is not None:
            conditions.append(OSDeveloper.total_stars_received >= min_stars)

        stmt = select(OSDeveloper).where(and_(*conditions))

        # 子查询：判断开发者是否有 Committer 角色（排序时优先）
        has_committer = exists().where(
            OSContribution.developer_id == OSDeveloper.developer_id,
            OSContribution.is_committer.is_(True),
        )

        order_map = {
            "stars_desc": [has_committer.desc(), OSDeveloper.total_stars_received.desc()],
            "stars_asc": [has_committer.desc(), OSDeveloper.total_stars_received.asc()],
            "name_asc": [has_committer.desc(), OSDeveloper.name.asc()],
        }
        order_clauses = order_map.get(sort_by, [OSDeveloper.total_stars_received.desc()])
        stmt = stmt.order_by(*order_clauses)

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

    # ========== Embedding ==========

    async def get_embedding_by_developer_id(
        self, developer_id: int, vector_type: str = "profile"
    ) -> OSEmbedding | None:
        """Get embedding record by developer ID and vector type."""
        result = await self.session.execute(
            select(OSEmbedding).where(
                OSEmbedding.developer_id == developer_id,
                OSEmbedding.vector_type == vector_type,
            )
        )
        return result.scalar_one_or_none()

    async def upsert_embedding(
        self,
        developer_id: int,
        embedding: list[float],
        model_name: str,
        source_text_hash: str,
        vector_type: str = "profile",
    ) -> OSEmbedding:
        """Create or update an embedding record."""
        from datetime import datetime

        now = datetime.utcnow()
        vector_str = "[" + ",".join(str(v) for v in embedding) + "]"

        if _is_postgres(self.session):
            await self.session.execute(
                text(
                    """
                    INSERT INTO os_embedding
                    (developer_id, vector_type, embedding, model_name,
                     source_text_hash, created_at, updated_at)
                    VALUES (:developer_id, :vector_type,
                            CAST(:embedding AS vector), :model_name,
                            :source_text_hash, :created_at, :updated_at)
                    ON CONFLICT (developer_id, vector_type) DO UPDATE SET
                        embedding = EXCLUDED.embedding,
                        model_name = EXCLUDED.model_name,
                        source_text_hash = EXCLUDED.source_text_hash,
                        updated_at = EXCLUDED.updated_at
                """
                ),
                {
                    "developer_id": developer_id,
                    "vector_type": vector_type,
                    "embedding": vector_str,
                    "model_name": model_name,
                    "source_text_hash": source_text_hash,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            await self.session.flush()
            return await self.get_embedding_by_developer_id(developer_id, vector_type)
        else:
            existing = await self.get_embedding_by_developer_id(developer_id, vector_type)
            embedding_str = json.dumps(embedding)
            if existing:
                existing.embedding = embedding_str
                existing.model_name = model_name
                existing.source_text_hash = source_text_hash
                existing.updated_at = now
                await self.session.flush()
                return existing
            else:
                record = OSEmbedding(
                    developer_id=developer_id,
                    vector_type=vector_type,
                    embedding=embedding_str,
                    model_name=model_name,
                    source_text_hash=source_text_hash,
                    created_at=now,
                    updated_at=now,
                )
                self.session.add(record)
                await self.session.flush()
                return record

    async def batch_upsert_embeddings(self, items: list[dict[str, Any]]) -> int:
        """Batch upsert embedding records."""
        if not items:
            return 0

        from datetime import datetime

        now = datetime.utcnow()

        if _is_postgres(self.session):
            values_clauses = []
            params: dict[str, Any] = {}
            for i, item in enumerate(items):
                vector_str = "[" + ",".join(str(v) for v in item["embedding"]) + "]"
                vector_type = item.get("vector_type", "profile")
                values_clauses.append(
                    f"(:developer_id_{i}, :vector_type_{i}, "
                    f"CAST(:embedding_{i} AS vector), :model_name_{i}, "
                    f":hash_{i}, :created_at, :updated_at)"
                )
                params[f"developer_id_{i}"] = item["developer_id"]
                params[f"vector_type_{i}"] = vector_type
                params[f"embedding_{i}"] = vector_str
                params[f"model_name_{i}"] = item["model_name"]
                params[f"hash_{i}"] = item["source_text_hash"]

            params["created_at"] = now
            params["updated_at"] = now

            sql = f"""
                INSERT INTO os_embedding
                (developer_id, vector_type, embedding, model_name,
                 source_text_hash, created_at, updated_at)
                VALUES {', '.join(values_clauses)}
                ON CONFLICT (developer_id, vector_type) DO UPDATE SET
                    embedding = EXCLUDED.embedding,
                    model_name = EXCLUDED.model_name,
                    source_text_hash = EXCLUDED.source_text_hash,
                    updated_at = EXCLUDED.updated_at
            """
            await self.session.execute(text(sql), params)
            await self.session.flush()
            return len(items)
        else:
            for item in items:
                await self.upsert_embedding(
                    developer_id=item["developer_id"],
                    embedding=item["embedding"],
                    model_name=item["model_name"],
                    source_text_hash=item["source_text_hash"],
                    vector_type=item.get("vector_type", "profile"),
                )
            return len(items)

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

    async def search_by_vector_similarity(
        self,
        query_embedding: list[float],
        similarity_threshold: float = 0.7,
        filters: dict[str, Any] | None = None,
        limit: int = 20,
        offset: int = 0,
        vector_type: str = "profile",
    ) -> tuple[list[OSDeveloper], int]:
        """
        Search developers by vector similarity using pgvector.

        Args:
            query_embedding: Query vector
            similarity_threshold: Minimum similarity score (0.0-1.0)
            filters: Additional filters (tech_elements, languages, location, company, min_stars)
            limit: Maximum results
            offset: Result offset
            vector_type: Vector type to search

        Returns:
            Tuple of (developer list, total count)
        """
        vector_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

        if not re.match(r"^[\d\.\-\,\s\[\]eE+]+$", vector_str):
            raise ValueError("Invalid vector format: contains disallowed characters")

        distance_threshold = 1.0 - similarity_threshold

        filter_clauses = ["e.vector_type = :vector_type"]
        filter_params: dict[str, Any] = {"vector_type": vector_type}

        if filters:
            if "tech_elements" in filters:
                filter_clauses.append("d.tech_tags @> :tech_elements::jsonb")
                filter_params["tech_elements"] = json.dumps(filters["tech_elements"])
            if "languages" in filters:
                filter_clauses.append("d.primary_languages @> :languages::jsonb")
                filter_params["languages"] = json.dumps(filters["languages"])
            if "location" in filters:
                filter_clauses.append("d.location ILIKE :location")
                filter_params["location"] = f"%{filters['location']}%"
            if "company" in filters:
                filter_clauses.append("d.company ILIKE :company")
                filter_params["company"] = f"%{filters['company']}%"
            if "min_stars" in filters:
                filter_clauses.append("d.total_stars_received >= :min_stars")
                filter_params["min_stars"] = filters["min_stars"]

        filter_sql = " AND " + " AND ".join(filter_clauses)

        # Count query
        count_query_str = f"""
            SELECT COUNT(*) as total
            FROM os_developer d
            INNER JOIN os_embedding e ON d.developer_id = e.developer_id
            WHERE d.is_visible = TRUE
            AND e.embedding <=> '{vector_str}'::vector <= :distance_threshold
            {filter_sql}
        """
        filter_params["distance_threshold"] = distance_threshold
        count_result = await self.session.execute(text(count_query_str), filter_params)
        total = count_result.scalar() or 0

        # Data query
        data_query_str = f"""
            SELECT d.*, e.embedding <=> '{vector_str}'::vector AS distance
            FROM os_developer d
            INNER JOIN os_embedding e ON d.developer_id = e.developer_id
            WHERE d.is_visible = TRUE
            AND e.embedding <=> '{vector_str}'::vector <= :distance_threshold
            {filter_sql}
            ORDER BY distance ASC
            LIMIT :limit OFFSET :offset
        """
        filter_params["limit"] = limit
        filter_params["offset"] = offset

        result = await self.session.execute(text(data_query_str), filter_params)
        rows = result.mappings().all()

        developers = []
        for row in rows:
            dev = OSDeveloper(
                developer_id=row["developer_id"],
                github_login=row["github_login"],
                github_id=row["github_id"],
                name=row["name"],
                bio=row["bio"],
                location=row["location"],
                company=row["company"],
                blog_url=row["blog_url"],
                email=row["email"],
                avatar_url=row["avatar_url"],
                followers_count=row["followers_count"],
                following_count=row["following_count"],
                public_repos_count=row["public_repos_count"],
                total_stars_received=row["total_stars_received"],
                total_forks_received=row["total_forks_received"],
                primary_languages=row["primary_languages"],
                tech_tags=row["tech_tags"],
                is_visible=row["is_visible"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            developers.append(dev)

        return developers, total

    async def generate_embeddings(self, batch_size: int = 50) -> dict[str, Any]:
        """Generate embeddings placeholder (replaced by OpenSourceEmbeddingService)."""
        return {"generated": 0, "batch_size": batch_size}
