"""
Search Service implementation.
搜索服务实现 - v1.4

Features:
- Keyword search (ILIKE pattern matching)
- Fulltext search (PostgreSQL tsvector)
- Semantic search (vector similarity)
- Hybrid search (combination)
- Multi-field search
- Fuzzy matching
"""

from __future__ import annotations

import asyncio
import time
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Any

from sqlalchemy import select, or_, and_, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.talent import Talent
from app.models.school import School
from app.models.search import SearchTalentDocument
from app.services.search.errors import EmptyQueryError, InvalidSearchModeError

logger = logging.getLogger(__name__)


class SearchMode(str, Enum):
    """搜索模式"""
    KEYWORD = "keyword"      # 关键词搜索 (ILIKE)
    FULLTEXT = "fulltext"    # 全文搜索 (tsvector)
    SEMANTIC = "semantic"    # 语义搜索 (向量)
    HYBRID = "hybrid"        # 混合搜索


# 学术领域常见缩写同义词映射
SYNONYM_MAP = {
    # AI/ML 领域 - 英文缩写
    "ml": "machine learning",
    "dl": "deep learning",
    "nlp": "natural language processing",
    "cv": "computer vision",
    "ai": "artificial intelligence",
    "nn": "neural network",
    "cnn": "convolutional neural network",
    "rnn": "recurrent neural network",
    "gan": "generative adversarial network",
    "transformer": "transformer attention mechanism",
    "llm": "large language model",
    "rl": "reinforcement learning",
    "svm": "support vector machine",
    "knn": "k-nearest neighbors",
    "pca": "principal component analysis",
    # 系统领域
    "os": "operating system",
    "db": "database",
    "io": "input output",
    "cpu": "central processing unit",
    "gpu": "graphics processing unit",
    "ram": "random access memory",
    # 网络领域
    "tcp": "transmission control protocol",
    "ip": "internet protocol",
    "http": "hypertext transfer protocol",
    "api": "application programming interface",
    "sdn": "software defined networking",
    # 安全领域
    "aes": "advanced encryption standard",
    "rsa": "rivest shamir adleman encryption",
    "ddos": "distributed denial of service",
    # 数据科学
    "bi": "business intelligence",
    "etl": "extract transform load",
    "dw": "data warehouse",
}

# 中英文翻译映射（仅用于语义搜索，使用英文 embedding）
CHINESE_TO_ENGLISH_MAP = {
    "机器学习": "machine learning",
    "深度学习": "deep learning",
    "自然语言处理": "natural language processing",
    "计算机视觉": "computer vision",
    "人工智能": "artificial intelligence",
    "神经网络": "neural network",
    "强化学习": "reinforcement learning",
    "数据挖掘": "data mining",
    "数据科学": "data science",
    "大数据": "big data",
    "云计算": "cloud computing",
    "物联网": "internet of things",
    "机器人": "robotics",
    "信息安全": "information security",
    "网络安全": "cybersecurity",
    "分布式系统": "distributed systems",
    "操作系统": "operating system",
    "数据库": "database",
}


def expand_query_with_synonyms(query: str) -> str:
    """
    扩展查询词，添加同义词（用于全文搜索）

    Args:
        query: 原始查询

    Returns:
        str: 扩展后的查询（原始查询 + 同义词）
    """
    query_lower = query.lower().strip()

    # 检查是否是已知缩写
    if query_lower in SYNONYM_MAP:
        synonym = SYNONYM_MAP[query_lower]
        # 返回原词 + 同义词，用于全文搜索
        return f"{query} {synonym}"

    return query


def get_english_translation(query: str) -> str | None:
    """
    获取中文查询的英文翻译（用于语义搜索 embedding）

    Args:
        query: 原始查询

    Returns:
        str | None: 英文翻译，如果没有则返回 None
    """
    query_stripped = query.strip()

    # 检查是否是中文术语
    if query_stripped in CHINESE_TO_ENGLISH_MAP:
        return CHINESE_TO_ENGLISH_MAP[query_stripped]

    # 也检查小写版本（针对英文缩写）
    query_lower = query_stripped.lower()
    if query_lower in SYNONYM_MAP:
        return SYNONYM_MAP[query_lower]

    return None


@dataclass
class SearchResult:
    """搜索结果"""
    total: int
    page: int
    page_size: int
    items: List[dict]
    search_mode: str
    took_ms: float

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "total": self.total,
            "page": self.page,
            "page_size": self.page_size,
            "items": self.items,
            "search_mode": self.search_mode,
            "took_ms": self.took_ms,
        }


