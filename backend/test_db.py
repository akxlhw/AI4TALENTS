import asyncio
import asyncpg

async def test():
    try:
        conn = await asyncpg.connect("postgresql://talent_user:ai4recruit@localhost:5432/talent_db")
        rows = await conn.fetch("SELECT datname FROM pg_database WHERE datname LIKE '%talent%'")
        for r in rows:
            print(f"DB: {r['datname']}")
        await conn.close()
        print("Connection OK")
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(test())
