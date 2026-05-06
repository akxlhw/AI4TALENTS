"""
Embedding configuration provider abstraction.

Provides a unified interface for retrieving embedding configuration per domain.
Current implementation returns a shared (unified) config for all domains.
Future implementations can return domain-specific configs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.domains.shared.services.config_service import ConfigService, LLMConfig


@dataclass
class EmbeddingConfig:
    """Embedding configuration for a single domain."""

    dimension: int
    model: str
    api_base: str
    api_key: str
    api_format: str
    enabled: bool


class EmbeddingConfigProvider(Protocol):
    """Protocol for providing embedding configuration per domain."""

    async def get_config(self, domain: str) -> EmbeddingConfig:
        """
        Get embedding configuration for the specified domain.

        Args:
            domain: Domain identifier, e.g. "academic" or "open_source"

        Returns:
            EmbeddingConfig: The embedding configuration for that domain
        """
        ...


class UnifiedEmbeddingConfigProvider:
    """
    Shared embedding config provider.

    All domains share the same LLM embedding configuration.
    This is the current production implementation.
    """

    def __init__(self, config_service: ConfigService):
        self.config_service = config_service

    async def get_config(self, domain: str) -> EmbeddingConfig:
        """
        Get the unified embedding configuration.

        The ``domain`` parameter is accepted for forward compatibility
        with per-domain providers but is not used in this implementation.
        """
        llm_config = await self.config_service.get_llm_config()
        return _llm_config_to_embedding_config(llm_config)


class PerDomainEmbeddingConfigProvider:
    """
    Per-domain embedding config provider (future extension).

    Reads domain-specific config keys from the database:
    - {DOMAIN}_EMBEDDING_DIMENSION
    - {DOMAIN}_EMBEDDING_MODEL
    etc.

    Falls back to the shared LLM config when domain-specific keys are absent.
    """

    def __init__(self, config_service: ConfigService):
        self.config_service = config_service

    async def get_config(self, domain: str) -> EmbeddingConfig:
        """Get embedding configuration for the specified domain."""
        prefix = domain.upper()

        dimension = await self.config_service.get_value(
            f"{prefix}_EMBEDDING_DIMENSION", None
        )
        model = await self.config_service.get_value(
            f"{prefix}_EMBEDDING_MODEL", None
        )
        api_base = await self.config_service.get_value(
            f"{prefix}_EMBEDDING_API_BASE", None
        )
        api_key = await self.config_service.get_value(
            f"{prefix}_EMBEDDING_API_KEY", None
        )
        api_format = await self.config_service.get_value(
            f"{prefix}_EMBEDDING_API_FORMAT", None
        )
        enabled = await self.config_service.get_value(
            f"{prefix}_EMBEDDING_ENABLED", None
        )

        # If any domain-specific key is missing, fall back to shared config
        if dimension is None or model is None:
            llm_config = await self.config_service.get_llm_config()
            return _llm_config_to_embedding_config(llm_config)

        return EmbeddingConfig(
            dimension=int(dimension),
            model=str(model),
            api_base=str(api_base or ""),
            api_key=str(api_key or ""),
            api_format=str(api_format or "openai"),
            enabled=str(enabled).lower() in ("true", "1", "yes", "on"),
        )


def _llm_config_to_embedding_config(llm_config: LLMConfig) -> EmbeddingConfig:
    """Convert LLMConfig to EmbeddingConfig."""
    return EmbeddingConfig(
        dimension=llm_config.embedding_dimension,
        model=llm_config.embedding_model,
        api_base=llm_config.embedding_api_base,
        api_key=llm_config.embedding_api_key,
        api_format=llm_config.embedding_api_format or llm_config.api_format,
        enabled=llm_config.embedding_enabled,
    )


async def get_embedding_config_provider(
    config_service: ConfigService,
) -> EmbeddingConfigProvider:
    """
    Factory function to get the current embedding config provider.

    Returns UnifiedEmbeddingConfigProvider by default.
    To switch to per-domain config, change the implementation here.
    """
    return UnifiedEmbeddingConfigProvider(config_service)
