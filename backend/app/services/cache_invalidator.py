"""
Cache invalidation manager.

Handles cache invalidation when data changes in the system.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.services.cache_keys import CacheKeys

if TYPE_CHECKING:
    from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)


class CacheInvalidator:
    """
    Centralized cache invalidation manager.

    Call appropriate methods when data changes to keep cache consistent.
    """

    def __init__(self, cache: CacheService) -> None:
        """Initialize with cache service."""
        self._cache = cache

    async def on_collection_complete(
        self,
        task_id: int,
        tech_element_id: int | None = None,
    ) -> None:
        """
        Invalidate caches after a collection task completes.

        Args:
            task_id: Collection task ID.
            tech_element_id: Tech element ID if collection was for a specific element.
        """
        logger.info(
            f"Invalidating caches after collection task {task_id} "
            f"(tech_element={tech_element_id})"
        )

        # Invalidate homepage statistics
        await self._cache.delete(CacheKeys.STATS_HOME_HIGHLIGHTS)

        # Invalidate overall statistics
        await self._cache.delete(CacheKeys.STATS_OVERALL)

        # Invalidate specific tech element stats
        if tech_element_id:
            key = CacheKeys.STATS_TECH_ELEMENT.format(element_id=tech_element_id)
            await self._cache.delete(key)

            # Invalidate distribution data for this element
            await self._cache.delete(
                CacheKeys.STATS_COUNTRY_DISTRIBUTION.format(element_id=tech_element_id)
            )
            await self._cache.delete(
                CacheKeys.STATS_SCHOOL_DISTRIBUTION.format(element_id=tech_element_id)
            )

        # Invalidate tech element list
        await self._cache.delete(CacheKeys.TECH_ELEMENT_LIST)

    async def on_talent_updated(self, talent_id: int) -> None:
        """
        Invalidate caches when a talent is updated.

        Args:
            talent_id: Talent ID.
        """
        logger.debug(f"Invalidating caches for talent {talent_id}")

        # Invalidate talent detail
        key = CacheKeys.TALENT_DETAIL.format(talent_id=talent_id)
        await self._cache.delete(key)

        # Statistics may have changed
        await self._cache.delete(CacheKeys.STATS_HOME_HIGHLIGHTS)
        await self._cache.delete(CacheKeys.STATS_OVERALL)

    async def on_school_updated(self, school_id: int) -> None:
        """
        Invalidate caches when a school is updated.

        Args:
            school_id: School ID.
        """
        logger.debug(f"Invalidating caches for school {school_id}")

        # Invalidate school detail
        key = CacheKeys.SCHOOL_DETAIL.format(school_id=school_id)
        await self._cache.delete(key)

        # Distribution data may have changed
        await self._cache.delete_pattern("stats:schools:*")

    async def on_tech_element_updated(self, element_id: int) -> None:
        """
        Invalidate caches when a tech element is updated.

        Args:
            element_id: Tech element ID.
        """
        logger.debug(f"Invalidating caches for tech element {element_id}")

        # Invalidate tech element detail
        key = CacheKeys.TECH_ELEMENT_DETAIL.format(element_id=element_id)
        await self._cache.delete(key)

        # Invalidate stats for this element
        stats_key = CacheKeys.STATS_TECH_ELEMENT.format(element_id=element_id)
        await self._cache.delete(stats_key)

        # Invalidate list cache
        await self._cache.delete(CacheKeys.TECH_ELEMENT_LIST)

    async def invalidate_all_stats(self) -> int:
        """
        Invalidate all statistics caches.

        Returns:
            Number of keys deleted.
        """
        logger.info("Invalidating all statistics caches")

        deleted = 0
        deleted += await self._cache.delete_pattern("stats:*")
        deleted += await self._cache.delete(CacheKeys.STATS_HOME_HIGHLIGHTS)
        deleted += await self._cache.delete(CacheKeys.STATS_OVERALL)

        return deleted

    async def invalidate_all(self) -> int:
        """
        Invalidate all caches.

        Returns:
            Number of keys deleted.
        """
        logger.warning("Invalidating ALL caches")
        return await self._cache.delete_pattern("*")
