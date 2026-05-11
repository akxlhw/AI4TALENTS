"""
Verify database indexes for performance optimization.

This script checks that all required performance indexes exist in the PostgreSQL database.

Usage:
    python scripts/verify_indexes.py
"""
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy import create_engine, text

from app.core.config import settings


# Required indexes for v1.3 performance optimization
# Format: (index_name, table_name)
REQUIRED_INDEXES = [
    # P0: User-visible pages
    ('ix_core_talent_visible_school_role', 'core_talent'),
    ('ix_core_talent_visible_cited_desc', 'core_talent'),
    ('ix_talent_tech_enabled_element', 'core_talent_tech_tag'),
    ('ix_talent_tech_enabled_direction', 'core_talent_tech_tag'),
    ('ix_favorite_user_active_created', 'iam_favorite_talent'),
    # P1: Collection tasks
    ('ix_raw_work_source_year', 'raw_work'),
    ('ix_raw_author_status_task', 'raw_author'),
    ('ix_raw_inst_status_task', 'raw_institution'),
]

# Additional indexes to check (should exist but not created by this migration)
EXISTING_INDEXES = [
    ('ix_core_talent_talent_id', 'core_talent'),
    ('ix_core_talent_school_id', 'core_talent'),
    ('ix_core_school_school_id', 'core_school'),
    ('ix_core_school_country_code', 'core_school'),
]


def get_postgres_indexes(engine) -> dict:
    """Get indexes from PostgreSQL database."""
    indexes = {}
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT indexname, tablename
            FROM pg_indexes
            WHERE schemaname = 'public'
        """))
        for row in result:
            table = row[1]
            index_name = row[0]
            if table not in indexes:
                indexes[table] = set()
            indexes[table].add(index_name)
    return indexes


def verify_indexes():
    """Verify all required indexes exist."""
    print("=" * 60)
    print("Database Index Verification")
    print("=" * 60)
    db_url = settings.DATABASE_SYNC_URL
    print(f"\nDatabase URL: {db_url.split('@')[-1] if '@' in db_url else db_url}")
    print("Database type: PostgreSQL")
    print()

    # Create sync engine
    engine = create_engine(settings.DATABASE_SYNC_URL, echo=False)

    # Get indexes
    indexes = get_postgres_indexes(engine)

    # Verify required indexes
    print("-" * 60)
    print("Required Performance Indexes (v1.3)")
    print("-" * 60)

    missing = []
    for index_name, table_name in REQUIRED_INDEXES:
        table_indexes = indexes.get(table_name, set())
        exists = index_name in table_indexes
        status = "[OK] EXISTS" if exists else "[MISSING]"
        print(f"  {index_name:45} {status}")
        if not exists:
            missing.append((index_name, table_name))

    print()

    # Check existing indexes
    print("-" * 60)
    print("Existing Core Indexes")
    print("-" * 60)

    for index_name, table_name in EXISTING_INDEXES:
        table_indexes = indexes.get(table_name, set())
        exists = index_name in table_indexes
        status = "[OK]" if exists else "[X]"
        print(f"  {status} {index_name:45} ({table_name})")

    print()

    # Summary
    print("=" * 60)
    if missing:
        print(f"RESULT: {len(missing)} missing index(es)")
        print("\nTo create missing indexes, run:")
        print("  cd backend && alembic upgrade head")
        return 1
    else:
        print("RESULT: All required indexes exist [OK]")
        return 0


if __name__ == "__main__":
    sys.exit(verify_indexes())
