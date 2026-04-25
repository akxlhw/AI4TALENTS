"""
Unit tests for cache service.
"""

import os

# Disable Redis for tests by default
os.environ["REDIS_ENABLED"] = "false"

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.cache import CacheConnection
from app.services.cache_keys import CacheKeys, CacheTTL
from app.services.cache_service import CacheService


class TestCacheConnection:
    """Tests for CacheConnection class."""

    def test_initial_state(self):
        """Test initial state of cache connection."""
        conn = CacheConnection()
        assert conn._pool is None
        assert conn._client is None
        assert conn.is_available is False

    @pytest.mark.asyncio
    async def test_connect_when_disabled(self):
        """Test connect returns False when Redis is disabled."""
        conn = CacheConnection()
        result = await conn.connect()
        assert result is False
        assert conn.is_available is False

    @pytest.mark.asyncio
    async def test_disconnect_safely(self):
        """Test disconnect works even when not connected."""
        conn = CacheConnection()
        await conn.disconnect()  # Should not raise
        assert conn._pool is None
        assert conn._client is None


class TestCacheService:
    """Tests for CacheService class."""

    @pytest.fixture
    def mock_cache_connection(self):
        """Create a mock cache connection."""
        conn = MagicMock(spec=CacheConnection)
        conn.is_available = True
        return conn

    @pytest.fixture
    def cache_service(self, mock_cache_connection):
        """Create a cache service with mock connection."""
        return CacheService(mock_cache_connection)

    def test_serialize_dict(self, cache_service):
        """Test serialization of dictionary."""
        data = {"key": "value", "number": 123}
        result = cache_service._serialize(data)
        assert '"key": "value"' in result
        assert '"number": 123' in result

    def test_serialize_list(self, cache_service):
        """Test serialization of list."""
        data = [{"id": 1}, {"id": 2}]
        result = cache_service._serialize(data)
        assert result == '[{"id": 1}, {"id": 2}]'

    def test_deserialize_json(self, cache_service):
        """Test deserialization of JSON string."""
        json_str = '{"key": "value"}'
        result = cache_service._deserialize(json_str)
        assert result == {"key": "value"}

    def test_deserialize_none(self, cache_service):
        """Test deserialization of None."""
        result = cache_service._deserialize(None)
        assert result is None

    def test_deserialize_invalid_json(self, cache_service):
        """Test deserialization of invalid JSON returns original."""
        invalid = "not valid json"
        result = cache_service._deserialize(invalid)
        assert result == "not valid json"

    def test_build_key(self, cache_service):
        """Test cache key building with prefix."""
        key = cache_service._build_key("test:key")
        assert key == "ai4talents:test:key"

    def test_get_ttl_with_jitter(self, cache_service):
        """Test TTL jitter calculation."""
        base_ttl = 300
        for _ in range(10):
            ttl = cache_service._get_ttl_with_jitter(base_ttl, jitter_percent=0.1)
            # TTL should be between base and base + 10%
            assert base_ttl <= ttl <= base_ttl + int(base_ttl * 0.1)

    @pytest.mark.asyncio
    async def test_get_returns_none_when_no_client(self, cache_service, mock_cache_connection):
        """Test get returns None when Redis client is not available."""
        mock_cache_connection.client = None
        result = await cache_service.get("test:key")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_returns_false_when_no_client(self, cache_service, mock_cache_connection):
        """Test set returns False when Redis client is not available."""
        mock_cache_connection.client = None
        result = await cache_service.set("test:key", {"data": "value"})
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_returns_false_when_no_client(self, cache_service, mock_cache_connection):
        """Test delete returns False when Redis client is not available."""
        mock_cache_connection.client = None
        result = await cache_service.delete("test:key")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_or_set_without_factory(self, cache_service, mock_cache_connection):
        """Test get_or_set returns None when no factory provided and key not cached."""
        mock_cache_connection.client = None
        result = await cache_service.get_or_set("test:key")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_or_set_with_factory_no_client(self, cache_service, mock_cache_connection):
        """Test get_or_set calls factory when Redis not available."""
        mock_cache_connection.client = None

        async def factory():
            return {"computed": "data"}

        result = await cache_service.get_or_set("test:key", factory=factory)
        assert result == {"computed": "data"}


