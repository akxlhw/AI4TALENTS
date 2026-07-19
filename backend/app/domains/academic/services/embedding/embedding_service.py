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
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domains.academic.models.talent import Talent
from app.domains.academic.repositories.embedding_repository import EmbeddingRepository
from app.domains.shared.services.llm.errors import EmbeddingError, TalentNotFoundError
from app.domains.shared.services.llm.protocols import LLMGatewayProtocol

logger = logging.getLogger(__name__)


class EmbeddingService:
    """嵌入服务

    负责生成和管理人才嵌入向量。
    支持多种向量类型：research（研究方向）、papers（论文标题）
    """

    # 向量类型常量
    VECTOR_TYPE_RESEARCH = "research"
    VECTOR_TYPE_PAPERS = "papers"

    def __init__(
        self,
        session: AsyncSession,
        llm_gateway: LLMGatewayProtocol | None = None,
        cache: Any = None,
        dimension: int | None = None,
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

    async def get_or_create_embedding(
        self, talent_id: int, vector_type: str = "research"
    ) -> list[float]:
        """
        获取或创建人才嵌入向量

        优先从数据库/缓存获取，不存在则生成。

        Args:
            talent_id: 人才 ID
            vector_type: 向量类型 (research/papers)

        Returns:
            List[float]: 嵌入向量

        Raises:
            TalentNotFoundError: 人才不存在
            EmbeddingError: 生成失败
        """
        talent = await self.session.get(Talent, talent_id)
        if not talent:
            raise TalentNotFoundError(talent_id)

        record = await self.repository.get_by_talent_id(talent_id, vector_type)
        if record:
            if record.model_name == self.model_name:
                return self.repository.get_embedding_vector(record)

        if self.cache:
            cached = await self.cache.get_embedding(talent_id, vector_type)
            if cached:
                return cached

        # 需要生成嵌入，检查是否有 LLM 网关
        if self.llm_gateway is None:
            raise EmbeddingError(
                f"No embedding found for talent {talent_id} ({vector_type}) and no LLM gateway configured. "
                "Cannot generate new embedding."
            )

        # 根据向量类型生成嵌入
        if vector_type == self.VECTOR_TYPE_RESEARCH:
            source_text = self._build_research_source_text(talent)
        else:
            source_text = await self._build_papers_source_text(talent_id)

        if not source_text:
            raise EmbeddingError(f"No source text for talent {talent_id} ({vector_type})")

        result = await self.llm_gateway.generate_embedding(source_text)

        # 存储到数据库
        source_hash = self.calculate_source_hash(source_text)
        await self.repository.upsert(
            talent_id=talent_id,
            embedding=result.embedding,
            model_name=self.model_name,
            source_text_hash=source_hash,
            vector_type=vector_type,
        )

        # 存储到缓存
        if self.cache:
            await self.cache.set_embedding(talent_id, result.embedding, vector_type)

        return result.embedding

    async def batch_generate_embeddings(
        self,
        talent_ids: list[int],
        batch_size: int = 100,
        force_regenerate: bool = False,
        progress_callback: Any = None,
        vector_types: list[str] | None = None,
    ) -> dict:
        """
        批量生成嵌入向量

        Args:
            talent_ids: 人才 ID 列表
            batch_size: 批次大小
            force_regenerate: 是否强制重新生成
            progress_callback: 进度回调函数
            vector_types: 要生成的向量类型列表，默认 ["research"]

        Returns:
            dict: 统计结果
        """
        if vector_types is None:
            vector_types = [self.VECTOR_TYPE_RESEARCH]

        stats = {
            "total": len(talent_ids) * len(vector_types),
            "processed": 0,
            "skipped": 0,
            "failed": 0,
            "failed_ids": [],
        }

        if self.llm_gateway is None:
            logger.error("Cannot generate embeddings: no LLM gateway configured")
            stats["failed"] = stats["total"]
            stats["failed_ids"] = talent_ids
            return stats

        # 获取人才信息（一次性获取，用于两种向量类型）
        talents = await self._get_talents_by_ids(talent_ids)
        if not talents:
            logger.warning("No talents found for given IDs")
            return stats

        talent_map = {t.talent_id: t for t in talents}

        papers_map: dict[int, list[str]] = {}
        if self.VECTOR_TYPE_PAPERS in vector_types:
            from app.domains.academic.repositories.talent_repository import TalentRepository

            talent_repo = TalentRepository(self.session)
            papers_map = await talent_repo.get_paper_titles_for_talents(
                list(talent_map.keys()), limit_per_talent=10
            )

        # 对每种向量类型分别处理
        for vector_type in vector_types:
            type_stats = await self._batch_generate_for_type(
                talent_ids=talent_ids,
                talent_map=talent_map,
                papers_map=papers_map,
                vector_type=vector_type,
                batch_size=batch_size,
                force_regenerate=force_regenerate,
                progress_callback=progress_callback,
            )
            stats["processed"] += type_stats["processed"]
            stats["skipped"] += type_stats["skipped"]
            stats["failed"] += type_stats["failed"]
            stats["failed_ids"].extend(type_stats["failed_ids"])

        return stats

    async def _batch_generate_for_type(
        self,
        talent_ids: list[int],
        talent_map: dict[int, Talent],
        papers_map: dict[int, list[str]],
        vector_type: str,
        batch_size: int,
        force_regenerate: bool,
        progress_callback: Any,
    ) -> dict:
        """对单个向量类型进行批量生成"""
        stats = {"processed": 0, "skipped": 0, "failed": 0, "failed_ids": []}

        if not force_regenerate:
            missing_ids = await self.repository.get_missing_talent_ids(
                talent_ids, self.model_name, vector_type
            )
            stats["skipped"] = len(talent_ids) - len(missing_ids)
            talent_ids = missing_ids

        if not talent_ids:
            logger.info(f"All talents already have {vector_type} embeddings")
            return stats

        # 批量处理
        for i in range(0, len(talent_ids), batch_size):
            batch = talent_ids[i : i + batch_size]
            batch_num = i // batch_size + 1

            try:
                texts = []
                valid_talent_ids = []
                for tid in batch:
                    talent = talent_map.get(tid)
                    if not talent:
                        continue

                    if vector_type == self.VECTOR_TYPE_RESEARCH:
                        text = self._build_research_source_text(talent)
                    else:
                        text = ". ".join(papers_map.get(tid, [])[:10])

                    if text:
                        texts.append(text)
                        valid_talent_ids.append(tid)

                if not texts:
                    logger.warning(f"Batch {batch_num}: No valid texts for {vector_type}")
                    continue

                logger.info(
                    f"Batch {batch_num}: Generating {vector_type} embeddings for {len(texts)} talents"
                )

                # 批量生成嵌入
                results = await self.llm_gateway.generate_embedding_batch(texts)

                logger.info(f"Batch {batch_num}: Received {len(results)} embedding results")

                result_count = len(results)
                if result_count != len(texts):
                    logger.error(
                        f"Batch {batch_num}: Result count mismatch! "
                        f"Expected {len(texts)}, got {result_count}"
                    )
                    failed_count = len(texts) - result_count
                    stats["failed"] += failed_count
                    stats["failed_ids"].extend(valid_talent_ids[result_count:])

                # 批量存储结果（只存成功返回的部分）
                items_to_store = []
                for tid, text, result in zip(
                    valid_talent_ids[:result_count], texts[:result_count], results, strict=False
                ):
                    source_hash = self.calculate_source_hash(text)
                    items_to_store.append(
                        {
                            "talent_id": tid,
                            "embedding": result.embedding,
                            "model_name": self.model_name,
                            "source_text_hash": source_hash,
                            "vector_type": vector_type,
                        }
                    )

                if items_to_store:
                    stored_count = await self.repository.batch_upsert(items_to_store)
                    stats["processed"] += stored_count
                    logger.info(
                        f"Batch {batch_num}: Stored {stored_count} {vector_type} embeddings"
                    )

                # 提交事务
                await self.session.commit()

                # 进度回调
                if progress_callback:
                    await progress_callback(
                        processed=stats["processed"], total=len(talent_ids), batch_num=batch_num
                    )

                # 限流
                if self.rate_limit_delay > 0:
                    await asyncio.sleep(self.rate_limit_delay)

            except Exception as e:
                logger.error(f"Batch embedding failed for batch {i} ({vector_type}): {e}")
                stats["failed"] += len(batch)
                stats["failed_ids"].extend(batch)
                await self.session.rollback()

        return stats

    async def get_average_embedding(
        self, talent_ids: list[int], vector_type: str = "research"
    ) -> list[float]:
        """
        获取多个人才的平均嵌入向量

        使用批量查询优化性能，避免 N+1 问题。

        Args:
            talent_ids: 人才 ID 列表
            vector_type: 向量类型 (research/papers)

        Returns:
            List[float]: 平均嵌入向量
        """
        import numpy as np

        if not talent_ids:
            dim = self.dimension or settings.EMBEDDING_DIMENSION
            return [0.0] * dim

        # 批量获取 embeddings（避免 N+1 查询）
        records = await self.repository.get_by_talent_ids(talent_ids, vector_type)

        embedding_map = {r.talent_id: r.embedding for r in records if r.embedding}

        # 收集存在的 embeddings
        embeddings = []
        missing_ids = []

        for tid in talent_ids:
            if tid in embedding_map:
                embeddings.append(embedding_map[tid])
            else:
                missing_ids.append(tid)

        # 如果有缺失的，可以并行生成（可选，当前使用零向量）
        if missing_ids:
            logger.info(f"Missing embeddings for {len(missing_ids)} talents, using zero vectors")

        if not embeddings:
            dim = self.dimension or settings.EMBEDDING_DIMENSION
            return [0.0] * dim

        avg = np.mean(embeddings, axis=0)
        return avg.tolist()

    async def get_query_embedding(self, query: str) -> list[float]:
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

    def _build_research_source_text(self, talent: Talent) -> str:
        """
        构建研究方向向量源文本

        使用 openalex_topics 作为主要研究方向描述，
        topic_tags 作为补充，职位和姓名作为最后回退。

        Args:
            talent: 人才对象

        Returns:
            str: 用于生成嵌入的文本
        """
        research_parts = []

        # OpenAlex 研究主题（最精准的研究方向描述）
        if talent.openalex_topics:
            research_parts.extend(talent.openalex_topics)

        # 技术标签作为补充
        if talent.topic_tags:
            research_parts.extend(talent.topic_tags)

        # 如果没有研究方向，使用职位
        if not research_parts and talent.current_title:
            research_parts.append(talent.current_title)

        # 最后回退：使用姓名
        if not research_parts:
            name_parts = []
            if talent.name:
                name_parts.append(talent.name)
            if talent.name_en and talent.name_en != talent.name:
                name_parts.append(talent.name_en)
            if name_parts:
                research_parts.append(" ".join(name_parts))

        return ", ".join(research_parts)

    async def _build_papers_source_text(self, talent_id: int) -> str:
        """
        构建论文向量源文本

        获取人才的代表性论文标题。

        Args:
            talent_id: 人才 ID

        Returns:
            str: 用于生成嵌入的文本
        """
        from app.domains.academic.repositories.talent_repository import TalentRepository

        talent_repo = TalentRepository(self.session)
        papers = await talent_repo.get_paper_titles_for_talents([talent_id], limit_per_talent=10)
        titles = papers.get(talent_id, [])

        return ". ".join(titles)

    async def _get_talents_by_ids(self, talent_ids: list[int]) -> list[Talent]:
        """根据 ID 列表获取人才"""
        if not talent_ids:
            return []

        # 分批查询，避免 PostgreSQL 参数上限 (32767)
        BATCH_SIZE = 5000
        all_talents = []

        for i in range(0, len(talent_ids), BATCH_SIZE):
            batch_ids = talent_ids[i : i + BATCH_SIZE]
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
