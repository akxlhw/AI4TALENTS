"""
Redis cache connection management.
"""

from __future__ import annotations

import logging
from typing import Any

from redis.asyncio import ConnectionPool, Redis
from redis.exceptions import RedisError

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global connection pool and client
_pool: ConnectionPool | None = None
_client: Redis | None = None


class CacheConnection:
    """Redis connection manager with connection pool."""

    def __init__(self) -> None:
        self._pool: ConnectionPool | None = None
        self._client: Redis | None = None

    async def connect(self) -> bool:
        """
        Initialize Redis connection pool.

        Returns:
            True if connection established, False otherwise.
        """
        if not settings.REDIS_ENABLED:
            logger.info("Redis cache is disabled via configuration")
            return False

        try:
            pool_kwargs: dict[str, Any] = {
                "url": settings.REDIS_URL,
                "max_connections": settings.REDIS_MAX_CONNECTIONS,
                "decode_responses": True,  # Return strings instead of bytes
            }

            if settings.REDIS_PASSWORD:
                pool_kwargs["password"] = settings.REDIS_PASSWORD

            self._pool = ConnectionPool(**pool_kwargs)
            self._client = Redis(connection_pool=self._pool)

            # Test connection
            await self._client.ping()
            logger.info(
                f"Redis cache connected: {settings.REDIS_URL} "
                f"(max_connections={settings.REDIS_MAX_CONNECTIONS})"
            )
            return True

        except RedisError as e:
            logger.warning(f"Failed to connect to Redis: {e}. Cache will be disabled.")
            self._pool = None
            self._client = None
            return False

    async def disconnect(self) -> None:
        """Close Redis connection pool."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("Redis client closed")

        if self._pool:
            await self._pool.aclose()
            self._pool = None
            logger.info("Redis connection pool closed")

    @property
    def is_available(self) -> bool:
        """Check if Redis connection is available."""
        return self._client is not None and settings.REDIS_ENABLED

    @property
    def client(self) -> Redis | None:
        """Get Redis client instance."""
        return self._client


# Global singleton instance
_cache_connection: CacheConnection | None = None


async def get_cache_connection() -> CacheConnection:
    """
    Get or create the global cache connection.

    Returns:
        CacheConnection instance.
    """
    global _cache_connection

    if _cache_connection is None:
        _cache_connection = CacheConnection()
        await _cache_connection.connect()

    return _cache_connection


async def close_cache_connection() -> None:
    """Close the global cache connection."""
    global _cache_connection

    if _cache_connection:
        await _cache_connection.disconnect()
        _cache_connection = None
