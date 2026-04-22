"""
Cache key definitions and TTL constants.
"""
from __future__ import annotations


class CacheKeys:
    """Cache key patterns for different data types."""

    # Homepage statistics
    STATS_HOME_HIGHLIGHTS = "stats:home:highlights"

    # Tech domain statistics
    STATS_TECH_DOMAIN = "stats:tech:{domain_id}"
    STATS_OVERALL = "stats:overall"

    # Distribution data
    STATS_COUNTRY_DISTRIBUTION = "stats:countries:{domain_id}"
    STATS_SCHOOL_DISTRIBUTION = "stats:schools:{domain_id}"

    # Entity details
    TALENT_DETAIL = "talent:{talent_id}"
    SCHOOL_DETAIL = "school:{school_id}"

    # Tech domain data
    TECH_DOMAIN_LIST = "tech:domains:list"
    TECH_DOMAIN_DETAIL = "tech:domain:{domain_id}"

    @classmethod
    def build_key(cls, pattern: str, **kwargs: str | int) -> str:
        """
        Build a cache key from a pattern with parameters.

        Args:
            pattern: Key pattern with placeholders.
            **kwargs: Parameters to substitute.

        Returns:
            Fully resolved cache key with prefix.
        """
        key = pattern.format(**kwargs)
        return f"{settings.CACHE_KEY_PREFIX}:{key}"


class CacheTTL:
    """TTL constants for different cache types (in seconds)."""

    # Short TTL for frequently changing data or empty results
    SHORT = 60  # 1 minute

    # Medium TTL for statistics and aggregated data
    MEDIUM = 300  # 5 minutes

    # Long TTL for distribution data
    LONG = 600  # 10 minutes

    # Very long TTL for entity details
    VERY_LONG = 1800  # 30 minutes

    # Distribution data TTL
    DISTRIBUTION = 300  # 5 minutes


# Import settings at the end to avoid circular imports
from app.core.config import settings  # noqa: E402
