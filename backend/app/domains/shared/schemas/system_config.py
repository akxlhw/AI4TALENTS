"""
Schemas for system configuration API.
"""

from typing import Any

from pydantic import BaseModel, Field


class SystemConfigItem(BaseModel):
    """System configuration item."""

    key: str = Field(description="配置键")
    value: Any = Field(description="配置值（json 类型可为 dict/list）")
    display_value: Any = Field(description="显示值（敏感配置已脱敏）")
    type: str = Field(description="值类型")
    is_sensitive: bool = Field(description="是否敏感信息")
    description: str | None = Field(default=None, description="配置说明")


class SystemConfigListResponse(BaseModel):
    """Response for listing system configurations."""

    items: list[SystemConfigItem] = Field(description="配置项列表")
    total: int = Field(description="总数")


class UpdateConfigRequest(BaseModel):
    """Request for updating a configuration value."""

    value: str | int | float | bool = Field(..., description="Configuration value")
    description: str | None = Field(
        default=None, description="可选的配置说明（备注名称），便于在配置总览中识别用途"
    )
    is_sensitive: bool | None = Field(
        default=None,
        description="可选，是否标记为敏感（脱敏显示）。对 API Key 类配置应设为 true",
    )


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
    embedding_api_format: str | None = Field(
        None, description="Embedding API format (openai/minimax), defaults to api_format"
    )
    embedding_dimension: int | None = Field(
        None, ge=128, le=4096, description="Embedding vector dimension (128-4096)"
    )
    timeout: int | None = Field(None, ge=1, le=600, description="Request timeout in seconds")


class LLMConfigResponse(BaseModel):
    """Response for LLM configuration."""

    enabled: bool = Field(description="对话模型是否启用")
    embedding_enabled: bool = Field(description="嵌入模型是否启用")
    api_format: str = Field(description="API格式")
    api_key_masked: str = Field(description="脱敏显示的API Key")
    api_base: str = Field(description="API基础URL")
    model: str = Field(description="对话模型名称")
    embedding_model: str = Field(description="嵌入模型名称")
    embedding_api_base: str = Field(description="嵌入模型API基础URL")
    embedding_api_key_masked: str = Field(description="脱敏显示的嵌入模型API Key")
    embedding_api_format: str = Field(description="嵌入模型API格式")
    embedding_dimension: int = Field(description="嵌入向量维度")
    timeout: int = Field(description="请求超时时间(秒)")


class ProxyConfigRequest(BaseModel):
    """Request for updating proxy configuration."""

    enabled: bool | None = Field(None, description="Enable HTTP proxy")
    url: str | None = Field(
        None, description="Proxy server URL (e.g., http://proxy.company.com:8080)"
    )
    username: str | None = Field(None, description="Proxy username (optional)")
    password: str | None = Field(None, description="Proxy password (optional)")
    no_proxy: str | None = Field(
        None,
        description="Addresses to bypass proxy (comma-separated, e.g., localhost,*.internal.com)",
    )
    ssl_verify: bool | None = Field(
        None, description="Verify SSL certificates (set False for self-signed certs)"
    )


class ProxyConfigResponse(BaseModel):
    """Response for proxy configuration."""

    enabled: bool = Field(description="是否启用代理")
    url: str = Field(description="代理服务器URL")
    username: str = Field(description="代理用户名")
    password_masked: str = Field(description="脱敏显示的代理密码")
    no_proxy: str = Field(description="不走代理的地址列表")
    ssl_verify: bool = Field(description="是否验证SSL证书")


class TestProxyRequest(BaseModel):
    """Request for testing proxy connection."""

    url: str | None = Field(
        None, description="Proxy URL to test (optional, uses saved config if not provided)"
    )
    username: str | None = Field(None, description="Proxy username (optional)")
    password: str | None = Field(None, description="Proxy password (optional)")
    test_internal_url: str | None = Field(
        None, description="Internal URL to test (optional, for no_proxy validation)"
    )


class TestProxyResult(BaseModel):
    """Result of a single proxy test."""

    url: str = Field(description="测试URL")
    success: bool = Field(description="是否成功")
    message: str = Field(description="测试结果消息")
    used_proxy: bool = Field(default=True, description="是否使用了代理")


class TestProxyResponse(BaseModel):
    """Response for testing proxy connection."""

    success: bool = Field(description="整体是否成功")
    message: str = Field(description="结果消息")
    details: dict | None = Field(default=None, description="详细数据")
    results: list[TestProxyResult] | None = Field(None, description="Individual test results")


class TestLLMRequest(BaseModel):
    """Request for testing LLM connection."""

    api_format: str | None = Field(None, description="API format (openai/minimax)")
    api_key: str | None = Field(None, description="API key to test (optional)")
    api_base: str | None = Field(None, description="API base URL to test (optional)")
    model: str | None = Field(None, description="Model name to test (optional)")


class TestLLMResponse(BaseModel):
    """Response for testing LLM connection."""

    success: bool = Field(description="是否成功")
    message: str = Field(description="结果消息")
    details: dict | None = Field(default=None, description="详细数据")


class TestEmbeddingRequest(BaseModel):
    """Request for testing embedding model connection."""

    api_format: str | None = Field(None, description="API format (openai/minimax)")
    api_key: str | None = Field(None, description="API key to test (optional)")
    api_base: str | None = Field(None, description="API base URL to test (optional)")
    embedding_model: str | None = Field(None, description="Embedding model name to test (optional)")


class GitHubConfigRequest(BaseModel):
    """Request for updating GitHub API configuration."""

    tokens: str | None = Field(None, description="GitHub Personal Access Tokens，多个用逗号分隔")
    base_url: str | None = Field(None, description="GitHub API 基础地址")
    rate_limit: int | None = Field(None, ge=60, le=50000, description="单 Token 每小时请求上限")


class GitHubConfigResponse(BaseModel):
    """Response for GitHub API configuration."""

    tokens_masked: str = Field(description="脱敏显示的 GitHub Tokens")
    base_url: str = Field(description="GitHub API 基础地址")
    rate_limit: int = Field(description="单 Token 每小时请求上限")


class TestGitHubResponse(BaseModel):
    """Response for testing GitHub API connection."""

    success: bool = Field(description="是否成功")
    message: str = Field(description="结果消息")
    details: dict | None = Field(default=None, description="详细数据")


class TestEmbeddingResponse(BaseModel):
    """Response for testing embedding connection."""

    success: bool = Field(description="是否成功")
    message: str = Field(description="结果消息")
    details: dict | None = Field(default=None, description="详细数据")