class TestCacheKeys:
    """Tests for cache key definitions."""

    def test_stats_home_highlights_key(self):
        """Test homepage highlights cache key."""
        assert CacheKeys.STATS_HOME_HIGHLIGHTS == "stats:home:highlights"

    def test_stats_tech_domain_pattern(self):
        """Test tech domain stats cache key pattern."""
        key = CacheKeys.STATS_TECH_DOMAIN.format(domain_id=1)
        assert key == "stats:tech:1"

    def test_talent_detail_pattern(self):
        """Test talent detail cache key pattern."""
        key = CacheKeys.TALENT_DETAIL.format(talent_id=123)
        assert key == "talent:123"


class TestCacheTTL:
    """Tests for cache TTL constants."""

    def test_ttl_values(self):
        """Test TTL constants have expected values."""
        assert CacheTTL.SHORT == 60
        assert CacheTTL.MEDIUM == 300
        assert CacheTTL.LONG == 600
        assert CacheTTL.VERY_LONG == 1800


class TestCacheServiceWithMockRedis:
    """Tests with mocked Redis client."""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        client = AsyncMock()
        return client

    @pytest.fixture
    def cache_with_redis(self, mock_redis):
        """Create cache service with mocked Redis."""
        conn = MagicMock(spec=CacheConnection)
        conn.client = mock_redis
        conn.is_available = True
        return CacheService(conn), mock_redis

    @pytest.mark.asyncio
    async def test_get_cached_value(self, cache_with_redis):
        """Test retrieving a cached value."""
        cache, redis = cache_with_redis
        redis.get.return_value = '{"key": "value"}'

        result = await cache.get("test:key")

        assert result == {"key": "value"}
        redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_missing_value(self, cache_with_redis):
        """Test retrieving a missing value."""
        cache, redis = cache_with_redis
        redis.get.return_value = None

        result = await cache.get("test:missing")

        assert result is None

    @pytest.mark.asyncio
    async def test_set_value(self, cache_with_redis):
        """Test setting a value."""
        cache, redis = cache_with_redis
        redis.setex.return_value = True

        result = await cache.set("test:key", {"data": "value"}, ttl=300)

        assert result is True
        redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_key(self, cache_with_redis):
        """Test deleting a key."""
        cache, redis = cache_with_redis
        redis.delete.return_value = 1

        result = await cache.delete("test:key")

        assert result is True
        redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_or_set_cached(self, cache_with_redis):
        """Test get_or_set returns cached value."""
        cache, redis = cache_with_redis
        redis.get.return_value = '{"cached": "data"}'

        factory_called = False

        async def factory():
            nonlocal factory_called
            factory_called = True
            return {"new": "data"}

        result = await cache.get_or_set("test:key", factory=factory)

        assert result == {"cached": "data"}
        assert not factory_called  # Factory should not be called

    @pytest.mark.asyncio
    async def test_get_or_set_compute(self, cache_with_redis):
        """Test get_or_set computes when not cached."""
        cache, redis = cache_with_redis
        redis.get.return_value = None
        redis.setex.return_value = True

        async def factory():
            return {"computed": "data"}

        result = await cache.get_or_set("test:key", factory=factory, ttl=300)

        assert result == {"computed": "data"}
        redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_pattern(self, cache_with_redis):
        """Test deleting keys by pattern."""
        cache, redis = cache_with_redis

        # Mock scan_iter to return some keys
        async def mock_scan(*args, **kwargs):
            for key in ["ai4talents:stats:1", "ai4talents:stats:2"]:
                yield key

        redis.scan_iter = mock_scan
        redis.delete.return_value = 2

        result = await cache.delete_pattern("stats:*")

        assert result == 2

    @pytest.mark.asyncio
    async def test_acquire_lock(self, cache_with_redis):
        """Test acquiring a distributed lock."""
        cache, redis = cache_with_redis
        redis.set.return_value = True

        result = await cache.acquire_lock("test:lock", ttl=10)

        assert result is True
        redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_acquire_lock_fails(self, cache_with_redis):
        """Test lock acquisition fails when already held."""
        cache, redis = cache_with_redis
        redis.set.return_value = None

        result = await cache.acquire_lock("test:lock", ttl=10)

        assert result is False

    @pytest.mark.asyncio
    async def test_release_lock_success(self, cache_with_redis):
        """Test releasing a lock successfully."""
        cache, redis = cache_with_redis
        redis.delete.return_value = 1

        result = await cache.release_lock("test:lock")

        assert result is True
        redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_release_lock_with_token_verification(self, cache_with_redis):
        """Test releasing a lock with token verification."""
        cache, redis = cache_with_redis
        redis.get.return_value = "my-token"
        redis.delete.return_value = 1

        result = await cache.release_lock("test:lock", token="my-token")

        assert result is True
        redis.get.assert_called_once()
        redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_release_lock_token_mismatch(self, cache_with_redis):
        """Test releasing a lock fails when token doesn't match."""
        cache, redis = cache_with_redis
        redis.get.return_value = "other-token"

        result = await cache.release_lock("test:lock", token="my-token")

        assert result is False
        redis.get.assert_called_once()
        redis.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_release_lock_no_client(self, cache_with_redis):
        """Test release_lock returns False when no Redis client."""
        cache, redis = cache_with_redis
        # Set client to None to simulate no connection
        cache._conn.client = None
        result = await cache.release_lock("test:lock")
        assert result is False

    @pytest.mark.asyncio
    async def test_incr_success(self, cache_with_redis):
        """Test incrementing a counter."""
        cache, redis = cache_with_redis
        redis.incr.return_value = 42

        result = await cache.incr("counter:key")

        assert result == 42
        redis.incr.assert_called_once()

    @pytest.mark.asyncio
    async def test_incr_no_client(self, cache_with_redis):
        """Test incr returns None when no Redis client."""
        cache, redis = cache_with_redis
        cache._conn.client = None
        result = await cache.incr("counter:key")
        assert result is None

    @pytest.mark.asyncio
    async def test_expire_success(self, cache_with_redis):
        """Test setting TTL on a key."""
        cache, redis = cache_with_redis
        redis.expire.return_value = True

        result = await cache.expire("test:key", ttl=300)

        assert result is True
        redis.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_expire_no_client(self, cache_with_redis):
        """Test expire returns False when no Redis client."""
        cache, redis = cache_with_redis
        cache._conn.client = None
        result = await cache.expire("test:key", ttl=300)
        assert result is False

    @pytest.mark.asyncio
    async def test_get_or_set_cache_empty_false(self, cache_with_redis):
        """Test get_or_set with cache_empty=False doesn't cache None."""
        cache, redis = cache_with_redis
        redis.get.return_value = None

        async def factory():
            return None

        result = await cache.get_or_set("test:key", factory=factory, cache_empty=False)

        assert result is None
        # Should not call setex since cache_empty=False and factory returned None
        redis.setex.assert_not_called()

    @pytest.mark.asyncio
    async def test_redis_error_on_get(self, cache_with_redis):
        """Test Redis error handling on get operation."""
        cache, redis = cache_with_redis
        from redis.exceptions import RedisError

        redis.get.side_effect = RedisError("Connection lost")

        result = await cache.get("test:key")

        # Should return None on error, not raise
        assert result is None

    @pytest.mark.asyncio
    async def test_redis_error_on_set(self, cache_with_redis):
        """Test Redis error handling on set operation."""
        cache, redis = cache_with_redis
        from redis.exceptions import RedisError

        redis.setex.side_effect = RedisError("Write failed")

        result = await cache.set("test:key", {"data": "value"})

        # Should return False on error, not raise
        assert result is False

    @pytest.mark.asyncio
    async def test_redis_error_on_delete(self, cache_with_redis):
        """Test Redis error handling on delete operation."""
        cache, redis = cache_with_redis
        from redis.exceptions import RedisError

        redis.delete.side_effect = RedisError("Delete failed")

        result = await cache.delete("test:key")

        # Should return False on error, not raise
        assert result is False

    @pytest.mark.asyncio
    async def test_redis_error_on_acquire_lock(self, cache_with_redis):
        """Test Redis error handling on acquire_lock operation."""
        cache, redis = cache_with_redis
        from redis.exceptions import RedisError

        redis.set.side_effect = RedisError("Lock failed")

        result = await cache.acquire_lock("test:lock")

        # Should return False on error, not raise
        assert result is False
