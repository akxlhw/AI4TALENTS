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
    embedding_api_key: str | None = Field(None, description="Embedding API key (optional, uses main API key if not provided)")
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
    embedding_api_key_masked: str  # Masked embedding API key for display
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
    provider: str | None = Field(None, description="Provider to test (optional, uses saved config if not provided)")
    api_key: str | None = Field(None, description="API key to test (optional)")
    api_base: str | None = Field(None, description="API base URL to test (optional)")
    model: str | None = Field(None, description="Model name to test (optional)")


class TestLLMResponse(BaseModel):
    """Response for testing LLM connection."""
    success: bool
    message: str
    details: dict | None = None
