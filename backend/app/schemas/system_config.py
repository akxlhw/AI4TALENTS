"""
Schemas for system configuration API.
"""
from pydantic import BaseModel, Field


class SystemConfigItem(BaseModel):
    """System configuration item."""
    key: str
    value: str | int | float | bool | None
    display_value: str | int | float | bool | None
    type: str
    is_sensitive: bool
    description: str | None = None


class SystemConfigListResponse(BaseModel):
    """Response for listing system configurations."""
    items: list[SystemConfigItem]
    total: int


class UpdateConfigRequest(BaseModel):
    """Request for updating a configuration value."""
    value: str | int | float | bool = Field(..., description="Configuration value")


class LLMConfigRequest(BaseModel):
    """Request for updating LLM configuration."""
    enabled: bool | None = Field(None, description="Enable LLM functionality")
    provider: str | None = Field(None, description="LLM provider (deepseek/openai/zhipu/qwen/minimax/custom)")
    api_key: str | None = Field(None, description="API key")
    api_base: str | None = Field(None, description="API base URL")
    model: str | None = Field(None, description="Chat model name")
    embedding_model: str | None = Field(None, description="Embedding model name")
    embedding_api_base: str | None = Field(None, description="Embedding API base URL (optional)")
    timeout: int | None = Field(None, ge=1, le=600, description="Request timeout in seconds")


class LLMConfigResponse(BaseModel):
    """Response for LLM configuration."""
    enabled: bool
    provider: str
    api_key_masked: str  # Masked API key for display
    api_base: str
    model: str
    embedding_model: str
    embedding_api_base: str
    timeout: int


class TestLLMRequest(BaseModel):
    """Request for testing LLM connection."""
    provider: str | None = Field(None, description="Provider to test (optional, uses saved config if not provided)")
    api_key: str | None = Field(None, description="API key to test (optional)")
    api_base: str | None = Field(None, description="API base URL to test (optional)")


class TestLLMResponse(BaseModel):
    """Response for testing LLM connection."""
    success: bool
    message: str
    details: dict | None = None
