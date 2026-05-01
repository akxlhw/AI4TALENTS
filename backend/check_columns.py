import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def check():
    engine = create_async_engine("postgresql+asyncpg://talent_user:ai4recruit@localhost:5432/talent_db")
    async with engine.connect() as conn:
        result = await conn.execute(text(
            "SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'os_developer' ORDER BY ordinal_position"
        ))
        print("os_developer columns:")
        for row in result:
            print(f"  {row[0]}: {row[1]}")
    await engine.dispose()

asyncio.run(check())
