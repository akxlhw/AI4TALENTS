"""
Application configuration module.
Loads settings from environment variables.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "智能人才库 API"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development, test, production

    # API
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://talent_user:talent_password@localhost:5432/talent_db"
    DATABASE_SYNC_URL: str = "postgresql://talent_user:talent_password@localhost:5432/talent_db"

    # OpenAlex API
    OPENALEX_BASE_URL: str = "https://api.openalex.org"
    OPENALEX_EMAIL: str | None = None  # For polite API access
    OPENALEX_RATE_LIMIT: int = 10  # Requests per second

    # GitHub API (v2.0 - Open Source Talent)
    GITHUB_TOKENS: str = ""  # Comma-separated GitHub personal access tokens
    GITHUB_BASE_URL: str = "https://api.github.com"
    GITHUB_RATE_LIMIT: int = 5000  # Requests per hour per token

    # JWT Authentication
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 8

    # CORS - 自动检测前端来源
    # 生产环境：允许同 IP 的前端端口访问（如 http://192.168.1.x:2012）
    # 开发环境：允许所有来源
    CORS_ORIGINS: list[str] = ["*"]  # 简化配置，允许所有来源

    # Rate Limiting (disabled in development)
    RATE_LIMIT_ENABLED: bool = False  # Enable in production
    RATE_LIMIT_PER_MINUTE: int = 100  # Requests per minute per user/IP

    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # Batch/Sync
    BATCH_SIZE: int = 1000
    SYNC_TIMEOUT: int = 3600  # 1 hour

    # Redis / Cache
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_ENABLED: bool = False  # Default disabled for development
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

    # JD Match Score Weights (v1.4.1)
    # Simplified to only research weight
    JD_MATCH_WEIGHT_RESEARCH: float = 1.0  # 研究方向匹配权重

    @property
    def JD_MATCH_WEIGHTS(self) -> dict:
        """获取 JD 匹配权重字典"""
        return {
            "research": self.JD_MATCH_WEIGHT_RESEARCH,
        }

    # Embedding Configuration
    EMBEDDING_DIMENSION: int = 1536  # Vector dimension
    EMBEDDING_BATCH_SIZE: int = 100  # Batch size for embedding generation

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

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
