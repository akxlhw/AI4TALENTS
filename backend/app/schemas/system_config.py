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
    enabled: bool | None = Field(None, description="Enable chat model functionality")
    embedding_enabled: bool | None = Field(None, description="Enable embedding model functionality")
    api_format: str | None = Field(None, description="API format (openai/minimax)")
    api_key: str | None = Field(None, description="API key")
    api_base: str | None = Field(None, description="API base URL")
    model: str | None = Field(None, description="Chat model name")
    embedding_model: str | None = Field(None, description="Embedding model name")
    embedding_api_base: str | None = Field(None, description="Embedding API base URL (optional)")
    embedding_api_key: str | None = Field(None, description="Embedding API key (optional)")
    embedding_api_format: str | None = Field(None, description="Embedding API format (openai/minimax), defaults to api_format")
    embedding_dimension: int | None = Field(None, ge=128, le=4096, description="Embedding vector dimension (128-4096)")
    timeout: int | None = Field(None, ge=1, le=600, description="Request timeout in seconds")


class LLMConfigResponse(BaseModel):
    """Response for LLM configuration."""
    enabled: bool
    embedding_enabled: bool
    api_format: str
    api_key_masked: str  # Masked API key for display
    api_base: str
    model: str
    embedding_model: str
    embedding_api_base: str
    embedding_api_key_masked: str  # Masked embedding API key for display
    embedding_api_format: str
    embedding_dimension: int
    timeout: int


class ProxyConfigRequest(BaseModel):
    """Request for updating proxy configuration."""
    enabled: bool | None = Field(None, description="Enable HTTP proxy")
    url: str | None = Field(None, description="Proxy server URL (e.g., http://proxy.company.com:8080)")
    username: str | None = Field(None, description="Proxy username (optional)")
    password: str | None = Field(None, description="Proxy password (optional)")
    no_proxy: str | None = Field(None, description="Addresses to bypass proxy (comma-separated, e.g., localhost,*.internal.com)")
    ssl_verify: bool | None = Field(None, description="Verify SSL certificates (set False for self-signed certs)")


class ProxyConfigResponse(BaseModel):
    """Response for proxy configuration."""
    enabled: bool
    url: str
    username: str
    password_masked: str  # Masked password for display
    no_proxy: str  # Addresses to bypass proxy
    ssl_verify: bool  # Whether to verify SSL certificates


class TestProxyRequest(BaseModel):
    """Request for testing proxy connection."""
    url: str | None = Field(None, description="Proxy URL to test (optional, uses saved config if not provided)")
    username: str | None = Field(None, description="Proxy username (optional)")
    password: str | None = Field(None, description="Proxy password (optional)")
    test_internal_url: str | None = Field(None, description="Internal URL to test (optional, for no_proxy validation)")


class TestProxyResult(BaseModel):
    """Result of a single proxy test."""
    url: str
    success: bool
    message: str
    used_proxy: bool = True


class TestProxyResponse(BaseModel):
    """Response for testing proxy connection."""
    success: bool
    message: str
    details: dict | None = None
    results: list[TestProxyResult] | None = Field(None, description="Individual test results")


class TestLLMRequest(BaseModel):
    """Request for testing LLM connection."""
    api_format: str | None = Field(None, description="API format (openai/minimax)")
    api_key: str | None = Field(None, description="API key to test (optional)")
    api_base: str | None = Field(None, description="API base URL to test (optional)")
    model: str | None = Field(None, description="Model name to test (optional)")


class TestLLMResponse(BaseModel):
    """Response for testing LLM connection."""
    success: bool
    message: str
    details: dict | None = None


class TestEmbeddingRequest(BaseModel):
    """Request for testing embedding model connection."""
    api_format: str | None = Field(None, description="API format (openai/minimax)")
    api_key: str | None = Field(None, description="API key to test (optional)")
    api_base: str | None = Field(None, description="API base URL to test (optional)")
    embedding_model: str | None = Field(None, description="Embedding model name to test (optional)")


class TestEmbeddingResponse(BaseModel):
    """Response for testing embedding connection."""
    success: bool
    message: str
    details: dict | None = None
