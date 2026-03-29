"""
Application configuration module.
Loads settings from environment variables.
"""
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "智能人才库 API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development, test, production

    # API
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://talent_user:talent_password@localhost:5432/talent_db"
    DATABASE_SYNC_URL: str = "postgresql://talent_user:talent_password@localhost:5432/talent_db"

    # OpenAlex API
    OPENALEX_BASE_URL: str = "https://api.openalex.org"
    OPENALEX_EMAIL: Optional[str] = None  # For polite API access
    OPENALEX_RATE_LIMIT: int = 10  # Requests per second

    # JWT Authentication
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 8

    # CORS - 前端固定使用 5173 端口
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # Batch/Sync
    BATCH_SIZE: int = 1000
    SYNC_TIMEOUT: int = 3600  # 1 hour

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
