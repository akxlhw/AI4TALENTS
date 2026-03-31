"""
重新提取所有学者的 openalex_topics 字段。

问题背景:
- 原代码错误地使用 topic.get("score", 0) > 0.3 过滤
- OpenAlex API 返回的是 "count" 字段，没有 "score" 字段
- 导致所有 topics 都被过滤掉，openalex_topics 为空

此脚本从 raw_author 表的 raw_json 重新提取 topics。
"""
import asyncio
import json
import logging
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.raw_data import RawAuthor
from app.models.standardized import StdAuthor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_topics_from_raw_json(raw_json: str, min_count: int = 3) -> list:
    """
    Extract research topics from OpenAlex raw_json.

    OpenAlex topics format:
    {
        "topics": [
            {
                "display_name": "Domain Adaptation and Few-Shot Learning",
                "count": 78,
                "subfield": {"display_name": "Artificial Intelligence"},
                ...
            }
        ]
    }
    """
    try:
        data = json.loads(raw_json)
        topics_data = data.get("topics", [])
        topics = []
        for topic in topics_data[:10]:
            if topic.get("count", 0) >= min_count:
                display_name = topic.get("display_name")
                if display_name:
                    topics.append(display_name)
        return topics
    except (json.JSONDecodeError, TypeError):
        return []


async def refresh_all_topics():
    """重新提取所有学者的 topics"""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # 1. 获取所有 raw_author 的 raw_json
        logger.info("正在获取 raw_author 数据...")
        result = await session.execute(
            select(RawAuthor.raw_author_id, RawAuthor.openalex_author_id, RawAuthor.raw_json)
        )
        raw_authors = result.all()
        logger.info(f"共找到 {len(raw_authors)} 条 raw_author 记录")

        # 2. 构建 openalex_author_id -> topics 的映射
        topics_map = {}
        for raw_id, openalex_id, raw_json in raw_authors:
            if raw_json and openalex_id:
                topics = extract_topics_from_raw_json(raw_json)
                if topics:
                    topics_map[openalex_id] = topics

        logger.info(f"其中 {len(topics_map)} 条有 topics 数据")

        # 3. 更新 std_author 表
        updated_count = 0
        for openalex_id, topics in topics_map.items():
            await session.execute(
                update(StdAuthor)
                .where(StdAuthor.openalex_author_id == openalex_id)
                .values(openalex_topics=topics)
            )
            updated_count += 1
            if updated_count % 500 == 0:
                await session.commit()
                logger.info(f"已更新 {updated_count} 条记录...")

        await session.commit()
        logger.info(f"完成！共更新 {updated_count} 条 std_author 记录")

        # 4. 同时更新 core_talent 表
        logger.info("正在更新 core_talent 表...")
        # 通过 std_author 关联更新 core_talent
        result = await session.execute(
            select(StdAuthor.std_author_id, StdAuthor.openalex_topics)
            .where(StdAuthor.openalex_topics != None)
        )
        std_authors = result.all()

        from app.models.talent import Talent
        talent_updated = 0
        for std_id, topics in std_authors:
            if topics:
                await session.execute(
                    update(Talent)
                    .where(Talent.std_author_id == std_id)
                    .values(openalex_topics=topics)
                )
                talent_updated += 1
                if talent_updated % 500 == 0:
                    await session.commit()
                    logger.info(f"已更新 {talent_updated} 条 talent 记录...")

        await session.commit()
        logger.info(f"完成！共更新 {talent_updated} 条 core_talent 记录")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(refresh_all_topics())
