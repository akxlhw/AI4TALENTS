"""
Database connection and session management.
"""
from collections.abc import AsyncGenerator, Generator
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

# Check if using SQLite
IS_SQLITE = "sqlite" in settings.DATABASE_URL


def _set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
    """Enable SQLite WAL mode for concurrent read/write access."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=30000")  # 30 seconds timeout
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


# Async engine for application
if IS_SQLITE:
    async_engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        connect_args={"check_same_thread": False},
    )
    # Enable WAL mode for async engine
    event.listen(async_engine.sync_engine, "connect", _set_sqlite_pragma)
else:
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
if IS_SQLITE:
    sync_engine = create_engine(
        settings.DATABASE_SYNC_URL,
        echo=settings.DEBUG,
        connect_args={"check_same_thread": False},
    )
    # Enable WAL mode for sync engine
    event.listen(sync_engine, "connect", _set_sqlite_pragma)
else:
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
