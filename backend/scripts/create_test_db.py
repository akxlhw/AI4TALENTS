#!/usr/bin/env python
"""
Create test database for pytest.

Usage:
    cd backend && python scripts/create_test_db.py

Note: You need to run this as a PostgreSQL superuser.
If talent_user doesn't have CREATEDB privilege, run:

    psql -U postgres -c "ALTER USER talent_user CREATEDB;"

Or create the database manually:

    psql -U postgres -c "CREATE DATABASE talent_db_test OWNER talent_user;"
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    from sqlalchemy import create_engine, text
    from app.core.config import settings

    # Parse DATABASE_URL to get connection info
    # Format: postgresql+asyncpg://user:password@host:port/database
    db_url = settings.DATABASE_SYNC_URL
    print(f"Connecting to: {db_url.split('@')[1] if '@' in db_url else db_url}")

    engine = create_engine(db_url)

    with engine.connect() as conn:
        conn.execute(text('COMMIT'))

        # Check if test database exists
        result = conn.execute(text(
            "SELECT 1 FROM pg_database WHERE datname = 'talent_db_test'"
        ))
        exists = result.scalar() == 1

        if exists:
            print("Test database 'talent_db_test' already exists.")
            return 0

        # Try to create test database
        try:
            conn.execute(text('CREATE DATABASE talent_db_test'))
            conn.commit()
            print("Test database 'talent_db_test' created successfully.")
            return 0
        except Exception as e:
            error_msg = str(e)
            if 'permission' in error_msg.lower() or '权限' in error_msg:
                print("\n" + "=" * 60)
                print("ERROR: talent_user lacks CREATEDB privilege.")
                print("=" * 60)
                print("\nPlease run one of the following commands as a superuser:")
                print("\n  Option 1: Grant CREATEDB privilege to talent_user")
                print("    psql -U postgres -c \"ALTER USER talent_user CREATEDB;\"")
                print("\n  Option 2: Create test database manually")
                print("    psql -U postgres -c \"CREATE DATABASE talent_db_test OWNER talent_user;\"")
                print("\n  Option 3: If using Docker")
                print("    docker exec -it talent-postgres psql -U postgres -c \"CREATE DATABASE talent_db_test OWNER talent_user;\"")
                print("=" * 60)
                return 1
            else:
                print(f"Error: {e}")
                return 1


if __name__ == "__main__":
    sys.exit(main())
