"""
Alembic environment configuration.

Uses SQLAlchemy async engine + run_sync pattern to avoid psycopg2
encoding issues on Windows. Compatible with all platforms.

Schema-drift policy (audited 2026-08-16):
- `search_talent_document.search_vector` is a tsvector column created by
  migration 025 outside the ORM (full-text search). The model deliberately
  does not declare it, so autogenerate would try to DROP it — filtered out
  here; it is managed by migrations only.
"""

import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.core.database import Base

# Import all models here so Alembic can detect them
from app.model_registry import *  # noqa: F401, F403

# this is the Alembic Config object, which
# provides access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# Columns managed by migrations only (not declared in ORM models) — never
# let autogenerate drop them.
_MIGRATION_MANAGED_COLUMNS = {
    ("search_talent_document", "search_vector"),
}


def _include_object(obj, name, type_, reflected, compare_to):
    """Keep migration-managed columns out of autogenerate comparisons."""
    if type_ == "column":
        table = getattr(getattr(obj, "table", None), "name", "")
        if (table, name) in _MIGRATION_MANAGED_COLUMNS:
            return False
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation we
    don't even need a DBAPI to be available.

    Calls to context.execute() here emit script output.
    """
    url = settings.DATABASE_URL.replace("+asyncpg", "")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    """Execute migrations with the given sync connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=_include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online_async() -> None:
    """Run migrations online using async engine.

    Uses asyncpg driver (via async engine) to avoid psycopg2
    encoding/decoding issues on Windows. The engine is wrapped
    via connection.run_sync() to return a sync connection
    that Alembic can work with.
    """
    connectable = create_async_engine(
        settings.DATABASE_URL,
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online_async())
