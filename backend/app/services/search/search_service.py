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
from app.repositories.talent_repository import TalentRepository
from app.services.search.errors import EmptyQueryError, InvalidSearchModeError
from app.services.llm.errors import (
    SemanticSearchError,
    FulltextSearchError,
    EmbeddingServiceError,
    LLMError,
)
from app.core.config import settings

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
    precise_count: int = 0  # 精准匹配数量 (similarity >= 0.95)
    similar_count: int = 0  # 相似匹配数量 (0.7 <= similarity < 0.95)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "total": self.total,
            "page": self.page,
            "page_size": self.page_size,
            "items": self.items,
            "search_mode": self.search_mode,
            "took_ms": self.took_ms,
            "precise_count": self.precise_count,
            "similar_count": self.similar_count,
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
        config: SearchConfig | None = None,
        talent_repository: TalentRepository | None = None,
    ):
        """
        初始化搜索服务

        Args:
            session: 数据库会话
            embedding_service: 嵌入服务（可选，用于语义搜索）
            config: 搜索配置
            talent_repository: 人才数据仓储（可选，默认自动创建）
        """
        self.session = session
        self.embedding_service = embedding_service
        self.config = config or SearchConfig()
        self.talent_repo = talent_repository or TalentRepository(session)

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

        # 从结果中获取精准匹配和相似匹配数量
        precise_count = result.get("precise_count", 0)
        similar_count = result.get("similar_count", 0)

        return SearchResult(
            total=result["total"],
            page=page,
            page_size=page_size,
            items=result["items"],
            search_mode=mode.value if isinstance(mode, SearchMode) else mode,
            took_ms=took_ms,
            precise_count=precise_count,
            similar_count=similar_count,
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
        关键词搜索（使用 GIN 索引优化）

        搜索范围：姓名、职位、研究方向(openalex_topics)、论文标题
        使用 GIN 索引加速 JSON 数组和全文搜索。
        """
        # 默认搜索字段
        if fields is None:
            fields = ["name", "title", "topics", "works"]

        # 收集匹配的人才 ID
        matched_talent_ids: set = set()
        pattern = f"%{query}%"

        # 1. 姓名、职位搜索（使用 ILIKE，无专门索引）
        basic_fields = [f for f in fields if f in ["name", "title"]]
        if basic_fields:
            query_stmt = (
                select(Talent.talent_id)
                .where(Talent.is_visible.is_(True))
            )

            field_mapping = {
                "name": [Talent.name, Talent.name_en],
                "title": [Talent.current_title],
            }

            search_conditions = []
            for field in basic_fields:
                for col in field_mapping.get(field, []):
                    if col is not None:
                        search_conditions.append(col.ilike(pattern))

            if search_conditions:
                query_stmt = query_stmt.where(or_(*search_conditions))
                query_stmt = self._apply_filters(query_stmt, filters)
                result = await self.session.execute(query_stmt)
                for row in result.fetchall():
                    matched_talent_ids.add(row.talent_id)

        # 2. 研究方向搜索（使用模糊匹配，因为 openalex_topics 值通常是复合词）
        if "topics" in fields:
            # 使用 ILIKE 进行子串匹配
            query_stmt = (
                select(Talent.talent_id)
                .where(Talent.is_visible.is_(True))
                .where(text("core_talent.openalex_topics::text ILIKE :pattern").bindparams(pattern=pattern))
            )
            query_stmt = self._apply_filters(query_stmt, filters)
            result = await self.session.execute(query_stmt)
            for row in result.fetchall():
                matched_talent_ids.add(row.talent_id)

        # 3. 论文标题搜索（使用 pg_trgm GIN 索引）
        if "works" in fields:
            try:
                work_talents = await self.talent_repo._search_by_paper_titles_gin(
                    keywords=[query],
                    filters=filters,
                    limit=page_size * 3,
                )
                for t in work_talents:
                    matched_talent_ids.add(t.talent_id)
            except Exception as e:
                logger.warning(f"Paper title GIN search failed: {e}")

        # 4. 如果没有匹配，返回空结果
        if not matched_talent_ids:
            return {"total": 0, "items": []}

        # 5. 获取完整人才数据并排序
        talent_ids_list = list(matched_talent_ids)
        talents = await self.talent_repo.get_by_ids(talent_ids_list, include_relations=True)

        # 按引用数排序
        talents.sort(key=lambda t: t.cited_by_count or 0, reverse=True)

        # 6. 计算总数和分页
        total = len(talents)
        offset = (page - 1) * page_size
        paginated_talents = talents[offset:offset + page_size]

        # 7. 转换结果
        items = [self._talent_to_dict(t) for t in paginated_talents]

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
                return await self._keyword_search(query, ["name", "title", "topics", "works"], False, page, page_size, filters)

            # 构建 tsquery 搜索词（使用 OR 连接多个词）
            # 将查询词分词并用 OR 连接，支持部分匹配
            search_terms = query.strip().split()
            tsquery = " | ".join(search_terms)  # OR 搜索，任一词匹配即可

            # 使用 tsvector 索引进行全文搜索
            query_stmt = (
                select(SearchTalentDocument)
                .where(SearchTalentDocument.is_active.is_(True))
                .where(
                    text("search_vector @@ to_tsquery('simple', :tsquery)").bindparams(tsquery=tsquery)
                )
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

            # 如果 tsquery 搜索没有结果，尝试降级到 ILIKE 搜索
            if total == 0:
                logger.info(f"tsquery search returned 0 results, falling back to ILIKE for query: {query}")
                pattern = f"%{query}%"
                query_stmt = (
                    select(SearchTalentDocument)
                    .where(SearchTalentDocument.is_active.is_(True))
                    .where(SearchTalentDocument.search_text.ilike(pattern))
                )

                # 重新应用过滤
                if filters:
                    if "school_id" in filters:
                        query_stmt = query_stmt.where(
                            SearchTalentDocument.school_id == filters["school_id"]
                        )
                    if "role_type" in filters:
                        query_stmt = query_stmt.where(
                            SearchTalentDocument.role_type == filters["role_type"]
                        )

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
            # 全文搜索失败，降级到关键词搜索
            logger.warning(f"Fulltext search failed: {e}, falling back to keyword search")
            return await self._keyword_search(query, ["name", "title", "topics", "works"], False, page, page_size, filters)

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

            # 计算偏移量
            offset = (page - 1) * page_size

            # 使用 Repository 进行向量相似度搜索
            items, total = await self.talent_repo.search_by_vector_similarity(
                query_embedding=query_embedding,
                similarity_threshold=settings.SEARCH_SEMANTIC_THRESHOLD,
                filters=filters,
                limit=page_size,
                offset=offset,
            )

            # 统计精准匹配和相似匹配
            precise_count = sum(1 for item in items if item.get("similarity_score", 0) >= settings.SEARCH_PRECISE_THRESHOLD)
            similar_count = sum(1 for item in items if settings.SEARCH_SIMILAR_THRESHOLD_MIN <= item.get("similarity_score", 0) < settings.SEARCH_PRECISE_THRESHOLD)

            logger.info(f"Semantic search found {total} results (similarity >= 70%) for query: {query}")

            return {
                "total": total,
                "items": items,
                "precise_count": precise_count,
                "similar_count": similar_count,
            }

        except LLMError as e:
            # LLM 错误：可降级到全文搜索
            logger.warning(f"Semantic search LLM error: {e}, falling back to fulltext")
            await self.session.rollback()
            return await self._fulltext_search(query, page, page_size, filters)
        except ValueError as e:
            # 向量格式错误：可降级
            logger.warning(f"Semantic search vector error: {e}, falling back to fulltext")
            await self.session.rollback()
            return await self._fulltext_search(query, page, page_size, filters)
        except Exception as e:
            # 其他未知错误：记录并降级
            logger.error(f"Semantic search unexpected error: {e}, falling back to fulltext")
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
            extended_page_size = min(page_size * settings.SEARCH_HYBRID_EXTENDED_FACTOR, 100)

            # 检查是否有中文到英文的翻译
            english_translation = get_english_translation(query)

            # 全文搜索：顺序执行中文和英文搜索（避免 session 并发问题）
            fulltext_items = {}

            # 1. 中文全文搜索
            chinese_result = await self._fulltext_search(query, 1, extended_page_size, filters)
            for item in chinese_result["items"]:
                tid = item["talent_id"]
                if tid not in fulltext_items:
                    fulltext_items[tid] = item

            # 2. 如果有英文翻译，也用英文执行全文搜索
            if english_translation:
                logger.info(f"Hybrid search: also searching with English translation '{english_translation}'")
                english_result = await self._fulltext_search(english_translation, 1, extended_page_size, filters)
                for item in english_result["items"]:
                    tid = item["talent_id"]
                    if tid not in fulltext_items:
                        fulltext_items[tid] = item

            fulltext_result = {"items": list(fulltext_items.values())}

            # 语义搜索
            semantic_result = await self._semantic_search(query, 1, extended_page_size, filters)

            # 融合结果
            # 使用倒数排名融合 (Reciprocal Rank Fusion)
            k = settings.SEARCH_RRF_CONSTANT
            score_map = {}  # talent_id -> combined_score
            item_map = {}   # talent_id -> item data

            # 全文搜索结果（精准匹配，给高分）
            for rank, item in enumerate(fulltext_result["items"], 1):
                tid = item["talent_id"]
                score_map[tid] = score_map.get(tid, 0) + 1.0 / (k + rank)
                # 全文搜索匹配的给高分相似度
                item["similarity_score"] = settings.SEARCH_PRECISE_THRESHOLD
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

            # 计算精准匹配和相似匹配数量（基于全部合并结果）
            precise_count = sum(1 for tid in sorted_ids if item_map[tid].get("similarity_score", 0) >= settings.SEARCH_PRECISE_THRESHOLD)
            similar_count = sum(1 for tid in sorted_ids if settings.SEARCH_SIMILAR_THRESHOLD_MIN <= item_map[tid].get("similarity_score", 0) < settings.SEARCH_PRECISE_THRESHOLD)

            # 分页
            offset = (page - 1) * page_size
            paginated_ids = sorted_ids[offset:offset + page_size]

            # 构建最终结果
            items = [item_map[tid] for tid in paginated_ids if tid in item_map]

            logger.info(f"Hybrid search: fulltext={len(fulltext_result['items'])}, semantic={len(semantic_result['items'])}, merged={len(sorted_ids)}, returned={len(items)}, precise={precise_count}, similar={similar_count}")

            return {
                "total": len(sorted_ids),
                "items": items,
                "precise_count": precise_count,
                "similar_count": similar_count,
            }

        except LLMError as e:
            # LLM 错误：降级到全文搜索
            logger.warning(f"Hybrid search LLM error: {e}, falling back to fulltext")
            await self.session.rollback()
            return await self._fulltext_search(query, page, page_size, filters)
        except ValueError as e:
            # 向量格式错误：降级到全文搜索
            logger.warning(f"Hybrid search vector error: {e}, falling back to fulltext")
            await self.session.rollback()
            return await self._fulltext_search(query, page, page_size, filters)
        except Exception as e:
            # 其他未知错误：降级到关键词搜索
            logger.error(f"Hybrid search unexpected error: {e}, falling back to keyword search")
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
            "topic_tags": talent.topic_tags or [],
            "openalex_topics": talent.openalex_topics or [],
            "works_count": talent.works_count,
            "cited_by_count": talent.cited_by_count,
            "h_index": talent.h_index,
            "orcid": talent.orcid,
        }
