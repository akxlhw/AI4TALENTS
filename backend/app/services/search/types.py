"""Search type definitions (models, enums, configs)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SearchMode(str, Enum):
    """搜索模式"""

    KEYWORD = "keyword"  # 关键词搜索 (ILIKE)
    FULLTEXT = "fulltext"  # 全文搜索 (tsvector)
    SEMANTIC = "semantic"  # 语义搜索 (向量)
    HYBRID = "hybrid"  # 混合搜索


@dataclass
class SearchResult:
    """搜索结果"""

    total: int
    page: int
    page_size: int
    items: list[dict]
    search_mode: str
    took_ms: float
    precise_count: int = 0  # 精准匹配数量 (similarity >= 0.95)
    similar_count: int = 0  # 相似匹配数量 (0.7 <= similarity < 0.95)
    fulltext_count: int = 0  # 关键词匹配数量
    semantic_count: int = 0  # 语义匹配数量

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
