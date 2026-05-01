import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def check():
    engine = create_async_engine('postgresql+asyncpg://talent_user:ai4recruit@localhost:5432/talent_db')
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename LIKE 'tech%'"))
        for row in result:
            print(row[0])
        result2 = await conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename LIKE 'core_tech%'"))
        for row in result2:
            print(row[0])
    await engine.dispose()

asyncio.run(check())
