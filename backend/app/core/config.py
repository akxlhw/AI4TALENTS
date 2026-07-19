"""
Application configuration module.
Loads settings from environment variables.
"""

from __future__ import annotations

import secrets
import warnings
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _generate_secret_key() -> str:
    """Generate a secure random secret key for development."""
    return secrets.token_urlsafe(32)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "智能人才库 API"
    APP_VERSION: str = "3.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development, test, production

    # API
    API_V1_PREFIX: str = "/api/v1"
    # Backend service port (local dev 8003; Docker deployments should set BACKEND_PORT=8000)
    BACKEND_PORT: int = 8003

    # Database
    DATABASE_URL: str = ""
    DATABASE_SYNC_URL: str = ""

    # OpenAlex API
    OPENALEX_BASE_URL: str = "https://api.openalex.org"
    OPENALEX_EMAIL: str | None = None  # For polite API access
    OPENALEX_RATE_LIMIT: int = 10  # Requests per second

    # GitHub API (v2.0 - Open Source Talent)
    GITHUB_TOKENS: str = ""  # Comma-separated GitHub personal access tokens
    GITHUB_BASE_URL: str = "https://api.github.com"
    GITHUB_RATE_LIMIT: int = 5000  # Requests per hour per token

    # JWT Authentication
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 8
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS - 生产环境必须限制为具体域名
    # 开发环境: ["http://localhost:2012", "http://localhost:3000"]
    # 生产环境: ["https://your-domain.com"]
    CORS_ORIGINS: list[str] = ["http://localhost:2012"]

    # Rate Limiting (disabled in development)
    RATE_LIMIT_ENABLED: bool = False  # Enable in production
    RATE_LIMIT_PER_MINUTE: int = 100  # Requests per minute per user/IP

    # Circuit Breaker (P0 fix)
    CIRCUIT_BREAKER_ENABLED: bool = True
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT: float = 30.0
    CIRCUIT_BREAKER_WINDOW_SIZE: int = 10

    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # Batch/Sync
    BATCH_SIZE: int = 1000
    SYNC_TIMEOUT: int = 3600  # 1 hour

    # Redis / Cache
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_ENABLED: bool = False
    REDIS_PASSWORD: str | None = None
    REDIS_MAX_CONNECTIONS: int = 10
    CACHE_DEFAULT_TTL: int = 300  # 5 minutes
    CACHE_KEY_PREFIX: str = "ai4talents"

    # ========== LLM Configuration (v1.4) ==========
    LLM_ENABLED: bool = False  # Global switch for LLM features
    LLM_PROVIDER: str = "deepseek"  # deepseek, openai, zhipu, qwen, custom
    LLM_API_KEY: str = ""
    LLM_API_BASE: str = "https://api.deepseek.com/v1"  # API base URL
    LLM_MODEL: str = "deepseek-chat"  # Chat model name
    LLM_EMBEDDING_MODEL: str = "deepseek-embedding"  # Embedding model name

    # LLM Advanced
    LLM_TIMEOUT: float = 30.0  # API timeout in seconds
    LLM_MAX_RETRIES: int = 3  # Max retry attempts
    LLM_ENABLE_FALLBACK: bool = False  # Disable fallback, require LLM for JD parsing

    # JD Match Score Weights
    # research + impact (h-index) blended scoring
    JD_MATCH_WEIGHT_RESEARCH: float = 0.8  # 研究方向匹配权重
    JD_MATCH_WEIGHT_IMPACT: float = 0.2  # 学术影响力权重 (h-index)
    JD_MATCH_H_REF: float = 100.0  # h-index 对数归一化参考上限

    @property
    def JD_MATCH_WEIGHTS(self) -> dict:
        """获取 JD 匹配权重字典"""
        return {
            "research": self.JD_MATCH_WEIGHT_RESEARCH,
            "impact": self.JD_MATCH_WEIGHT_IMPACT,
        }

    # Embedding Configuration
    EMBEDDING_DIMENSION: int = 1536  # Vector dimension
    EMBEDDING_BATCH_SIZE: int = 100  # Batch size for embedding generation

    # LLM Gateway
    LLM_MAX_BATCH_SIZE: int = 16  # Max requests per batch to LLM API

    # HTTP Client Timeouts
    HTTP_TIMEOUT_SHORT: float = 10.0  # For internal/health checks
    HTTP_TIMEOUT_DEFAULT: float = 30.0  # For external API calls

    # Data Sync
    SYNC_COMMIT_BATCH_SIZE: int = 100  # Commit interval for raw data insertion

    # GitHub API
    GITHUB_PER_PAGE: int = 100  # Items per page for GitHub API
    GITHUB_BATCH_SIZE: int = 5  # Concurrent repo requests (reduced to avoid burst detection)

    # Collection
    COLLECT_ERROR_MAX_LENGTH: int = 500  # Max length for collection error messages
    COLLECT_SUBTASK_RETRY_COUNT: int = 3  # Max retries per venue sub-task (Phase 1)
    COLLECT_SUBTASK_RETRY_BASE_WAIT: int = 1  # Base wait seconds for sub-task retry backoff

    # Genealogy
    GENEALOGY_RANKING_DEFAULT_LIMIT: int = 50
    GENEALOGY_RANKING_MAX_LIMIT: int = 200

    # Schools
    SCHOOL_LIST_MAX_PAGE_SIZE: int = 5000

    # Materialized View Refresh
    MV_REFRESH_TIMEOUT: int = 300  # Seconds for materialized view refresh

    # Search Configuration (v1.4)
    SEARCH_DEFAULT_MODE: str = "keyword"  # keyword, fulltext, semantic, hybrid
    SEARCH_ENABLE_SEMANTIC: bool = True  # Enable semantic search

    # Search Thresholds
    SEARCH_SEMANTIC_THRESHOLD: float = 0.5  # Minimum similarity for semantic search
    SEARCH_PRECISE_THRESHOLD: float = 0.95  # Threshold for "precise match" classification
    SEARCH_SIMILAR_THRESHOLD_MIN: float = 0.7  # Minimum for "similar match" classification

    # Hybrid Search
    SEARCH_RRF_CONSTANT: int = 60  # Reciprocal Rank Fusion constant (k)
    SEARCH_HYBRID_EXTENDED_FACTOR: int = 3  # Get extended_page_size = page_size * factor

    # Recommend Thresholds
    RECOMMEND_SIMILARITY_THRESHOLD: float = 0.6  # Minimum similarity for recommendations
    RECOMMEND_TAG_WEIGHT: float = 0.5  # Weight for tag overlap in fallback similarity
    RECOMMEND_RESEARCH_WEIGHT: float = 0.5  # Weight for research overlap in fallback similarity

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent.parent / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._validate_security_settings()

    def _validate_security_settings(self) -> None:
        """Validate critical security settings and warn if unsafe."""
        # Validate SECRET_KEY
        if not self.SECRET_KEY:
            if self.ENVIRONMENT == "production":
                raise ValueError(
                    "SECRET_KEY must be set in production environment. "
                    'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(32))"'
                )
            # Development: auto-generate but warn
            object.__setattr__(self, "SECRET_KEY", _generate_secret_key())
            warnings.warn(
                "SECRET_KEY not set. Using auto-generated key for development only. "
                "Set a persistent SECRET_KEY in your .env file.",
                RuntimeWarning,
                stacklevel=3,
            )
        elif len(self.SECRET_KEY) < 32:
            warnings.warn(
                f"SECRET_KEY is too short ({len(self.SECRET_KEY)} chars). "
                "Recommended: at least 32 characters for security.",
                RuntimeWarning,
                stacklevel=3,
            )

        # Validate DATABASE_URL
        if not self.DATABASE_URL:
            raise ValueError(
                "DATABASE_URL must be set. "
                "Example: postgresql+asyncpg://user:password@localhost:5432/db_name"
            )

        # Validate CORS in production
        if self.ENVIRONMENT == "production":
            if not self.CORS_ORIGINS or self.CORS_ORIGINS == ["*"]:
                raise ValueError(
                    "CORS_ORIGINS must be explicitly set to specific domains in production. "
                    "Wildcard '*' is not allowed for security reasons."
                )
            if any("localhost" in origin for origin in self.CORS_ORIGINS):
                raise ValueError(
                    "CORS_ORIGINS must not contain localhost in production. "
                    "Set specific production domains instead."
                )

        # Warn about default/weak database credentials in non-dev environments
        if self.ENVIRONMENT in ("staging", "production"):
            if "talent_password" in self.DATABASE_URL or "ai4recruit" in self.DATABASE_URL:
                warnings.warn(
                    "DATABASE_URL appears to use default or weak credentials. "
                    "Please use strong, unique passwords in staging/production.",
                    RuntimeWarning,
                    stacklevel=3,
                )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