@dataclass
class SearchConfig:
    """搜索配置"""
    min_query_length: int = 1
    max_page_size: int = 100
    default_page_size: int = 20
    default_mode: SearchMode = SearchMode.KEYWORD


class SearchService:
    """搜索服务

    支持多种搜索模式：
    - KEYWORD: 使用 ILIKE 进行模式匹配
    - FULLTEXT: 使用 PostgreSQL tsvector 全文搜索
    - SEMANTIC: 使用向量相似度搜索
    - HYBRID: 结合多种搜索模式
    """

    def __init__(
        self,
        session: AsyncSession,
        embedding_service: Any = None,
        config: SearchConfig | None = None
    ):
        """
        初始化搜索服务

        Args:
            session: 数据库会话
            embedding_service: 嵌入服务（可选，用于语义搜索）
            config: 搜索配置
        """
        self.session = session
        self.embedding_service = embedding_service
        self.config = config or SearchConfig()

    async def search(
        self,
        query: str,
        mode: SearchMode | str = SearchMode.KEYWORD,
        fields: List[str] | None = None,
        fuzzy: bool = False,
        page: int = 1,
        page_size: int | None = None,
        filters: dict | None = None,
    ) -> SearchResult:
        """
        统一搜索入口

        Args:
            query: 搜索关键词
            mode: 搜索模式
            fields: 搜索字段列表
            fuzzy: 是否启用模糊匹配
            page: 页码
            page_size: 每页数量
            filters: 额外过滤条件

        Returns:
            SearchResult: 搜索结果

        Raises:
            EmptyQueryError: 空查询
            InvalidSearchModeError: 无效搜索模式
        """
        start_time = time.time()

        # 验证查询
        query = query.strip()
        if len(query) < self.config.min_query_length:
            raise EmptyQueryError()

        # 规范化模式
        if isinstance(mode, str):
            try:
                mode = SearchMode(mode.lower())
            except ValueError:
                # 无效模式，默认使用关键词搜索
                mode = SearchMode.KEYWORD

        # 规范化分页参数
        if page_size is None:
            page_size = self.config.default_page_size
        page_size = min(page_size, self.config.max_page_size)
        page = max(1, page)

        # 根据模式执行搜索
        if mode == SearchMode.KEYWORD:
            result = await self._keyword_search(query, fields, fuzzy, page, page_size, filters)
        elif mode == SearchMode.FULLTEXT:
            result = await self._fulltext_search(query, page, page_size, filters)
        elif mode == SearchMode.SEMANTIC:
            result = await self._semantic_search(query, page, page_size, filters)
        elif mode == SearchMode.HYBRID:
            result = await self._hybrid_search(query, fields, fuzzy, page, page_size, filters)
        else:
            result = await self._keyword_search(query, fields, fuzzy, page, page_size, filters)

        # 计算耗时
        took_ms = (time.time() - start_time) * 1000

        return SearchResult(
            total=result["total"],
            page=page,
            page_size=page_size,
            items=result["items"],
            search_mode=mode.value if isinstance(mode, SearchMode) else mode,
            took_ms=took_ms,
        )

    async def _keyword_search(
        self,
        query: str,
        fields: List[str] | None,
        fuzzy: bool,
        page: int,
        page_size: int,
        filters: dict | None,
    ) -> dict:
        """
        关键词搜索

        使用 ILIKE 进行模式匹配。
        搜索范围：姓名、职位、研究方向、研究主题(openalex_topics)、论文标题
        """
        # 默认搜索字段
        if fields is None:
            fields = ["name", "title", "research_interests", "topics", "works"]

        # 构建搜索条件
        pattern = f"%{query}%"

        # 基础查询
        query_stmt = (
            select(Talent)
            .options(selectinload(Talent.school))
            .where(Talent.is_visible.is_(True))
        )

        # 字段映射（直接用 ORM 列的）
        field_mapping = {
            "name": [Talent.name, Talent.name_en],
            "title": [Talent.current_title],
            "research_interests": [Talent.research_interests],
        }

        # 构建基础搜索条件
        search_conditions = []
        for field in fields:
            if field in field_mapping:
                for col in field_mapping[field]:
                    if col is not None:
                        search_conditions.append(col.ilike(pattern))

        # 添加 openalex_topics 搜索（JSON 数组字段转为文本搜索）
        if "topics" in fields:
            # 使用 PostgreSQL 的 ::text 转换来搜索 JSON 数组
            search_conditions.append(
                text("core_talent.openalex_topics::text ILIKE :pattern").bindparams(pattern=pattern)
            )

        # 添加论文标题搜索（使用 EXISTS 子查询）
        if "works" in fields:
            # author_ids 是 text 类型存储的 JSON 数组，需要转为 jsonb
            work_exists = text("""
                EXISTS (
                    SELECT 1
                    FROM raw_work rw
                    JOIN std_author sa ON sa.openalex_author_id = ANY(
                        SELECT jsonb_array_elements_text(rw.author_ids::jsonb)
                    )
                    WHERE sa.std_author_id = core_talent.std_author_id
                    AND rw.title ILIKE :pattern
                )
            """).bindparams(pattern=pattern)
            search_conditions.append(work_exists)

        if search_conditions:
            query_stmt = query_stmt.where(or_(*search_conditions))

        # 应用额外过滤
        query_stmt = self._apply_filters(query_stmt, filters)

        # 获取总数
        count_query = select(func.count()).select_from(query_stmt.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # 分页
        offset = (page - 1) * page_size
        query_stmt = query_stmt.order_by(Talent.cited_by_count.desc())
        query_stmt = query_stmt.offset(offset).limit(page_size)

        result = await self.session.execute(query_stmt)
        talents = list(result.scalars().all())

        # 转换结果
        items = [self._talent_to_dict(t) for t in talents]

        return {"total": total, "items": items}

    async def _fulltext_search(
        self,
        query: str,
        page: int,
        page_size: int,
        filters: dict | None,
    ) -> dict:
        """
        全文搜索

        使用 PostgreSQL tsvector 进行全文搜索。
        如果 SearchTalentDocument 表没有数据，则降级到关键词搜索。
        """
        try:
            # 检查是否有全文搜索支持
            # 首先检查 SearchTalentDocument 表是否有数据
            count_query = select(func.count()).select_from(SearchTalentDocument)
            count_result = await self.session.execute(count_query)
            doc_count = count_result.scalar() or 0

            if doc_count == 0:
                logger.info("SearchTalentDocument table is empty, falling back to keyword search")
                return await self._keyword_search(query, ["name", "title", "research_interests", "topics", "works"], False, page, page_size, filters)

            # 使用 search_text 进行简单匹配
            pattern = f"%{query}%"
            query_stmt = (
                select(SearchTalentDocument)
                .where(SearchTalentDocument.is_active.is_(True))
                .where(SearchTalentDocument.search_text.ilike(pattern))
            )

            # 应用过滤
            if filters:
                if "school_id" in filters:
                    query_stmt = query_stmt.where(
                        SearchTalentDocument.school_id == filters["school_id"]
                    )
                if "role_type" in filters:
                    query_stmt = query_stmt.where(
                        SearchTalentDocument.role_type == filters["role_type"]
                    )

            # 获取总数
            count_query = select(func.count()).select_from(query_stmt.subquery())
            total_result = await self.session.execute(count_query)
            total = total_result.scalar() or 0

            # 分页
            offset = (page - 1) * page_size
            query_stmt = query_stmt.order_by(SearchTalentDocument.cited_by_count.desc())
            query_stmt = query_stmt.offset(offset).limit(page_size)

            result = await self.session.execute(query_stmt)
            docs = list(result.scalars().all())

            # 转换结果 - 获取完整人才信息
            items = []
            for doc in docs:
                item = {
                    "talent_id": doc.talent_id,
                    "name": doc.name,
                    "name_en": None,
                    "title": None,
                    "school_id": doc.school_id,
                    "school_name": doc.school_name,
                    "role_type": doc.role_type,
                    "research_interests": None,
                    "topic_tags": doc.topic_tags or [],
                    "openalex_topics": [],  # SearchTalentDocument 没有 openalex_topics，需要从 core_talent 获取
                    "works_count": doc.works_count,
                    "cited_by_count": doc.cited_by_count,
                    "h_index": doc.h_index,
                    "orcid": doc.orcid,
                }
                items.append(item)

            return {"total": total, "items": items}

        except Exception as e:
            logger.warning(f"Fulltext search failed: {e}, falling back to keyword search")
            return await self._keyword_search(query, ["name", "title", "research_interests", "topics", "works"], False, page, page_size, filters)

    async def _semantic_search(
        self,
        query: str,
        page: int,
        page_size: int,
        filters: dict | None,
    ) -> dict:
        """
        语义搜索

        使用向量相似度进行搜索。
        如果没有嵌入服务，降级到全文搜索。
        """
        # 检查嵌入服务
        if self.embedding_service is None:
            logger.warning("Semantic search requested but no embedding service, falling back to fulltext")
            return await self._fulltext_search(query, page, page_size, filters)

        try:
            # 检查是否有中文到英文的翻译映射
            english_translation = get_english_translation(query)

            if english_translation:
                # 中文查询：使用英文翻译生成 embedding（避免拼接导致的语义偏差）
                embedding_text = english_translation
                logger.info(f"Chinese query '{query}' -> English embedding '{english_translation}'")
            else:
                # 英文查询：同义词扩展后生成 embedding
                embedding_text = expand_query_with_synonyms(query)
                if embedding_text != query:
                    logger.info(f"Query expanded: '{query}' -> '{embedding_text}'")

            # 获取查询嵌入向量
            query_embedding = await self.embedding_service.get_query_embedding(embedding_text)

            # 使用 pgvector 进行向量相似度搜索
            # 将向量转换为 PostgreSQL 格式（纯数值，安全）
            vector_str = '[' + ','.join(str(v) for v in query_embedding) + ']'

            # 计算偏移量
            offset = (page - 1) * page_size

            # 构建基础查询
            # 注意：向量字符串直接嵌入 SQL，因为它是纯数值，没有 SQL 注入风险
            base_query = f"""
                SELECT t.talent_id, t.name, t.name_en, t.current_title, t.school_id,
                       t.role_type, t.research_interests, t.topic_tags, t.openalex_topics,
                       t.works_count, t.cited_by_count, t.h_index, t.orcid,
                       s.school_name,
                       e.embedding <=> '{vector_str}'::vector AS distance
                FROM core_talent t
                LEFT JOIN core_school s ON t.school_id = s.school_id
                INNER JOIN core_talent_embedding e ON t.talent_id = e.talent_id
                WHERE 1=1
            """

            # 添加过滤条件
            filter_params = {}
            filter_clauses = []

            if filters:
                if "school_id" in filters:
                    filter_clauses.append("t.school_id = :school_id")
                    filter_params["school_id"] = filters["school_id"]
                if "role_type" in filters:
                    filter_clauses.append("t.role_type = :role_type")
                    filter_params["role_type"] = filters["role_type"]
                if "min_citations" in filters:
                    filter_clauses.append("t.cited_by_count >= :min_citations")
                    filter_params["min_citations"] = filters["min_citations"]

            if filter_clauses:
                base_query += " AND " + " AND ".join(filter_clauses)

            # 计算总数
            count_query = f"SELECT COUNT(*) as total FROM ({base_query}) subq"
            count_result = await self.session.execute(text(count_query), filter_params)
            total = count_result.scalar() or 0

            # 获取分页结果
            # 相似度阈值：distance <= 0.3 即相似度 >= 70%
            data_query = f"""
                {base_query}
                AND e.embedding <=> '{vector_str}'::vector <= 0.3
                ORDER BY distance ASC
                LIMIT :limit OFFSET :offset
            """
            filter_params["limit"] = page_size
            filter_params["offset"] = offset

            result = await self.session.execute(text(data_query), filter_params)
            rows = result.fetchall()

            # 转换结果，并过滤低于阈值的结果
            items = []
            for row in rows:
                similarity = 1.0 - (row.distance or 0)
                # 再次确认相似度 >= 70%
                if similarity >= 0.7:
                    items.append({
                        "talent_id": row.talent_id,
                        "name": row.name,
                        "name_en": row.name_en,
                        "title": row.current_title,
                        "school_id": row.school_id,
                        "school_name": row.school_name,
                        "role_type": row.role_type,
                        "research_interests": row.research_interests,
                        "topic_tags": row.topic_tags or [],
                        "openalex_topics": row.openalex_topics or [],
                        "works_count": row.works_count,
                        "cited_by_count": row.cited_by_count,
                        "h_index": row.h_index,
                        "orcid": row.orcid,
                        "similarity_score": similarity,
                    })

            # 更新总数为实际过滤后的数量
            total = len(items)

            logger.info(f"Semantic search found {total} results (similarity >= 70%) for query: {query}")

            return {
                "total": total,
                "items": items,
            }

        except Exception as e:
            logger.error(f"Semantic search failed: {e}, falling back to fulltext")
            # 回滚失败的事务，确保后续查询可以执行
            await self.session.rollback()
            return await self._fulltext_search(query, page, page_size, filters)

    async def _hybrid_search(
        self,
        query: str,
        fields: List[str] | None,
        fuzzy: bool,
        page: int,
        page_size: int,
        filters: dict | None,
    ) -> dict:
        """
        混合搜索

        结合全文搜索和语义搜索的结果，重新排序。
        """
        # 如果没有嵌入服务，降级到全文搜索
        if self.embedding_service is None:
            logger.info("Hybrid search: no embedding service, using fulltext only")
            return await self._fulltext_search(query, page, page_size, filters)

        try:
            # 并行执行全文搜索和语义搜索
            # 获取更多结果用于融合
            extended_page_size = min(page_size * 3, 100)

            # 检查是否有中文到英文的翻译
            english_translation = get_english_translation(query)

            # 全文搜索：同时使用中文和英文
            fulltext_tasks = []
            fulltext_tasks.append(self._fulltext_search(query, 1, extended_page_size, filters))

            # 如果有英文翻译，也用英文执行全文搜索
            if english_translation:
                logger.info(f"Hybrid search: also searching with English translation '{english_translation}'")
                fulltext_tasks.append(self._fulltext_search(english_translation, 1, extended_page_size, filters))

            # 并行执行所有全文搜索
            fulltext_results = await asyncio.gather(*fulltext_tasks, return_exceptions=True)

            # 合并全文搜索结果，处理可能的异常
            fulltext_merged = {}
            for result in fulltext_results:
                if isinstance(result, Exception):
                    logger.warning(f"Fulltext search task failed: {result}")
                    continue
                for item in result["items"]:
                    tid = item["talent_id"]
                    if tid not in fulltext_merged:
                        fulltext_merged[tid] = item

            fulltext_result = {"items": list(fulltext_merged.values())}

            # 语义搜索
            semantic_result = await self._semantic_search(query, 1, extended_page_size, filters)

            # 融合结果
            # 使用倒数排名融合 (Reciprocal Rank Fusion)
            k = 60  # RRF 常数
            score_map = {}  # talent_id -> combined_score
            item_map = {}   # talent_id -> item data

            # 全文搜索结果（精准匹配，给高分）
            for rank, item in enumerate(fulltext_result["items"], 1):
                tid = item["talent_id"]
                score_map[tid] = score_map.get(tid, 0) + 1.0 / (k + rank)
                # 全文搜索匹配的给高分相似度（95%+）
                item["similarity_score"] = 0.95
                item_map[tid] = item

            # 语义搜索结果（已过滤相似度 >= 70%）
            for rank, item in enumerate(semantic_result["items"], 1):
                tid = item["talent_id"]
                score_map[tid] = score_map.get(tid, 0) + 1.0 / (k + rank)
                # 如果已存在（全文搜索命中），保留较高的相似度
                if tid in item_map:
                    existing_score = item_map[tid].get("similarity_score", 0)
                    new_score = item.get("similarity_score", 0)
                    if new_score > existing_score:
                        item_map[tid]["similarity_score"] = new_score
                else:
                    item_map[tid] = item

            # 按相似度排序（优先显示精准匹配）
            sorted_ids = sorted(
                item_map.keys(),
                key=lambda x: (item_map[x].get("similarity_score", 0), score_map.get(x, 0)),
                reverse=True
            )

            # 分页
            offset = (page - 1) * page_size
            paginated_ids = sorted_ids[offset:offset + page_size]

            # 构建最终结果
            items = [item_map[tid] for tid in paginated_ids if tid in item_map]

            logger.info(f"Hybrid search: fulltext={len(fulltext_result['items'])}, semantic={len(semantic_result['items'])}, merged={len(sorted_ids)}, returned={len(items)}")

            return {
                "total": len(sorted_ids),
                "items": items,
            }

        except Exception as e:
            logger.error(f"Hybrid search failed: {e}, falling back to keyword search")
            # 回滚失败的事务
            await self.session.rollback()
            return await self._keyword_search(query, fields, fuzzy, page, page_size, filters)

    def _apply_filters(self, query, filters: dict | None):
        """应用过滤条件"""
        if not filters:
            return query

        if "school_id" in filters:
            query = query.where(Talent.school_id == filters["school_id"])

        if "role_type" in filters:
            query = query.where(Talent.role_type == filters["role_type"])

        if "min_citations" in filters:
            query = query.where(Talent.cited_by_count >= filters["min_citations"])

        if "min_works" in filters:
            query = query.where(Talent.works_count >= filters["min_works"])

        if "tech_elements" in filters:
            # 技术要素过滤需要join
            pass

        return query

    def _talent_to_dict(self, talent: Talent) -> dict:
        """将 Talent 模型转换为字典"""
        return {
            "talent_id": talent.talent_id,
            "name": talent.name,
            "name_en": talent.name_en,
            "title": talent.current_title,
            "school_id": talent.school_id,
            "school_name": talent.school.school_name if talent.school else None,
            "role_type": talent.role_type,
            "research_interests": talent.research_interests,
            "topic_tags": talent.topic_tags or [],
            "openalex_topics": talent.openalex_topics or [],
            "works_count": talent.works_count,
            "cited_by_count": talent.cited_by_count,
            "h_index": talent.h_index,
            "orcid": talent.orcid,
        }
