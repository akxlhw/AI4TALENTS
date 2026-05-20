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
from sqlalchemy.exc import SQLAlchemyError
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
    except SQLAlchemyError:
        return True


class OpenSourceAdvancedRepository:
    """Advanced search, embedding and analytics for open-source talent."""

    def __init__(self, session):
        self.session = session

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
        language_distribution = dict(lang_result.all())

        tech_result = await self.session.execute(
            select(OSRepoConfig.tech_element, func.count(OSRepoConfig.repo_config_id))
            .where(OSRepoConfig.is_active.is_(True))
            .group_by(OSRepoConfig.tech_element)
        )
        tech_element_distribution = dict(tech_result.all())

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
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).replace(tzinfo=None)
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

        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).replace(tzinfo=None)

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
                filter_clauses.append("d.primary_languages ?| :languages")
                filter_params["languages"] = filters["languages"]
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
