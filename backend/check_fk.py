import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def check():
    engine = create_async_engine('postgresql+asyncpg://talent_user:ai4recruit@localhost:5432/talent_db')
    async with engine.begin() as conn:
        result = await conn.execute(text("""
            SELECT
                tc.table_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name LIKE 'os_%'
        """))
        for row in result:
            print(f"{row[0]}.{row[1]} -> {row[2]}.{row[3]}")
    await engine.dispose()

asyncio.run(check())
