"""
Cache Manager implementation.
缓存管理器实现 - v1.4

Features:
- Multi-level caching
- JD features caching
- Embedding caching
- Configurable TTL
"""

from __future__ import annotations

import hashlib
import json
import logging
from abc import ABC, abstractmethod
from typing import Optional, Any, List

from app.services.llm.protocols import JDFeatures

logger = logging.getLogger(__name__)


class CacheBackend(ABC):
    """缓存后端抽象接口"""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        ...

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """设置缓存"""
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        """删除缓存"""
        ...


class MemoryCacheBackend(CacheBackend):
    """内存缓存后端（用于测试和简单场景）"""

    def __init__(self) -> None:
        self._cache: dict[str, Any] = {}

    async def get(self, key: str) -> Optional[Any]:
        return self._cache.get(key)

    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        self._cache[key] = value

    async def delete(self, key: str) -> None:
        self._cache.pop(key, None)


class CacheManager:
    """统一缓存管理器

    管理 JD 解析结果、嵌入向量等的缓存。
    """

    def __init__(self, backend: CacheBackend | None = None):
        """
        初始化缓存管理器

        Args:
            backend: 缓存后端（可选）
        """
        self.backend = backend

    def _cache_key(self, prefix: str, *args: Any) -> str:
        """
        生成缓存键

        Args:
            prefix: 前缀
            *args: 参数

        Returns:
            str: 缓存键
        """
        content = json.dumps(args, sort_keys=True, default=str)
        hash_key = hashlib.md5(content.encode()).hexdigest()[:16]
        return f"{prefix}:{hash_key}"

    # ========== JD Features ==========

    async def get_jd_features(self, jd_text: str) -> Optional[JDFeatures]:
        """
        获取缓存的 JD 解析结果

        Args:
            jd_text: JD 文本

        Returns:
            Optional[JDFeatures]: 缓存的结果或 None
        """
        if not self.backend:
            return None

        key = self._cache_key("jd", jd_text)
        data = await self.backend.get(key)

        if data:
            return JDFeatures.from_dict(data)
        return None

    async def set_jd_features(
        self,
        jd_text: str,
        features: JDFeatures,
        ttl: int = 86400  # 24 小时
    ) -> None:
        """
        缓存 JD 解析结果

        Args:
            jd_text: JD 文本
            features: 解析结果
            ttl: 缓存时间（秒）
        """
        if not self.backend:
            return

        key = self._cache_key("jd", jd_text)
        await self.backend.set(key, features.to_dict(), ttl)

    # ========== Embeddings ==========

    async def get_embedding(self, talent_id: int) -> Optional[List[float]]:
        """
        获取缓存的人才嵌入向量

        Args:
            talent_id: 人才 ID

        Returns:
            Optional[List[float]]: 嵌入向量或 None
        """
        if not self.backend:
            return None

        key = f"emb:{talent_id}"
        return await self.backend.get(key)

    async def set_embedding(
        self,
        talent_id: int,
        embedding: List[float],
        ttl: int = 604800  # 7 天
    ) -> None:
        """
        缓存人才嵌入向量

        Args:
            talent_id: 人才 ID
            embedding: 嵌入向量
            ttl: 缓存时间（秒）
        """
        if not self.backend:
            return

        key = f"emb:{talent_id}"
        await self.backend.set(key, embedding, ttl)

    # ========== Generic ==========

    async def get(self, key: str) -> Optional[Any]:
        """通用获取"""
        if not self.backend:
            return None
        return await self.backend.get(key)

    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """通用设置"""
        if not self.backend:
            return
        await self.backend.set(key, value, ttl)

    async def delete(self, key: str) -> None:
        """通用删除"""
        if not self.backend:
            return
        await self.backend.delete(key)
