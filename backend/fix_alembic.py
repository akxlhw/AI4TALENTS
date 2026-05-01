import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def fix():
    engine = create_async_engine("postgresql+asyncpg://talent_user:ai4recruit@localhost:5432/talent_db")
    async with engine.begin() as conn:
        await conn.execute(text("UPDATE alembic_version SET version_num = '046'"))
        result = await conn.execute(text("SELECT version_num FROM alembic_version"))
        print(f"Updated alembic version to: {result.scalar()}")
    await engine.dispose()

asyncio.run(fix())
