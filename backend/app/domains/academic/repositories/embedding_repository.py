"""
Embedding Repository.
嵌入向量仓储层 - v1.4

Handles database operations for talent embeddings.

Security Note (S608):
This module uses raw SQL with f-strings for batch operations. All such queries are safe because:
- Values use parameterized placeholders (:param_name)
- No user input is directly interpolated into SQL strings
"""

# ruff: noqa: S608

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import is_postgres as _is_postgres
from app.domains.academic.models.embedding import TalentEmbedding

logger = logging.getLogger(__name__)


class EmbeddingRepository:
    """嵌入向量仓储

    负责嵌入向量的数据库 CRUD 操作。
    支持多种向量类型：research、papers
    """

    # 向量类型常量
    VECTOR_TYPE_RESEARCH = "research"
    VECTOR_TYPE_PAPERS = "papers"

    def __init__(self, session: AsyncSession):
        """
        初始化仓储

        Args:
            session: 数据库会话
        """
        self.session = session

    async def get_by_talent_id(
        self, talent_id: int, vector_type: str = "research"
    ) -> TalentEmbedding | None:
        """
        根据人才 ID 获取嵌入向量

        Args:
            talent_id: 人才 ID
            vector_type: 向量类型 (research/papers)

        Returns:
            Optional[TalentEmbedding]: 嵌入记录或 None
        """
        result = await self.session.execute(
            select(TalentEmbedding).where(
                TalentEmbedding.talent_id == talent_id, TalentEmbedding.vector_type == vector_type
            )
        )
        return result.scalar_one_or_none()

    async def get_by_talent_ids(
        self, talent_ids: list[int], vector_type: str | None = None
    ) -> list[TalentEmbedding]:
        """
        批量获取嵌入向量

        Args:
            talent_ids: 人才 ID 列表
            vector_type: 向量类型过滤 (可选，不过滤则返回全部)

        Returns:
            List[TalentEmbedding]: 嵌入记录列表
        """
        if not talent_ids:
            return []

        # 分批查询，避免 PostgreSQL 参数上限 (32767)
        BATCH_SIZE = 5000
        all_results = []

        for i in range(0, len(talent_ids), BATCH_SIZE):
            batch_ids = talent_ids[i : i + BATCH_SIZE]
            query = select(TalentEmbedding).where(TalentEmbedding.talent_id.in_(batch_ids))
            if vector_type:
                query = query.where(TalentEmbedding.vector_type == vector_type)
            result = await self.session.execute(query)
            all_results.extend(result.scalars().all())

        return all_results

    async def create(
        self,
        talent_id: int,
        embedding: list[float],
        model_name: str,
        source_text_hash: str,
        vector_type: str = "research",
    ) -> TalentEmbedding:
        """
        创建嵌入记录

        Args:
            talent_id: 人才 ID
            embedding: 嵌入向量
            model_name: 模型名称
            source_text_hash: 源文本哈希
            vector_type: 向量类型 (research/papers)

        Returns:
            TalentEmbedding: 创建的记录
        """
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        if _is_postgres(self.session):
            # PostgreSQL: 使用原生 SQL 插入向量
            vector_str = "[" + ",".join(str(v) for v in embedding) + "]"
            # 使用 CAST 函数避免 :: 类型转换与 SQLAlchemy 参数冲突
            await self.session.execute(
                text("""
                    INSERT INTO core_talent_embedding
                    (talent_id, vector_type, embedding, model_name, source_text_hash, created_at, updated_at)
                    VALUES (:talent_id, :vector_type, CAST(:embedding AS vector), :model_name, :source_text_hash, :created_at, :updated_at)
                """),
                {
                    "talent_id": talent_id,
                    "vector_type": vector_type,
                    "embedding": vector_str,
                    "model_name": model_name,
                    "source_text_hash": source_text_hash,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            await self.session.flush()
            # 返回记录（需要重新查询）
            return await self.get_by_talent_id(talent_id, vector_type)
        else:
            # Fallback: 使用 JSON 存储 (non-PostgreSQL)
            embedding_str = json.dumps(embedding)
            record = TalentEmbedding(
                talent_id=talent_id,
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

    async def batch_upsert(
        self,
        items: list[dict],
    ) -> int:
        """
        批量创建或更新嵌入记录

        使用 PostgreSQL 的多行 INSERT ... ON CONFLICT 实现高效批量操作。

        Args:
            items: 嵌入记录列表，每个包含:
                - talent_id: 人才 ID
                - embedding: 嵌入向量
                - model_name: 模型名称
                - source_text_hash: 源文本哈希
                - vector_type: 向量类型 (可选，默认 research)

        Returns:
            int: 处理的记录数
        """
        if not items:
            return 0

        now = datetime.now(timezone.utc).replace(tzinfo=None)

        if _is_postgres(self.session):
            # PostgreSQL: 使用原生 SQL 批量 UPSERT
            values_clauses = []
            params = {}
            for i, item in enumerate(items):
                vector_str = "[" + ",".join(str(v) for v in item["embedding"]) + "]"
                vector_type = item.get("vector_type", "research")
                values_clauses.append(
                    f"(:talent_id_{i}, :vector_type_{i}, CAST(:embedding_{i} AS vector), :model_name_{i}, :hash_{i}, :created_at, :updated_at)"
                )
                params[f"talent_id_{i}"] = item["talent_id"]
                params[f"vector_type_{i}"] = vector_type
                params[f"embedding_{i}"] = vector_str
                params[f"model_name_{i}"] = item["model_name"]
                params[f"hash_{i}"] = item["source_text_hash"]

            params["created_at"] = now
            params["updated_at"] = now

            # Safe: values_clauses use only parameterized placeholders, no user input in SQL string
            sql = f"""
                INSERT INTO core_talent_embedding
                (talent_id, vector_type, embedding, model_name, source_text_hash, created_at, updated_at)
                VALUES {', '.join(values_clauses)}
                ON CONFLICT (talent_id, vector_type) DO UPDATE SET
                    embedding = EXCLUDED.embedding,
                    model_name = EXCLUDED.model_name,
                    source_text_hash = EXCLUDED.source_text_hash,
                    updated_at = EXCLUDED.updated_at
            """

            await self.session.execute(text(sql), params)
            await self.session.flush()
            return len(items)
        else:
            # Fallback: 逐个处理（non-PostgreSQL）
            for item in items:
                await self.upsert(
                    talent_id=item["talent_id"],
                    embedding=item["embedding"],
                    model_name=item["model_name"],
                    source_text_hash=item["source_text_hash"],
                    vector_type=item.get("vector_type", "research"),
                )
            return len(items)

    async def upsert(
        self,
        talent_id: int,
        embedding: list[float],
        model_name: str,
        source_text_hash: str,
        vector_type: str = "research",
    ) -> TalentEmbedding:
        """
        创建或更新嵌入记录

        Args:
            talent_id: 人才 ID
            embedding: 嵌入向量
            model_name: 模型名称
            source_text_hash: 源文本哈希
            vector_type: 向量类型 (research/papers)

        Returns:
            TalentEmbedding: 记录
        """
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        if _is_postgres(self.session):
            # PostgreSQL: 使用原生 SQL UPSERT
            vector_str = "[" + ",".join(str(v) for v in embedding) + "]"
            # 使用 CAST 函数避免 :: 类型转换与 SQLAlchemy 参数冲突
            await self.session.execute(
                text("""
                    INSERT INTO core_talent_embedding
                    (talent_id, vector_type, embedding, model_name, source_text_hash, created_at, updated_at)
                    VALUES (:talent_id, :vector_type, CAST(:embedding AS vector), :model_name, :source_text_hash, :created_at, :updated_at)
                    ON CONFLICT (talent_id, vector_type) DO UPDATE SET
                        embedding = EXCLUDED.embedding,
                        model_name = EXCLUDED.model_name,
                        source_text_hash = EXCLUDED.source_text_hash,
                        updated_at = EXCLUDED.updated_at
                """),
                {
                    "talent_id": talent_id,
                    "vector_type": vector_type,
                    "embedding": vector_str,
                    "model_name": model_name,
                    "source_text_hash": source_text_hash,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            await self.session.flush()
            return await self.get_by_talent_id(talent_id, vector_type)
        else:
            # Fallback: 使用 JSON 存储 (non-PostgreSQL)
            existing = await self.get_by_talent_id(talent_id, vector_type)

            if existing:
                existing.embedding = json.dumps(embedding)
                existing.model_name = model_name
                existing.source_text_hash = source_text_hash
                existing.updated_at = now
                await self.session.flush()
                return existing
            else:
                return await self.create(
                    talent_id, embedding, model_name, source_text_hash, vector_type
                )

    async def count(self) -> int:
        """
        统计嵌入记录总数

        Returns:
            int: 记录数
        """
        from sqlalchemy import func

        result = await self.session.execute(select(func.count()).select_from(TalentEmbedding))
        return result.scalar() or 0

    async def get_embedding_status(self) -> dict:
        """
        获取嵌入生成状态统计

        Returns:
            dict: 包含 total_talents, embedded_talents, last_generated
        """
        from sqlalchemy import func

        from app.domains.academic.models.talent import Talent

        # Count total visible talents
        total_result = await self.session.execute(
            select(func.count()).select_from(Talent).where(Talent.is_visible.is_(True))
        )
        total_talents = total_result.scalar() or 0

        # Count talents with embeddings
        embedded_result = await self.session.execute(
            select(func.count()).select_from(TalentEmbedding)
        )
        embedded_talents = embedded_result.scalar() or 0

        # Get last embedding creation time
        last_result = await self.session.execute(
            select(TalentEmbedding.created_at).order_by(TalentEmbedding.created_at.desc()).limit(1)
        )
        last_row = last_result.scalar_one_or_none()
        last_generated = last_row.isoformat() if last_row else None

        return {
            "total_talents": total_talents,
            "embedded_talents": embedded_talents,
            "last_generated": last_generated,
        }

    async def get_visible_talent_ids(self) -> list[int]:
        """
        获取所有可见人才的 ID 列表

        Returns:
            List[int]: 人才 ID 列表
        """
        from app.domains.academic.models.talent import Talent

        result = await self.session.execute(
            select(Talent.talent_id).where(Talent.is_visible.is_(True)).order_by(Talent.talent_id)
        )
        return [row[0] for row in result.fetchall()]

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
        self, talent_ids: list[int], model_name: str | None = None, vector_type: str | None = None
    ) -> list[int]:
        """
        获取没有嵌入向量的人才 ID

        Args:
            talent_ids: 人才 ID 列表
            model_name: 可选的模型名称过滤
            vector_type: 可选的向量类型过滤 (research/papers)

        Returns:
            List[int]: 缺失嵌入的人才 ID 列表
        """
        if not talent_ids:
            return []

        # 分批查询已有嵌入的人才 ID，避免 PostgreSQL 参数上限 (32767)
        BATCH_SIZE = 5000
        existing_ids = set()

        for i in range(0, len(talent_ids), BATCH_SIZE):
            batch_ids = talent_ids[i : i + BATCH_SIZE]
            query = select(TalentEmbedding.talent_id).where(
                TalentEmbedding.talent_id.in_(batch_ids)
            )
            if model_name:
                query = query.where(TalentEmbedding.model_name == model_name)
            if vector_type:
                query = query.where(TalentEmbedding.vector_type == vector_type)

            result = await self.session.execute(query)
            for row in result.fetchall():
                existing_ids.add(row[0])

        return [tid for tid in talent_ids if tid not in existing_ids]

    def _str_to_embedding(self, embedding_str: str) -> list[float]:
        """
        将字符串转换为嵌入向量

        Args:
            embedding_str: 字符串表示

        Returns:
            List[float]: 嵌入向量
        """
        if not embedding_str:
            return []

        # PostgreSQL vector 格式: '[0.1,0.2,...]'
        # JSON 格式: '[0.1, 0.2, ...]'
        try:
            return json.loads(embedding_str)
        except json.JSONDecodeError:
            # 尝试解析 PostgreSQL vector 格式
            return [float(v.strip()) for v in embedding_str.strip("[]").split(",") if v.strip()]

    def get_embedding_vector(self, record: TalentEmbedding) -> list[float]:
        """
        从记录中获取嵌入向量

        Args:
            record: 嵌入记录

        Returns:
            List[float]: 嵌入向量
        """
        return self._str_to_embedding(record.embedding)
