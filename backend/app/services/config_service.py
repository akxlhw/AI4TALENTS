"""
Configuration service for system configuration management.

Provides caching with TTL to avoid frequent database queries.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system_config import SystemConfig

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """LLM configuration settings."""
    enabled: bool = False
    provider: str = "deepseek"
    api_key: str = ""
    api_base: str = ""
    model: str = "deepseek-chat"
    embedding_model: str = ""
    embedding_api_base: str = ""  # 单独的嵌入 API 地址（可选）
    embedding_api_key: str = ""  # 单独的嵌入 API Key（可选）
    timeout: int = 60


@dataclass
class ProxyConfig:
    """Proxy configuration settings."""
    enabled: bool = False
    url: str = ""
    username: str = ""
    password: str = ""
    no_proxy: str = ""  # 不走代理的地址列表 (逗号分隔)
    ssl_verify: bool = True  # 是否验证 SSL 证书


class ConfigService:
    """
    Service for managing system configuration.

    Features:
    - Key-value store for configuration
    - TTL-based caching
    - Sensitive value masking
    - Type coercion
    """

    # Cache with TTL
    _cache: dict[str, tuple[Any, float]] = {}
    _cache_ttl: int = 300  # 5 minutes default TTL

    # Sensitive keys that should be masked
    SENSITIVE_KEYS = {"LLM_API_KEY", "PROXY_PASSWORD", "LLM_EMBEDDING_API_KEY"}

    @classmethod
    def mask_sensitive_value(cls, key: str, value: str) -> str:
        """Mask sensitive values for display."""
        if key in cls.SENSITIVE_KEYS and value:
            # Show only last 4 characters
            if len(value) > 8:
                return f"{value[:4]}****{value[-4:]}"
            else:
                return "****"
        return value

    @classmethod
    def clear_cache(cls) -> None:
        """Clear all cached configuration."""
        cls._cache.clear()

    @classmethod
    def _get_cached(cls, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key in cls._cache:
            value, timestamp = cls._cache[key]
            if time.time() - timestamp < cls._cache_ttl:
                return value
            else:
                del cls._cache[key]
        return None

    @classmethod
    def _set_cache(cls, key: str, value: Any) -> None:
        """Set value in cache with current timestamp."""
        cls._cache[key] = (value, time.time())

    def __init__(self, session: AsyncSession, cache_ttl: int = 300):
        self.session = session
        self._cache_ttl = cache_ttl

    async def get_value(
        self, key: str, default: Any = None, use_cache: bool = True
    ) -> Any:
        """
        Get configuration value by key.

        Args:
            key: Configuration key
            default: Default value if key not found
            use_cache: Whether to use cache

        Returns:
            Configuration value with type coercion
        """
        # Check cache first
        if use_cache:
            cached = self._get_cached(key)
            if cached is not None:
                return cached

        # Query database
        result = await self.session.execute(
            select(SystemConfig).where(SystemConfig.config_key == key)
        )
        config = result.scalar_one_or_none()

        if not config:
            return default

        # Type coercion
        value = self._coerce_value(config.config_value, config.config_type)

        # Cache the value
        if use_cache:
            self._set_cache(key, value)

        return value

    async def set_value(
        self, key: str, value: Any, config_type: str = "string"
    ) -> SystemConfig:
        """
        Set configuration value.

        Args:
            key: Configuration key
            value: Configuration value
            config_type: Value type (string, int, float, bool, json)

        Returns:
            Updated or created SystemConfig
        """
        result = await self.session.execute(
            select(SystemConfig).where(SystemConfig.config_key == key)
        )
        config = result.scalar_one_or_none()

        # Convert value to string for storage
        str_value = self._to_string(value, config_type)

        if config:
            config.config_value = str_value
            config.config_type = config_type
        else:
            config = SystemConfig(
                config_key=key,
                config_value=str_value,
                config_type=config_type,
            )
            self.session.add(config)

        # Invalidate cache
        if key in self._cache:
            del self._cache[key]

        return config

    async def get_all(
        self, mask_sensitive: bool = True
    ) -> list[dict[str, Any]]:
        """
        Get all configuration values.

        Args:
            mask_sensitive: Whether to mask sensitive values

        Returns:
            List of configuration dictionaries
        """
        result = await self.session.execute(
            select(SystemConfig).order_by(SystemConfig.config_key)
        )
        configs = result.scalars().all()

        items = []
        for config in configs:
            value = self._coerce_value(config.config_value, config.config_type)

            item = {
                "key": config.config_key,
                "value": value,
                "type": config.config_type,
                "is_sensitive": config.is_sensitive,
                "description": config.description,
            }

            # Mask sensitive values for display
            if mask_sensitive and config.is_sensitive:
                item["display_value"] = self.mask_sensitive_value(
                    config.config_key, config.config_value or ""
                )
            else:
                item["display_value"] = value

            items.append(item)

        return items

    async def get_llm_config(self, use_cache: bool = True) -> LLMConfig:
        """
        Get LLM configuration.

        Args:
            use_cache: Whether to use cache

        Returns:
            LLMConfig object
        """
        # Get all LLM config values
        enabled = await self.get_value("LLM_ENABLED", False, use_cache)
        provider = await self.get_value("LLM_PROVIDER", "deepseek", use_cache)
        api_key = await self.get_value("LLM_API_KEY", "", use_cache)
        api_base = await self.get_value("LLM_API_BASE", "", use_cache)
        model = await self.get_value("LLM_MODEL", "deepseek-chat", use_cache)
        embedding_model = await self.get_value("LLM_EMBEDDING_MODEL", "", use_cache)
        embedding_api_base = await self.get_value("LLM_EMBEDDING_API_BASE", "", use_cache)
        embedding_api_key = await self.get_value("LLM_EMBEDDING_API_KEY", "", use_cache)
        timeout = await self.get_value("LLM_TIMEOUT", 60, use_cache)

        return LLMConfig(
            enabled=bool(enabled),
            provider=str(provider),
            api_key=str(api_key),
            api_base=str(api_base),
            model=str(model),
            embedding_model=str(embedding_model),
            embedding_api_base=str(embedding_api_base),
            embedding_api_key=str(embedding_api_key),
            timeout=int(timeout),
        )

    async def update_llm_config(self, config: dict[str, Any]) -> None:
        """
        Update LLM configuration.

        Args:
            config: Dictionary of LLM configuration values
        """
        key_mapping = {
            "enabled": "LLM_ENABLED",
            "provider": "LLM_PROVIDER",
            "api_key": "LLM_API_KEY",
            "api_base": "LLM_API_BASE",
            "model": "LLM_MODEL",
            "embedding_model": "LLM_EMBEDDING_MODEL",
            "embedding_api_base": "LLM_EMBEDDING_API_BASE",
            "embedding_api_key": "LLM_EMBEDDING_API_KEY",
            "timeout": "LLM_TIMEOUT",
        }

        for field, key in key_mapping.items():
            if field in config:
                value = config[field]
                config_type = "string"
                if field == "enabled":
                    config_type = "bool"
                elif field == "timeout":
                    config_type = "int"

                await self.set_value(key, value, config_type)

        await self.session.commit()

    async def get_proxy_config(self, use_cache: bool = True) -> ProxyConfig:
        """
        Get proxy configuration.

        Args:
            use_cache: Whether to use cache

        Returns:
            ProxyConfig object
        """
        enabled = await self.get_value("PROXY_ENABLED", False, use_cache)
        url = await self.get_value("PROXY_URL", "", use_cache)
        username = await self.get_value("PROXY_USERNAME", "", use_cache)
        password = await self.get_value("PROXY_PASSWORD", "", use_cache)
        no_proxy = await self.get_value("PROXY_NO_PROXY", "", use_cache)
        ssl_verify = await self.get_value("PROXY_SSL_VERIFY", True, use_cache)

        return ProxyConfig(
            enabled=bool(enabled),
            url=str(url),
            username=str(username),
            password=str(password),
            no_proxy=str(no_proxy),
            ssl_verify=bool(ssl_verify),
        )

    async def update_proxy_config(self, config: dict[str, Any]) -> None:
        """
        Update proxy configuration.

        Args:
            config: Dictionary of proxy configuration values
        """
        key_mapping = {
            "enabled": "PROXY_ENABLED",
            "url": "PROXY_URL",
            "username": "PROXY_USERNAME",
            "password": "PROXY_PASSWORD",
            "no_proxy": "PROXY_NO_PROXY",
            "ssl_verify": "PROXY_SSL_VERIFY",
        }

        for field, key in key_mapping.items():
            if field in config:
                value = config[field]
                config_type = "string"
                if field in ("enabled", "ssl_verify"):
                    config_type = "bool"

                await self.set_value(key, value, config_type)

        await self.session.commit()

    def _coerce_value(self, value: Optional[str], config_type: str) -> Any:
        """Coerce string value to appropriate type."""
        if value is None:
            return None

        try:
            if config_type == "int":
                return int(value)
            elif config_type == "float":
                return float(value)
            elif config_type == "bool":
                return value.lower() in ("true", "1", "yes", "on")
            elif config_type == "json":
                return json.loads(value)
            else:
                return value
        except (ValueError, json.JSONDecodeError):
            return value

    def _to_string(self, value: Any, config_type: str) -> str:
        """Convert value to string for storage."""
        if value is None:
            return ""

        if config_type == "json":
            return json.dumps(value)
        elif config_type == "bool":
            return "true" if value else "false"
        else:
            return str(value)
