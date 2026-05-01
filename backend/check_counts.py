import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

TABLES = [
    "os_repo_config", "os_developer", "os_repository", "os_contribution",
    "os_language_skill", "os_embedding", "os_favourite", "os_talent_pool",
    "os_pool_member", "os_collect_task", "os_raw_developer", "os_repo_mapping"
]

async def check():
    engine = create_async_engine("postgresql+asyncpg://talent_user:ai4recruit@localhost:5432/talent_db")
    async with engine.connect() as conn:
        for t in TABLES:
            result = await conn.execute(text(f"SELECT COUNT(*) FROM {t}"))
            count = result.scalar()
            print(f"  {t}: {count}")
    await engine.dispose()

asyncio.run(check())
