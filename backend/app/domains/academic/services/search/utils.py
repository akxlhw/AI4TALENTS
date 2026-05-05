"""Search utilities and shared helper functions."""

from __future__ import annotations

from app.domains.academic.models.search import SearchTalentDocument
from app.domains.academic.models.talent import Talent
from app.domains.academic.models.tech_domain import TalentTechTag

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
    """扩展查询词，添加同义词（用于全文搜索）。

    Args:
        query: 原始查询

    Returns:
        str: 扩展后的查询（原始查询 + 同义词）
    """
    query_lower = query.lower().strip()
    if query_lower in SYNONYM_MAP:
        return f"{query} {SYNONYM_MAP[query_lower]}"
    return query


def get_english_translation(query: str) -> str | None:
    """获取中文查询的英文翻译（用于语义搜索 embedding）。

    Args:
        query: 原始查询

    Returns:
        str | None: 英文翻译，如果没有则返回 None
    """
    query_stripped = query.strip()
    if query_stripped in CHINESE_TO_ENGLISH_MAP:
        return CHINESE_TO_ENGLISH_MAP[query_stripped]
    query_lower = query_stripped.lower()
    if query_lower in SYNONYM_MAP:
        return SYNONYM_MAP[query_lower]
    return None


def talent_to_dict(talent: Talent) -> dict:
    """将 Talent 模型转换为字典。"""
    return {
        "talent_id": talent.talent_id,
        "name": talent.name,
        "name_en": talent.name_en,
        "title": talent.current_title,
        "school_id": talent.school_id,
        "school_name": talent.primary_school_name,
        "education_school_id": talent.education_school_id,
        "education_school_name": talent.education_school.school_name if talent.education_school else None,
        "company_school_id": talent.company_school_id,
        "company_school_name": talent.company_school.school_name if talent.company_school else None,
        "role_type": talent.role_type,
        "topic_tags": talent.topic_tags or [],
        "openalex_topics": talent.openalex_topics or [],
        "works_count": talent.works_count,
        "cited_by_count": talent.cited_by_count,
        "h_index": talent.h_index,
        "orcid": talent.orcid,
    }


def apply_talent_filters(query, filters: dict | None):
    """应用过滤条件到 Talent 查询。"""
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

    if "country_code" in filters:
        query = query.where(Talent.country_code == filters["country_code"])

    if "tech_domain_id" in filters:
        query = query.join(
            TalentTechTag, Talent.talent_id == TalentTechTag.talent_id
        ).where(
            TalentTechTag.tech_domain_id == filters["tech_domain_id"],
            TalentTechTag.is_enabled.is_(True),
        )

    if "is_graduated" in filters:
        is_grad = filters["is_graduated"] == "true" or filters["is_graduated"] is True
        query = query.where(Talent.is_graduated == is_grad)

    if "confirm_status" in filters:
        query = query.join(
            TalentTechTag, Talent.talent_id == TalentTechTag.talent_id
        ).where(TalentTechTag.confirm_status == filters["confirm_status"])

    return query


def apply_search_document_filters(query, filters: dict | None):
    """Apply filters to SearchTalentDocument query."""
    if not filters:
        return query

    if "school_id" in filters:
        query = query.where(SearchTalentDocument.school_id == filters["school_id"])
    if "role_type" in filters:
        query = query.where(SearchTalentDocument.role_type == filters["role_type"])

    return query
