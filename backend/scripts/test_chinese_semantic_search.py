"""
测试中文查询的语义搜索改进

验证使用英文翻译生成 embedding 是否能提高相似度匹配。
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.search.search_service import (
    get_english_translation,
    expand_query_with_synonyms,
    CHINESE_TO_ENGLISH_MAP,
    SYNONYM_MAP,
)


def test_translation_maps():
    """测试翻译映射"""
    print("=" * 60)
    print("测试翻译映射")
    print("=" * 60)

    # 测试中文查询
    chinese_queries = ["机器学习", "深度学习", "自然语言处理", "计算机视觉"]

    for query in chinese_queries:
        english = get_english_translation(query)
        expanded = expand_query_with_synonyms(query)
        print(f"查询: {query}")
        print(f"  英文翻译 (用于 embedding): {english}")
        print(f"  扩展后 (用于全文搜索): {expanded}")
        print()

    # 测试英文缩写
    english_abbrs = ["ml", "nlp", "cv", "ai"]

    for query in english_abbrs:
        english = get_english_translation(query)
        expanded = expand_query_with_synonyms(query)
        print(f"查询: {query}")
        print(f"  英文翻译 (用于 embedding): {english}")
        print(f"  扩展后 (用于全文搜索): {expanded}")
        print()


async def test_semantic_search():
    """测试语义搜索"""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from app.services.embedding.embedding_service import EmbeddingService
    from app.services.search.search_service import SearchService, SearchMode
    from app.services.config_service import ConfigService
    from app.services.llm import LLMGateway
    from app.core.config import settings

    print("=" * 60)
    print("测试语义搜索")
    print("=" * 60)

    # 创建数据库连接
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
    )

    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        # 获取 LLM 配置
        config_service = ConfigService(session)
        llm_config = await config_service.get_llm_config()

        if not llm_config.enabled or not llm_config.api_key:
            print("LLM 未启用或未配置 API Key，跳过语义搜索测试")
            return

        # 创建 LLM 网关
        llm_gateway = LLMGateway(
            api_key=llm_config.api_key,
            api_base=llm_config.api_base or "https://api.deepseek.com/v1",
            model=llm_config.model or "deepseek-chat",
            embedding_model=llm_config.embedding_model or "deepseek-embedding",
            timeout=llm_config.timeout or 60,
        )

        # 创建 embedding 服务
        embedding_service = EmbeddingService(
            session=session,
            llm_gateway=llm_gateway,
        )
        search_service = SearchService(session, embedding_service)

        # 测试查询
        queries = ["机器学习", "machine learning", "ml", "深度学习", "deep learning"]

        for query in queries:
            print(f"\n查询: {query}")
            print("-" * 40)

            try:
                result = await search_service.search(
                    query=query,
                    mode=SearchMode.SEMANTIC,
                    page=1,
                    page_size=5,
                )

                print(f"总数: {result.total}, 耗时: {result.took_ms:.0f}ms")

                for item in result.items:
                    similarity = item.get("similarity_score", 0)
                    percent = int(similarity * 100)
                    print(f"  {percent}% | {item['name']} | {item.get('school_name', 'N/A')}")

            except Exception as e:
                print(f"  错误: {e}")


async def compare_embeddings():
    """比较不同文本的 embedding 相似度"""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import text
    from app.services.embedding.embedding_service import EmbeddingService
    from app.services.config_service import ConfigService
    from app.services.llm import LLMGateway
    from app.core.config import settings

    print("=" * 60)
    print("比较 Embedding 相似度")
    print("=" * 60)

    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
    )

    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        # 获取 LLM 配置
        config_service = ConfigService(session)
        llm_config = await config_service.get_llm_config()

        if not llm_config.enabled or not llm_config.api_key:
            print("LLM 未启用或未配置 API Key，跳过 embedding 比较")
            return

        # 创建 LLM 网关
        llm_gateway = LLMGateway(
            api_key=llm_config.api_key,
            api_base=llm_config.api_base or "https://api.deepseek.com/v1",
            model=llm_config.model or "deepseek-chat",
            embedding_model=llm_config.embedding_model or "deepseek-embedding",
            timeout=llm_config.timeout or 60,
        )

        embedding_service = EmbeddingService(
            session=session,
            llm_gateway=llm_gateway,
        )

        # 获取不同文本的 embedding
        texts = [
            "machine learning",
            "机器学习",
            "机器学习 machine learning",
            "deep learning",
        ]

        embeddings = {}
        for text in texts:
            emb = await embedding_service.get_query_embedding(text)
            embeddings[text] = emb
            print(f"文本: '{text}' -> 向量维度: {len(emb)}")

        print("\n计算余弦相似度:")
        print("-" * 40)

        # 计算相似度矩阵
        for i, text1 in enumerate(texts):
            for text2 in texts[i+1:]:
                # 余弦相似度 = 1 - 余弦距离
                vec1 = embeddings[text1]
                vec2 = embeddings[text2]

                # 计算点积
                dot_product = sum(a * b for a, b in zip(vec1, vec2))
                norm1 = sum(a * a for a in vec1) ** 0.5
                norm2 = sum(b * b for b in vec2) ** 0.5

                cosine_sim = dot_product / (norm1 * norm2)

                print(f"'{text1}' vs '{text2}': {cosine_sim:.4f} ({int(cosine_sim * 100)}%)")


if __name__ == "__main__":
    print("测试中文语义搜索改进\n")

    # 测试翻译映射
    test_translation_maps()

    # 比较 embedding
    asyncio.run(compare_embeddings())

    # 测试语义搜索
    asyncio.run(test_semantic_search())
