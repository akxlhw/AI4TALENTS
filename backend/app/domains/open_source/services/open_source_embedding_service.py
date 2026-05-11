"""
Open Source Embedding Service.

Handles embedding generation and management for open-source developers.
Mirrors the academic EmbeddingService but operates on os_developer / os_embedding.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.open_source.models.open_source import OSDeveloper
from app.domains.open_source.repositories.open_source import (
    OpenSourceRepository,
)
from app.domains.shared.services.llm.errors import EmbeddingError
from app.domains.shared.services.llm.protocols import LLMGatewayProtocol

logger = logging.getLogger(__name__)


class OpenSourceEmbeddingService:
    """嵌入服务（开源域）

    负责生成和管理开源开发者的嵌入向量。
    支持向量类型：profile（开发者画像）
    """

    VECTOR_TYPE_PROFILE = "profile"

    def __init__(
        self,
        session: AsyncSession,
        llm_gateway: LLMGatewayProtocol | None = None,
        dimension: int | None = None,
        model_name: str | None = None,
        rate_limit_delay: float = 0.0,
    ):
        self.session = session
        self.llm_gateway = llm_gateway
        self.dimension = dimension
        self.model_name = model_name or "default-embedding-model"
        self.rate_limit_delay = rate_limit_delay
        self.repository = OpenSourceRepository(session)

    async def get_or_create_embedding(
        self, developer_id: int, vector_type: str = "profile"
    ) -> list[float]:
        """获取或创建开发者嵌入向量。"""
        dev = await self.session.get(OSDeveloper, developer_id)
        if not dev:
            raise EmbeddingError(f"Developer {developer_id} not found")

        record = await self.repository.get_embedding_by_developer_id(developer_id, vector_type)
        if record and record.model_name == self.model_name:
            return self._parse_embedding(record.embedding)

        if self.llm_gateway is None:
            raise EmbeddingError(
                f"No embedding found for developer {developer_id} and no LLM gateway configured"
            )

        source_text = self._build_profile_source_text(dev)
        if not source_text:
            raise EmbeddingError(f"No source text for developer {developer_id}")

        result = await self.llm_gateway.generate_embedding(source_text)
        source_hash = self._calculate_source_hash(source_text)

        await self.repository.upsert_embedding(
            developer_id=developer_id,
            embedding=result.embedding,
            model_name=self.model_name,
            source_text_hash=source_hash,
            vector_type=vector_type,
        )
        await self.session.commit()

        return result.embedding

    async def batch_generate_embeddings(
        self,
        developer_ids: list[int],
        batch_size: int = 50,
        force_regenerate: bool = False,
        progress_callback: Any = None,
    ) -> dict:
        """批量生成嵌入向量。"""
        stats = {
            "total": len(developer_ids),
            "processed": 0,
            "skipped": 0,
            "failed": 0,
            "failed_ids": [],
        }

        if self.llm_gateway is None:
            logger.error("Cannot generate embeddings: no LLM gateway configured")
            stats["failed"] = stats["total"]
            stats["failed_ids"] = developer_ids
            return stats

        if not force_regenerate:
            missing_ids = await self.repository.get_missing_developer_ids(
                developer_ids, self.model_name, self.VECTOR_TYPE_PROFILE
            )
            stats["skipped"] = len(developer_ids) - len(missing_ids)
            developer_ids = missing_ids

        if not developer_ids:
            logger.info("All developers already have embeddings")
            return stats

        # Fetch all developers in one query
        devs = await self._get_developers_by_ids(developer_ids)
        dev_map = {d.developer_id: d for d in devs}

        for i in range(0, len(developer_ids), batch_size):
            batch = developer_ids[i : i + batch_size]
            batch_num = i // batch_size + 1

            try:
                texts = []
                valid_ids = []
                for did in batch:
                    dev = dev_map.get(did)
                    if not dev:
                        continue
                    text = self._build_profile_source_text(dev)
                    if text:
                        texts.append(text)
                        valid_ids.append(did)

                if not texts:
                    logger.warning(f"Batch {batch_num}: No valid texts")
                    continue

                logger.info(f"Batch {batch_num}: Generating embeddings for {len(texts)} developers")
                results = await self.llm_gateway.generate_embedding_batch(texts)

                items_to_store = []
                for did, text, result in zip(
                    valid_ids[: len(results)], texts[: len(results)], results, strict=False
                ):
                    source_hash = self._calculate_source_hash(text)
                    items_to_store.append(
                        {
                            "developer_id": did,
                            "embedding": result.embedding,
                            "model_name": self.model_name,
                            "source_text_hash": source_hash,
                            "vector_type": self.VECTOR_TYPE_PROFILE,
                        }
                    )

                if items_to_store:
                    stored_count = await self.repository.batch_upsert_embeddings(items_to_store)
                    stats["processed"] += stored_count
                    logger.info(f"Batch {batch_num}: Stored {stored_count} embeddings")

                await self.session.commit()

                if progress_callback:
                    await progress_callback(
                        processed=stats["processed"], total=len(developer_ids), batch_num=batch_num
                    )

                if self.rate_limit_delay > 0:
                    await asyncio.sleep(self.rate_limit_delay)

            except Exception as e:
                logger.error(f"Batch {batch_num} failed: {e}")
                stats["failed"] += len(batch)
                stats["failed_ids"].extend(batch)
                await self.session.rollback()

        return stats

    async def get_query_embedding(self, query: str) -> list[float]:
        """获取查询文本的嵌入向量。"""
        if self.llm_gateway is None:
            raise EmbeddingError("No LLM gateway configured")
        result = await self.llm_gateway.generate_embedding(query)
        return result.embedding

    def _build_profile_source_text(self, dev: OSDeveloper) -> str:
        """构建开发者画像源文本。"""
        parts = []
        if dev.bio:
            parts.append(dev.bio)
        if dev.name and dev.name != dev.github_login:
            parts.append(dev.name)
        if dev.primary_languages:
            parts.append(f"Languages: {', '.join(dev.primary_languages)}")
        if dev.tech_tags:
            parts.append(f"Technologies: {', '.join(dev.tech_tags)}")
        if dev.company:
            parts.append(f"Company: {dev.company}")
        if dev.location:
            parts.append(f"Location: {dev.location}")
        return ". ".join(parts)

    async def _get_developers_by_ids(self, developer_ids: list[int]) -> list[OSDeveloper]:
        """根据 ID 列表批量获取开发者。"""
        if not developer_ids:
            return []
        BATCH_SIZE = 5000
        all_devs = []
        for i in range(0, len(developer_ids), BATCH_SIZE):
            batch_ids = developer_ids[i : i + BATCH_SIZE]
            query = select(OSDeveloper).where(OSDeveloper.developer_id.in_(batch_ids))
            result = await self.session.execute(query)
            all_devs.extend(result.scalars().all())
        return all_devs

    @staticmethod
    def _calculate_source_hash(source_text: str) -> str:
        return hashlib.md5(source_text.encode()).hexdigest()

    @staticmethod
    def _parse_embedding(embedding_str: str) -> list[float]:
        """解析嵌入向量字符串。"""
        if not embedding_str:
            return []
        import json

        try:
            return json.loads(embedding_str)
        except json.JSONDecodeError:
            return [float(v.strip()) for v in embedding_str.strip("[]").split(",") if v.strip()]
