import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def check():
    engine = create_async_engine("postgresql+asyncpg://talent_user:ai4recruit@localhost:5432/talent_db")
    async with engine.connect() as conn:
        result = await conn.execute(text(
            "SELECT column_name, is_nullable, column_default FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = 'os_developer' AND column_name IN "
            "('total_commits', 'total_prs', 'total_issues', 'extra_data', 'visibility_status')"
        ))
        for row in result:
            print(f"  {row[0]}: nullable={row[1]}, default={row[2]}")
    await engine.dispose()

asyncio.run(check())
