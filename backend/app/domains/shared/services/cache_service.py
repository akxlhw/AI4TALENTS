"""
Cache service for Redis operations.
"""

from __future__ import annotations

import json
import logging
import random
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from pydantic import BaseModel
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.cache import CacheConnection
from app.domains.shared.services.cache_keys import CacheTTL

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CacheService:
    """
    High-level cache service with Redis backend.

    Features:
    - JSON serialization for complex types
    - TTL jitter to prevent cache stampede
    - Graceful fallback when Redis is unavailable
    - Distributed lock support
    """

    def __init__(self, cache_conn: CacheConnection) -> None:
        """Initialize with cache connection."""
        self._conn = cache_conn

    @property
    def _client(self) -> Redis | None:
        """Get Redis client if available."""
        return self._conn.client

    def _build_key(self, key: str) -> str:
        """Build full cache key with prefix."""
        from app.core.config import settings

        return f"{settings.CACHE_KEY_PREFIX}:{key}"

    def _serialize(self, value: Any) -> str:
        """Serialize value to JSON string."""
        if isinstance(value, BaseModel):
            return value.model_dump_json()
        return json.dumps(value, ensure_ascii=False, default=str)

    def _deserialize(self, value: str | None) -> Any | None:
        """Deserialize JSON string to Python object."""
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    def _get_ttl_with_jitter(self, base_ttl: int, jitter_percent: float = 0.1) -> int:
        """
        Add random jitter to TTL to prevent cache stampede.

        Args:
            base_ttl: Base TTL in seconds.
            jitter_percent: Jitter percentage (default 10%).

        Returns:
            TTL with random jitter applied.
        """
        jitter = int(base_ttl * jitter_percent * random.random())
        return base_ttl + jitter

    async def get(self, key: str) -> Any | None:
        """
        Get a value from cache.

        Args:
            key: Cache key (without prefix).

        Returns:
            Cached value or None if not found.
        """
        if not self._client:
            return None

        try:
            full_key = self._build_key(key)
            value = await self._client.get(full_key)
            return self._deserialize(value)
        except RedisError as e:
            logger.warning(f"Cache get failed for key '{key}': {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
        use_jitter: bool = True,
    ) -> bool:
        """
        Set a value in cache.

        Args:
            key: Cache key (without prefix).
            value: Value to cache (will be JSON serialized).
            ttl: TTL in seconds (default from settings).
            use_jitter: Whether to add random jitter to TTL.

        Returns:
            True if set successfully, False otherwise.
        """
        if not self._client:
            return False

        try:
            from app.core.config import settings

            full_key = self._build_key(key)
            serialized = self._serialize(value)

            if ttl is None:
                ttl = settings.CACHE_DEFAULT_TTL

            if use_jitter:
                ttl = self._get_ttl_with_jitter(ttl)

            await self._client.setex(full_key, ttl, serialized)
            return True
        except RedisError as e:
            logger.warning(f"Cache set failed for key '{key}': {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete a key from cache.

        Args:
            key: Cache key (without prefix).

        Returns:
            True if deleted, False otherwise.
        """
        if not self._client:
            return False

        try:
            full_key = self._build_key(key)
            await self._client.delete(full_key)
            return True
        except RedisError as e:
            logger.warning(f"Cache delete failed for key '{key}': {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.

        Args:
            pattern: Key pattern to match (without prefix).

        Returns:
            Number of keys deleted.
        """
        if not self._client:
            return 0

        try:
            full_pattern = self._build_key(pattern)
            keys = []

            # Use SCAN for better performance on large datasets
            async for key in self._client.scan_iter(match=full_pattern):
                keys.append(key)

            if keys:
                deleted: int = await self._client.delete(*keys)
                logger.debug(f"Deleted {deleted} keys matching pattern '{pattern}'")
                return deleted

            return 0
        except RedisError as e:
            logger.warning(f"Cache delete_pattern failed for pattern '{pattern}': {e}")
            return 0

    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Awaitable[T]] | None = None,
        ttl: int = CacheTTL.MEDIUM,
        cache_empty: bool = True,
    ) -> T | None:
        """
        Get from cache or compute and cache the result.

        Args:
            key: Cache key.
            factory: Async function to compute value if not cached.
            ttl: TTL for cached value.
            cache_empty: Whether to cache None/empty results.

        Returns:
            Cached or computed value.
        """
        # Try to get from cache first
        cached = await self.get(key)
        if cached is not None:
            logger.debug(f"Cache hit for key '{key}'")
            return cached  # type: ignore[no-any-return]

        # Compute value if factory provided
        if factory is None:
            return None

        logger.debug(f"Cache miss for key '{key}', computing...")
        value = await factory()

        # Cache the result
        if value is not None or cache_empty:
            # Use shorter TTL for empty results
            actual_ttl = CacheTTL.SHORT if value is None else ttl
            await self.set(key, value, actual_ttl)

        return value

    async def acquire_lock(
        self,
        key: str,
        ttl: int = 10,
        token: str | None = None,
    ) -> bool:
        """
        Acquire a distributed lock.

        Args:
            key: Lock key.
            ttl: Lock TTL in seconds.
            token: Unique token for lock ownership.

        Returns:
            True if lock acquired, False otherwise.
        """
        if not self._client:
            return False

        try:
            import uuid

            lock_key = self._build_key(f"lock:{key}")
            lock_token = token or str(uuid.uuid4())

            # SET NX EX is atomic
            result = await self._client.set(lock_key, lock_token, nx=True, ex=ttl)
            return result is not None
        except RedisError as e:
            logger.warning(f"Failed to acquire lock '{key}': {e}")
            return False

    async def release_lock(self, key: str, token: str | None = None) -> bool:
        """
        Release a distributed lock.

        Args:
            key: Lock key.
            token: Token used when acquiring lock.

        Returns:
            True if lock released, False otherwise.
        """
        if not self._client:
            return False

        try:
            lock_key = self._build_key(f"lock:{key}")

            if token:
                # Verify ownership before releasing
                current = await self._client.get(lock_key)
                if current != token:
                    return False

            await self._client.delete(lock_key)
            return True
        except RedisError as e:
            logger.warning(f"Failed to release lock '{key}': {e}")
            return False

    async def incr(self, key: str) -> int | None:
        """
        Increment a counter.

        Args:
            key: Counter key.

        Returns:
            New value after increment, or None on error.
        """
        if not self._client:
            return None

        try:
            full_key = self._build_key(key)
            result: int = await self._client.incr(full_key)
            return result
        except RedisError as e:
            logger.warning(f"Failed to increment '{key}': {e}")
            return None

    async def expire(self, key: str, ttl: int) -> bool:
        """
        Set TTL on an existing key.

        Args:
            key: Cache key.
            ttl: New TTL in seconds.

        Returns:
            True if TTL set, False otherwise.
        """
        if not self._client:
            return False

        try:
            full_key = self._build_key(key)
            result: bool = await self._client.expire(full_key, ttl)
            return result
        except RedisError as e:
            logger.warning(f"Failed to set TTL on '{key}': {e}")
            return False
