"""
Database connection and session management.

本项目仅支持 PostgreSQL，开发与生产环境均使用 PostgreSQL。
无 SQLite 降级方案。
"""

from collections.abc import AsyncGenerator, Generator
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

# Cached dialect check (shared across all repositories)
_is_postgres_cache: bool | None = None


def is_postgres(session: AsyncSession) -> bool:
    """Check if the database is PostgreSQL. Result is cached on first call."""
    global _is_postgres_cache

    if _is_postgres_cache is not None:
        return _is_postgres_cache

    try:
        bind = session.get_bind()
        _is_postgres_cache = bind.dialect.name == "postgresql"
        return _is_postgres_cache
    except SQLAlchemyError:
        return True


# Async engine for application
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Alias for background tasks
async_session_factory = AsyncSessionLocal

# Sync engine for Alembic migrations
sync_engine = create_engine(
    settings.DATABASE_SYNC_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
)

# Sync session factory for migrations
SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def get_sync_session() -> Generator[Any, None, None]:
    """Dependency for getting sync database session (for migrations)."""
    session = SyncSessionLocal()
    try:
        yield session
    finally:
        session.close()
