import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def check():
    engine = create_async_engine("postgresql+asyncpg://talent_user:ai4recruit@localhost:5432/talent_db")
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT version_num FROM alembic_version"))
        for row in result:
            print(f"Current alembic version: {row[0]}")
    await engine.dispose()

asyncio.run(check())
