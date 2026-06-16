"""
Configuration service for system configuration management.

Provides caching with TTL to avoid frequent database queries.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.shared.models.system_config import SystemConfig

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """LLM configuration settings.

    API Format determines the request/response format:
    - openai: OpenAI-compatible format (DeepSeek, Qwen, Zhipu, vLLM, Ollama, LocalAI)
    - minimax: MiniMax-specific format
    """

    enabled: bool = False  # 对话模型启用开关
    embedding_enabled: bool = False  # 嵌入模型启用开关
    api_format: str = "openai"  # API 格式: openai / minimax
    api_key: str = ""
    api_base: str = ""
    model: str = ""
    embedding_model: str = ""
    embedding_api_base: str = ""  # 单独的嵌入 API 地址（可选）
    embedding_api_key: str = ""  # 单独的嵌入 API Key（可选）
    embedding_api_format: str = ""  # 嵌入 API 格式，留空则使用 api_format
    embedding_dimension: int = 1024  # 嵌入向量维度 (128-4096)
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


@dataclass
class GitHubConfig:
    """GitHub API configuration settings."""

    tokens: str = ""  # 逗号分隔的多个 GitHub Personal Access Token
    base_url: str = "https://api.github.com"
    rate_limit: int = 5000  # 每小时每 Token 请求上限


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
    SENSITIVE_KEYS = {"LLM_API_KEY", "PROXY_PASSWORD", "LLM_EMBEDDING_API_KEY", "GITHUB_TOKENS"}

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
    def _get_cached(cls, key: str) -> Any | None:
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

    async def get_value(self, key: str, default: Any = None, use_cache: bool = True) -> Any:
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

    async def set_value(self, key: str, value: Any, config_type: str = "string") -> SystemConfig:
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

    async def get_all(self, mask_sensitive: bool = True) -> list[dict[str, Any]]:
        """
        Get all configuration values.

        Args:
            mask_sensitive: Whether to mask sensitive values

        Returns:
            List of configuration dictionaries
        """
        result = await self.session.execute(select(SystemConfig).order_by(SystemConfig.config_key))
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
        embedding_enabled = await self.get_value("LLM_EMBEDDING_ENABLED", False, use_cache)
        api_format = await self.get_value("LLM_API_FORMAT", "openai", use_cache)
        api_key = await self.get_value("LLM_API_KEY", "", use_cache)
        api_base = await self.get_value("LLM_API_BASE", "", use_cache)
        model = await self.get_value("LLM_MODEL", "", use_cache)
        embedding_model = await self.get_value("LLM_EMBEDDING_MODEL", "", use_cache)
        embedding_api_base = await self.get_value("LLM_EMBEDDING_API_BASE", "", use_cache)
        embedding_api_key = await self.get_value("LLM_EMBEDDING_API_KEY", "", use_cache)
        embedding_api_format = await self.get_value("LLM_EMBEDDING_API_FORMAT", "", use_cache)
        embedding_dimension = await self.get_value("LLM_EMBEDDING_DIMENSION", 1024, use_cache)
        timeout = await self.get_value("LLM_TIMEOUT", 60, use_cache)

        config = LLMConfig(
            enabled=bool(enabled),
            embedding_enabled=bool(embedding_enabled),
            api_format=str(api_format),
            api_key=str(api_key),
            api_base=str(api_base),
            model=str(model),
            embedding_model=str(embedding_model),
            embedding_api_base=str(embedding_api_base),
            embedding_api_key=str(embedding_api_key),
            embedding_api_format=str(embedding_api_format),
            embedding_dimension=int(embedding_dimension),
            timeout=int(timeout),
        )

        # Log key config info (mask sensitive values)
        logger.debug(
            f"[LLM Config] Loaded: chat_enabled={config.enabled}, embedding_enabled={config.embedding_enabled}, "
            f"api_format={config.api_format}, model={config.model}, "
            f"api_base={config.api_base}, embedding_model={config.embedding_model}, "
            f"embedding_api_format={config.embedding_api_format or config.api_format}, "
            f"embedding_dimension={config.embedding_dimension}"
        )

        return config

    async def update_llm_config(self, config: dict[str, Any]) -> None:
        """
        Update LLM configuration.

        Args:
            config: Dictionary of LLM configuration values
        """
        key_mapping = {
            "enabled": "LLM_ENABLED",
            "embedding_enabled": "LLM_EMBEDDING_ENABLED",
            "api_format": "LLM_API_FORMAT",
            "api_key": "LLM_API_KEY",
            "api_base": "LLM_API_BASE",
            "model": "LLM_MODEL",
            "embedding_model": "LLM_EMBEDDING_MODEL",
            "embedding_api_base": "LLM_EMBEDDING_API_BASE",
            "embedding_api_key": "LLM_EMBEDDING_API_KEY",
            "embedding_api_format": "LLM_EMBEDDING_API_FORMAT",
            "embedding_dimension": "LLM_EMBEDDING_DIMENSION",
            "timeout": "LLM_TIMEOUT",
        }

        # Log non-sensitive config updates
        safe_fields = {
            "enabled",
            "embedding_enabled",
            "api_format",
            "api_base",
            "model",
            "embedding_model",
            "embedding_api_base",
            "embedding_api_format",
            "embedding_dimension",
            "timeout",
        }
        logged_updates = {k: v for k, v in config.items() if k in safe_fields}
        logger.debug(f"[LLM Config] Updating: {logged_updates}")

        for field, key in key_mapping.items():
            if field in config:
                value = config[field]
                config_type = "string"
                if field in ("enabled", "embedding_enabled"):
                    config_type = "bool"
                elif field in ("timeout", "embedding_dimension"):
                    config_type = "int"

                await self.set_value(key, value, config_type)

        await self.session.commit()
        logger.info("[LLM Config] Configuration saved to database")

    async def update_llm_config_with_dimension_change(
        self, config: dict[str, Any], new_dimension: int
    ) -> dict[str, Any]:
        """
        Update LLM configuration with vector dimension change.

        This handles the special case where embedding dimension changes,
        requiring database DDL to modify the vector column.
        Affects both academic (core_talent_embedding) and open-source
        (os_embedding) tables.

        Args:
            config: Dictionary of LLM configuration values
            new_dimension: New embedding dimension

        Returns:
            Result dict with message and optional warning
        """
        from sqlalchemy import text

        # Update config values first
        await self.update_llm_config(config)

        # Execute DDL for academic embedding table
        await self.session.execute(text("DROP INDEX IF EXISTS ix_talent_embedding_vector"))
        await self.session.execute(text("DELETE FROM core_talent_embedding"))
        await self.session.execute(
            text(
                f"ALTER TABLE core_talent_embedding ALTER COLUMN embedding TYPE vector({new_dimension})"
            )
        )
        await self.session.execute(
            text(
                """
            CREATE INDEX ix_talent_embedding_vector
            ON core_talent_embedding
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
        """
            )
        )

        # Execute DDL for open-source embedding table
        await self.session.execute(text("DROP INDEX IF EXISTS ix_os_embedding_vector"))
        await self.session.execute(text("DELETE FROM os_embedding"))
        await self.session.execute(
            text(f"ALTER TABLE os_embedding ALTER COLUMN embedding TYPE vector({new_dimension})")
        )
        await self.session.execute(
            text(
                """
            CREATE INDEX ix_os_embedding_vector
            ON os_embedding
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
        """
            )
        )
        await self.session.commit()

        logger.info(
            f"[LLM Config] Vector columns modified to vector({new_dimension}) for both "
            "core_talent_embedding and os_embedding; existing embeddings cleared"
        )

        return {"message": "LLM configuration updated successfully"}

    async def get_embedding_config_for_domain(self, domain: str) -> dict[str, Any]:
        """
        Get embedding configuration for a specific domain.

        Currently returns the unified LLM embedding config for all domains.
        This is a convenience wrapper around get_llm_config for domain-aware
        services.

        Args:
            domain: Domain identifier, e.g. "academic" or "open_source"

        Returns:
            dict: Embedding configuration for the domain
        """
        llm_config = await self.get_llm_config()
        return {
            "domain": domain,
            "dimension": llm_config.embedding_dimension,
            "model": llm_config.embedding_model,
            "api_base": llm_config.embedding_api_base,
            "api_key": llm_config.embedding_api_key,
            "api_format": llm_config.embedding_api_format or llm_config.api_format,
            "enabled": llm_config.embedding_enabled,
        }

    async def set_and_commit(
        self, key: str, value: Any, config_type: str = "string"
    ) -> SystemConfig:
        """
        Set configuration value and commit immediately.

        Args:
            key: Configuration key
            value: Configuration value
            config_type: Value type (string, int, float, bool, json)

        Returns:
            Updated or created SystemConfig
        """
        config = await self.set_value(key, value, config_type)
        await self.session.commit()
        return config

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

    async def refresh_http_client_factory(self) -> None:
        """Reload proxy config and refresh HttpClientFactory.

        Must be called after updating proxy config so that new settings
        take effect immediately for subsequent HTTP requests.
        """
        from app.domains.shared.services.common.http_client import HttpClientFactory

        proxy_config = await self.get_proxy_config(use_cache=False)
        if proxy_config.enabled and proxy_config.url:
            HttpClientFactory.configure(
                proxy_url=proxy_config.url,
                proxy_username=proxy_config.username or None,
                proxy_password=proxy_config.password or None,
                no_proxy=proxy_config.no_proxy or None,
                ssl_verify=proxy_config.ssl_verify,
            )
            logger.info(
                f"HttpClientFactory refreshed with proxy: {proxy_config.url}, no_proxy: {proxy_config.no_proxy}"
            )
        else:
            HttpClientFactory.configure()  # Reset to no proxy
            logger.info("HttpClientFactory reset to direct connection")

    def _coerce_value(self, value: str | None, config_type: str) -> Any:
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

    async def get_github_config(self, use_cache: bool = True) -> GitHubConfig:
        """
        Get GitHub API configuration.

        Args:
            use_cache: Whether to use cache

        Returns:
            GitHubConfig object
        """
        tokens = await self.get_value("GITHUB_TOKENS", "", use_cache)
        base_url = await self.get_value("GITHUB_BASE_URL", "https://api.github.com", use_cache)
        rate_limit = await self.get_value("GITHUB_RATE_LIMIT", 5000, use_cache)

        return GitHubConfig(
            tokens=str(tokens),
            base_url=str(base_url),
            rate_limit=int(rate_limit),
        )

    async def update_github_config(self, config: dict[str, Any]) -> None:
        """
        Update GitHub API configuration.

        Args:
            config: Dictionary of GitHub configuration values
        """
        key_mapping = {
            "tokens": "GITHUB_TOKENS",
            "base_url": "GITHUB_BASE_URL",
            "rate_limit": "GITHUB_RATE_LIMIT",
        }

        for field, key in key_mapping.items():
            if field in config:
                value = config[field]
                config_type = "string"
                if field == "rate_limit":
                    config_type = "int"

                await self.set_value(key, value, config_type)

        await self.session.commit()
        logger.info("[GitHub Config] Configuration saved to database")

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
