"""
Embedding Service implementation.
嵌入服务实现 - v1.4

Features:
- Single embedding generation
- Batch embedding generation
- Database storage
- Caching
- Model tracking
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import List, Optional, Any
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.talent import Talent
from app.models.embedding import TalentEmbedding
from app.repositories.embedding_repository import EmbeddingRepository
from app.services.llm.protocols import LLMGatewayProtocol
from app.services.llm.errors import EmbeddingError, TalentNotFoundError

logger = logging.getLogger(__name__)


class EmbeddingService:
    """嵌入服务

    负责生成和管理人才嵌入向量。
    """

    def __init__(
        self,
        session: AsyncSession,
        llm_gateway: LLMGatewayProtocol | None = None,
        cache: Any = None,
        dimension: int = 1536,
        model_name: str | None = None,
        rate_limit_delay: float = 0.0,
    ):
        """
        初始化嵌入服务

        Args:
            session: 数据库会话
            llm_gateway: LLM 网关（可选，仅生成新嵌入时需要）
            cache: 缓存管理器
            dimension: 向量维度
            model_name: 模型名称
            rate_limit_delay: 限流延迟（秒）
        """
        self.session = session
        self.llm_gateway = llm_gateway
        self.cache = cache
        self.dimension = dimension
        self.model_name = model_name or "default-embedding-model"
        self.rate_limit_delay = rate_limit_delay
        self.repository = EmbeddingRepository(session)

    async def get_or_create_embedding(self, talent_id: int) -> List[float]:
        """
        获取或创建人才嵌入向量

        优先从数据库/缓存获取，不存在则生成。

        Args:
            talent_id: 人才 ID

        Returns:
            List[float]: 嵌入向量

        Raises:
            TalentNotFoundError: 人才不存在
            EmbeddingError: 生成失败
        """
        # 检查人才是否存在
        talent = await self.session.get(Talent, talent_id)
        if not talent:
            raise TalentNotFoundError(talent_id)

        # 检查数据库
        record = await self.repository.get_by_talent_id(talent_id)
        if record:
            # 检查模型是否匹配
            if record.model_name == self.model_name:
                return self.repository.get_embedding_vector(record)

        # 检查缓存
        if self.cache:
            cached = await self.cache.get_embedding(talent_id)
            if cached:
                return cached

        # 需要生成嵌入，检查是否有 LLM 网关
        if self.llm_gateway is None:
            raise EmbeddingError(
                f"No embedding found for talent {talent_id} and no LLM gateway configured. "
                "Cannot generate new embedding."
            )

        # 生成嵌入
        source_text = self._build_source_text(talent)
        result = await self.llm_gateway.generate_embedding(source_text)

        # 存储到数据库
        source_hash = self.calculate_source_hash(source_text)
        await self.repository.upsert(
            talent_id=talent_id,
            embedding=result.embedding,
            model_name=self.model_name,
            source_text_hash=source_hash,
        )

        # 存储到缓存
        if self.cache:
            await self.cache.set_embedding(talent_id, result.embedding)

        return result.embedding

    async def batch_generate_embeddings(
        self,
        talent_ids: List[int],
        batch_size: int = 100,
        force_regenerate: bool = False,
        progress_callback: Any = None,
    ) -> dict:
        """
        批量生成嵌入向量

        Args:
            talent_ids: 人才 ID 列表
            batch_size: 批次大小
            force_regenerate: 是否强制重新生成
            progress_callback: 进度回调函数

        Returns:
            dict: 统计结果
        """
        stats = {
            "total": len(talent_ids),
            "processed": 0,
            "skipped": 0,
            "failed": 0,
            "failed_ids": [],
        }

        # 获取已有嵌入的人才（如果不强制重新生成）
        if not force_regenerate:
            missing_ids = await self.repository.get_missing_talent_ids(
                talent_ids, self.model_name
            )
            stats["skipped"] = len(talent_ids) - len(missing_ids)
            talent_ids = missing_ids

        if not talent_ids:
            logger.info("All talents already have embeddings")
            return stats

        # 检查是否有 LLM 网关（生成嵌入需要）
        if self.llm_gateway is None:
            logger.error("Cannot generate embeddings: no LLM gateway configured")
            stats["failed"] = len(talent_ids)
            stats["failed_ids"] = talent_ids
            return stats

        # 批量处理
        for i in range(0, len(talent_ids), batch_size):
            batch = talent_ids[i:i + batch_size]
            batch_num = i // batch_size + 1

            try:
                # 获取人才信息
                talents = await self._get_talents_by_ids(batch)
                if not talents:
                    logger.warning(f"Batch {batch_num}: No talents found for IDs {batch}")
                    continue

                # 构建文本
                texts = [self._build_source_text(t) for t in talents]
                talent_id_map = {self._build_source_text(t): t.talent_id for t in talents}

                logger.info(f"Batch {batch_num}: Generating embeddings for {len(texts)} talents")

                # 批量生成嵌入
                results = await self.llm_gateway.generate_embedding_batch(texts)

                logger.info(f"Batch {batch_num}: Received {len(results)} embedding results")

                # 验证结果数量
                if len(results) != len(texts):
                    logger.error(
                        f"Batch {batch_num}: Result count mismatch! "
                        f"Expected {len(texts)}, got {len(results)}"
                    )
                    # 只处理匹配的部分
                    stats["failed"] += len(texts) - len(results)

                # 批量存储结果（性能优化：单次数据库操作）
                items_to_store = []
                for text, result in zip(texts, results):
                    talent_id = talent_id_map.get(text)
                    if talent_id:
                        source_hash = self.calculate_source_hash(text)
                        items_to_store.append({
                            'talent_id': talent_id,
                            'embedding': result.embedding,
                            'model_name': self.model_name,
                            'source_text_hash': source_hash,
                        })

                if items_to_store:
                    stored_count = await self.repository.batch_upsert(items_to_store)
                    stats["processed"] += stored_count
                    logger.info(f"Batch {batch_num}: Batch stored {stored_count} embeddings")

                # 提交事务
                await self.session.commit()

                # 进度回调
                if progress_callback:
                    await progress_callback(
                        processed=stats["processed"],
                        total=len(talent_ids),
                        batch_num=i // batch_size + 1
                    )

                # 限流
                if self.rate_limit_delay > 0:
                    await asyncio.sleep(self.rate_limit_delay)

            except Exception as e:
                logger.error(f"Batch embedding failed for batch {i}: {e}")
                stats["failed"] += len(batch)
                stats["failed_ids"].extend(batch)
                await self.session.rollback()

        return stats

    async def get_average_embedding(self, talent_ids: List[int]) -> List[float]:
        """
        获取多个人才的平均嵌入向量

        Args:
            talent_ids: 人才 ID 列表

        Returns:
            List[float]: 平均嵌入向量
        """
        import numpy as np

        embeddings = []
        for tid in talent_ids:
            try:
                emb = await self.get_or_create_embedding(tid)
                embeddings.append(emb)
            except Exception as e:
                logger.warning(f"Failed to get embedding for talent {tid}: {e}")

        if not embeddings:
            return [0.0] * self.dimension

        # 计算平均
        avg = np.mean(embeddings, axis=0)
        return avg.tolist()

    async def get_query_embedding(self, query: str) -> List[float]:
        """
        获取查询文本的嵌入向量

        Args:
            query: 查询文本

        Returns:
            List[float]: 嵌入向量
        """
        result = await self.llm_gateway.generate_embedding(query)
        return result.embedding

    def calculate_source_hash(self, source_text: str) -> str:
        """
        计算源文本哈希

        Args:
            source_text: 源文本

        Returns:
            str: 哈希值
        """
        return hashlib.md5(source_text.encode()).hexdigest()

    def _build_source_text(self, talent: Talent) -> str:
        """
        构建嵌入源文本

        优先使用研究方向信息，让语义搜索更精准匹配研究领域。

        Args:
            talent: 人才对象

        Returns:
            str: 用于生成嵌入的文本
        """
        # 研究方向相关字段优先
        research_parts = []

        # 1. OpenAlex 研究主题（最精准的研究方向描述）
        if talent.openalex_topics:
            research_parts.extend(talent.openalex_topics)

        # 2. 技术标签
        if talent.topic_tags:
            research_parts.extend(talent.topic_tags)

        # 如果没有任何研究方向信息，使用职位
        if not research_parts and talent.current_title:
            research_parts.append(talent.current_title)

        # 姓名（标识用，放在末尾降低权重）
        name_parts = []
        if talent.name:
            name_parts.append(talent.name)
        if talent.name_en and talent.name_en != talent.name:
            name_parts.append(talent.name_en)

        # 组合：研究方向为主，姓名为辅
        if research_parts and name_parts:
            return f"{', '.join(research_parts)}. Researcher: {' '.join(name_parts)}"
        elif research_parts:
            return ", ".join(research_parts)
        else:
            return " ".join(name_parts) if name_parts else ""

    async def _get_talents_by_ids(self, talent_ids: List[int]) -> List[Talent]:
        """根据 ID 列表获取人才"""
        if not talent_ids:
            return []

        # 分批查询，避免 PostgreSQL 参数上限 (32767)
        BATCH_SIZE = 5000
        all_talents = []

        for i in range(0, len(talent_ids), BATCH_SIZE):
            batch_ids = talent_ids[i:i + BATCH_SIZE]
            query = select(Talent).where(Talent.talent_id.in_(batch_ids))
            result = await self.session.execute(query)
            all_talents.extend(result.scalars().all())

        return all_talents

    async def get_stats(self) -> dict:
        """
        获取嵌入统计信息

        Returns:
            dict: 统计信息
        """
        total = await self.repository.count()
        by_model = await self.repository.count_by_model(self.model_name)

        return {
            "total_embeddings": total,
            "current_model": self.model_name,
            "current_model_count": by_model,
        }
