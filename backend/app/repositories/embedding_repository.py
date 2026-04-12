"""
Embedding Repository.
嵌入向量仓储层 - v1.4

Handles database operations for talent embeddings.
"""

from __future__ import annotations

import logging
from typing import List, Optional
from datetime import datetime

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.embedding import TalentEmbedding

logger = logging.getLogger(__name__)


class EmbeddingRepository:
    """嵌入向量仓储

    负责嵌入向量的数据库 CRUD 操作。
    """

    def __init__(self, session: AsyncSession):
        """
        初始化仓储

        Args:
            session: 数据库会话
        """
        self.session = session

    async def get_by_talent_id(self, talent_id: int) -> Optional[TalentEmbedding]:
        """
        根据人才 ID 获取嵌入向量

        Args:
            talent_id: 人才 ID

        Returns:
            Optional[TalentEmbedding]: 嵌入记录或 None
        """
        result = await self.session.execute(
            select(TalentEmbedding).where(TalentEmbedding.talent_id == talent_id)
        )
        return result.scalar_one_or_none()

    async def get_by_talent_ids(self, talent_ids: List[int]) -> List[TalentEmbedding]:
        """
        批量获取嵌入向量

        Args:
            talent_ids: 人才 ID 列表

        Returns:
            List[TalentEmbedding]: 嵌入记录列表
        """
        if not talent_ids:
            return []

        result = await self.session.execute(
            select(TalentEmbedding).where(TalentEmbedding.talent_id.in_(talent_ids))
        )
        return list(result.scalars().all())

    async def create(
        self,
        talent_id: int,
        embedding: List[float],
        model_name: str,
        source_text_hash: str,
    ) -> TalentEmbedding:
        """
        创建嵌入记录

        Args:
            talent_id: 人才 ID
            embedding: 嵌入向量
            model_name: 模型名称
            source_text_hash: 源文本哈希

        Returns:
            TalentEmbedding: 创建的记录
        """
        # 将向量转换为字符串存储（兼容 SQLite）
        # PostgreSQL 可以使用 pgvector 的 vector 类型
        embedding_str = self._embedding_to_str(embedding)

        record = TalentEmbedding(
            talent_id=talent_id,
            embedding=embedding_str,
            model_name=model_name,
            source_text_hash=source_text_hash,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        self.session.add(record)
        await self.session.flush()

        return record

    async def upsert(
        self,
        talent_id: int,
        embedding: List[float],
        model_name: str,
        source_text_hash: str,
    ) -> TalentEmbedding:
        """
        创建或更新嵌入记录

        Args:
            talent_id: 人才 ID
            embedding: 嵌入向量
            model_name: 模型名称
            source_text_hash: 源文本哈希

        Returns:
            TalentEmbedding: 记录
        """
        existing = await self.get_by_talent_id(talent_id)

        if existing:
            # 更新现有记录
            existing.embedding = self._embedding_to_str(embedding)
            existing.model_name = model_name
            existing.source_text_hash = source_text_hash
            existing.updated_at = datetime.utcnow()
            await self.session.flush()
            return existing
        else:
            # 创建新记录
            return await self.create(talent_id, embedding, model_name, source_text_hash)

    async def delete_by_talent_id(self, talent_id: int) -> bool:
        """
        删除嵌入记录

        Args:
            talent_id: 人才 ID

        Returns:
            bool: 是否删除成功
        """
        result = await self.session.execute(
            delete(TalentEmbedding).where(TalentEmbedding.talent_id == talent_id)
        )
        return result.rowcount > 0

    async def delete_by_model(self, model_name: str) -> int:
        """
        删除指定模型的所有嵌入记录

        Args:
            model_name: 模型名称

        Returns:
            int: 删除的记录数
        """
        result = await self.session.execute(
            delete(TalentEmbedding).where(TalentEmbedding.model_name == model_name)
        )
        return result.rowcount

    async def count(self) -> int:
        """
        统计嵌入记录总数

        Returns:
            int: 记录数
        """
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.count()).select_from(TalentEmbedding)
        )
        return result.scalar() or 0

    async def count_by_model(self, model_name: str) -> int:
        """
        统计指定模型的嵌入记录数

        Args:
            model_name: 模型名称

        Returns:
            int: 记录数
        """
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.count())
            .select_from(TalentEmbedding)
            .where(TalentEmbedding.model_name == model_name)
        )
        return result.scalar() or 0

    async def get_missing_talent_ids(
        self,
        talent_ids: List[int],
        model_name: str | None = None
    ) -> List[int]:
        """
        获取没有嵌入向量的人才 ID

        Args:
            talent_ids: 人才 ID 列表
            model_name: 可选的模型名称过滤

        Returns:
            List[int]: 缺失嵌入的人才 ID 列表
        """
        if not talent_ids:
            return []

        # 查询已有嵌入的人才 ID
        query = select(TalentEmbedding.talent_id).where(
            TalentEmbedding.talent_id.in_(talent_ids)
        )
        if model_name:
            query = query.where(TalentEmbedding.model_name == model_name)

        result = await self.session.execute(query)
        existing_ids = set(row[0] for row in result.fetchall())

        # 返回缺失的 ID
        return [tid for tid in talent_ids if tid not in existing_ids]

    async def get_existing_talent_ids(self) -> set[int]:
        """
        获取所有已有嵌入向量的人才 ID

        Returns:
            set[int]: 已有嵌入的人才 ID 集合
        """
        result = await self.session.execute(
            select(TalentEmbedding.talent_id)
        )
        return set(row[0] for row in result.fetchall())

    def _embedding_to_str(self, embedding: List[float]) -> str:
        """
        将嵌入向量转换为字符串

        Args:
            embedding: 嵌入向量

        Returns:
            str: 字符串表示
        """
        # 使用 JSON 格式存储
        import json
        return json.dumps(embedding)

    def _str_to_embedding(self, embedding_str: str) -> List[float]:
        """
        将字符串转换为嵌入向量

        Args:
            embedding_str: 字符串表示

        Returns:
            List[float]: 嵌入向量
        """
        import json
        return json.loads(embedding_str)

    def get_embedding_vector(self, record: TalentEmbedding) -> List[float]:
        """
        从记录中获取嵌入向量

        Args:
            record: 嵌入记录

        Returns:
            List[float]: 嵌入向量
        """
        return self._str_to_embedding(record.embedding)
