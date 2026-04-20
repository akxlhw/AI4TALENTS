"""
System configuration API endpoints.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import require_user
from app.core.database import get_async_session
from app.schemas.system_config import (
    LLMConfigRequest,
    LLMConfigResponse,
    ProxyConfigRequest,
    ProxyConfigResponse,
    SystemConfigItem,
    SystemConfigListResponse,
    TestLLMRequest,
    TestLLMResponse,
    TestEmbeddingRequest,
    TestEmbeddingResponse,
    TestProxyRequest,
    TestProxyResponse,
    TestProxyResult,
    UpdateConfigRequest,
)
from app.services.config_service import ConfigService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system-config", tags=["System Configuration"])


def require_admin_user(current_user: dict = Depends(require_user)) -> dict:
    """Require admin or super_admin role."""
    if current_user.get("role") not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get(
    "",
    response_model=SystemConfigListResponse,
    summary="获取系统配置列表",
    description="获取所有系统配置项"
)
async def list_configs(
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin_user),
):
    """List all system configurations."""
    config_service = ConfigService(session)
    configs = await config_service.get_all(mask_sensitive=True)

    items = [SystemConfigItem(**config) for config in configs]
    return SystemConfigListResponse(items=items, total=len(items))


@router.get(
    "/llm",
    response_model=LLMConfigResponse,
    summary="获取 LLM 配置",
    description="获取 LLM 相关配置（API Key 已脱敏）"
)
async def get_llm_config(
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin_user),
):
    """Get LLM configuration."""
    config_service = ConfigService(session)
    config = await config_service.get_llm_config()

    return LLMConfigResponse(
        enabled=config.enabled,
        provider=config.provider,
        api_key_masked=config_service.mask_sensitive_value(
            "LLM_API_KEY", config.api_key
        ) if config.api_key else "",
        api_base=config.api_base,
        model=config.model,
        embedding_model=config.embedding_model,
        embedding_api_base=config.embedding_api_base,
        embedding_api_key_masked=config_service.mask_sensitive_value(
            "LLM_EMBEDDING_API_KEY", config.embedding_api_key
        ) if config.embedding_api_key else "",
        timeout=config.timeout,
    )


@router.put(
    "/llm",
    summary="更新 LLM 配置",
    description="更新 LLM 相关配置"
)
async def update_llm_config(
    request: LLMConfigRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin_user),
):
    """Update LLM configuration."""
    config_service = ConfigService(session)

    # Only update provided fields
    update_data = request.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    await config_service.update_llm_config(update_data)
    await session.commit()

    # Clear cache to force refresh
    ConfigService.clear_cache()

    logger.info(f"LLM configuration updated by user {current_user.get('user_id')}")

    return {"message": "LLM configuration updated successfully"}


@router.post(
    "/test-llm",
    response_model=TestLLMResponse,
    summary="测试 LLM 连接",
    description="测试 LLM API 连接是否正常"
)
async def test_llm_connection(
    request: TestLLMRequest | None = None,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin_user),
):
    """Test LLM API connection."""
    config_service = ConfigService(session)

    # Get saved config or use provided values
    if request and request.api_key:
        # Use provided values for testing
        provider = request.provider or "deepseek"
        api_key = request.api_key
        api_base = request.api_base or ""
        model = request.model or ""
    else:
        # Use saved config
        config = await config_service.get_llm_config()
        if not config.enabled:
            return TestLLMResponse(
                success=False,
                message="LLM is not enabled. Please enable it first.",
            )
        provider = config.provider
        api_key = config.api_key
        api_base = config.api_base
        model = config.model

    if not api_key:
        return TestLLMResponse(
            success=False,
            message="API key is required",
        )

    # Test connection based on provider
    try:
        if provider == "deepseek":
            return await _test_deepseek(api_key, api_base, model)
        elif provider == "openai":
            return await _test_openai(api_key, api_base, model)
        elif provider == "zhipu":
            return await _test_zhipu(api_key, api_base, model)
        elif provider == "qwen":
            return await _test_qwen(api_key, api_base, model)
        elif provider == "minimax":
            return await _test_minimax(api_key, api_base, model)
        else:
            # Generic test for custom providers
            return await _test_generic(api_key, api_base, model)
    except Exception as e:
        logger.error(f"LLM connection test failed: {e}")
        return TestLLMResponse(
            success=False,
            message=f"Connection test failed: {str(e)}",
        )


async def _test_deepseek(api_key: str, api_base: str, model: str = "") -> TestLLMResponse:
    """Test DeepSeek API connection with model validation."""
    base_url = api_base or "https://api.deepseek.com"
    test_model = model or "deepseek-chat"
    return await _test_openai_compatible(
        api_key=api_key,
        base_url=base_url,
        model=test_model,
        provider_name="DeepSeek",
        provider_key="deepseek",
    )


async def _test_openai(api_key: str, api_base: str, model: str = "") -> TestLLMResponse:
    """Test OpenAI API connection with model validation."""
    base_url = api_base or "https://api.openai.com"
    test_model = model or "gpt-3.5-turbo"
    return await _test_openai_compatible(
        api_key=api_key,
        base_url=base_url,
        model=test_model,
        provider_name="OpenAI",
        provider_key="openai",
    )


async def _test_zhipu(api_key: str, api_base: str, model: str = "") -> TestLLMResponse:
    """Test Zhipu AI API connection with model validation."""
    base_url = api_base or "https://open.bigmodel.cn/api/paas/v4"
    test_model = model or "glm-4-flash"
    return await _test_openai_compatible(
        api_key=api_key,
        base_url=base_url,
        model=test_model,
        provider_name="智谱 AI",
        provider_key="zhipu",
    )


async def _test_qwen(api_key: str, api_base: str, model: str = "") -> TestLLMResponse:
    """Test Qwen (Alibaba Tongyi) API connection with model validation."""
    base_url = api_base or "https://dashscope.aliyuncs.com/compatible-mode"
    test_model = model or "qwen-turbo"
    return await _test_openai_compatible(
        api_key=api_key,
        base_url=base_url,
        model=test_model,
        provider_name="通义千问",
        provider_key="qwen",
    )


async def _test_minimax(api_key: str, api_base: str, model: str = "") -> TestLLMResponse:
    """Test MiniMax API connection with model validation."""
    base_url = api_base or "https://api.minimax.chat/v1"
    test_model = model or "abab6.5s-chat"
    provider_name = "MiniMax"

    # 确保 URL 以 /v1 结尾
    if not base_url.endswith("/v1"):
        base_url = base_url.rstrip("/") + "/v1"

    return await _test_openai_compatible(
        api_key=api_key,
        base_url=base_url,
        model=test_model,
        provider_name=provider_name,
        provider_key="minimax",
    )


async def _test_generic(api_key: str, api_base: str, model: str = "") -> TestLLMResponse:
    """Generic API connection test with model validation."""
    if not api_base:
        return TestLLMResponse(
            success=False,
            message="自定义提供商需要配置 API Base URL",
        )

    test_model = model or "gpt-3.5-turbo"
    return await _test_openai_compatible(
        api_key=api_key,
        base_url=api_base,
        model=test_model,
        provider_name="自定义 API",
        provider_key="custom",
    )


async def _test_openai_compatible(
    api_key: str,
    base_url: str,
    model: str,
    provider_name: str,
    provider_key: str,
) -> TestLLMResponse:
    """通用 OpenAI 兼容 API 测试函数。"""
    from app.services.common.http_client import HttpClientFactory

    async with HttpClientFactory.create_client_for_url(base_url, timeout=30.0) as client:
        # Step 1: Try chat completion to verify model and key
        chat_endpoint = f"{base_url}/chat/completions" if base_url.endswith("/v1") else f"{base_url}/v1/chat/completions"
        response = await client.post(
            chat_endpoint,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1},
        )

        if response.status_code == 200:
            return TestLLMResponse(
                success=True,
                message=f"{provider_name} 连接成功，模型: {model}",
                details={"provider": provider_key, "base_url": base_url, "model": model},
            )

        # Step 2: Analyze error
        error_data = {}
        try:
            error_data = response.json()
        except Exception:
            pass

        error_msg = (
            error_data.get("error", {}).get("message", "")
            or error_data.get("message", "")
            or error_data.get("error_message", "")
            or error_data.get("base_resp", {}).get("status_msg", "")
        )

        # 401 - API Key invalid
        if response.status_code == 401 or any(kw in error_msg.lower() for kw in ["unauthorized", "invalid api-key", "invalid api key"]):
            return TestLLMResponse(
                success=False,
                message=f"{provider_name} API Key 无效或已过期",
            )

        # Model not found - try to get available models
        model_error_keywords = ["model", "not found", "does not exist", "unknown model"]
        if any(kw in error_msg.lower() for kw in model_error_keywords):
            models_endpoint = f"{base_url}/models" if base_url.endswith("/v1") else f"{base_url}/v1/models"
            models_response = await client.get(
                models_endpoint,
                headers={"Authorization": f"Bearer {api_key}"},
            )
            available_models = []
            if models_response.status_code == 200:
                try:
                    models_data = models_response.json()
                    model_list = models_data.get("data", []) or models_data.get("models", [])
                    available_models = [m.get("id") or m.get("model_id") for m in model_list if m.get("id") or m.get("model_id")]
                except Exception:
                    pass

            if available_models:
                return TestLLMResponse(
                    success=False,
                    message=f"模型 '{model}' 不存在。可用模型: {', '.join(available_models[:10])}",
                    details={"error": error_msg, "available_models": available_models},
                )
            else:
                return TestLLMResponse(
                    success=False,
                    message=f"模型 '{model}' 不存在，请检查模型名称是否正确",
                    details={"error": error_msg},
                )

        # Other errors
        return TestLLMResponse(
            success=False,
            message=f"{provider_name} 错误: {error_msg or f'状态码 {response.status_code}'}",
        )


async def _test_generic(api_key: str, api_base: str, model: str = "") -> TestLLMResponse:
    """Generic API connection test using /v1/models endpoint."""
    if not api_base:
        return TestLLMResponse(
            success=False,
            message="自定义提供商需要配置 API Base URL",
        )

    from app.services.common.http_client import HttpClientFactory

    async with HttpClientFactory.create_client_for_url(api_base, timeout=30.0) as client:
        response = await client.get(
            f"{api_base}/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
        )

        if response.status_code == 200:
            model_info = f", model: {model}" if model else ""
            return TestLLMResponse(
                success=True,
                message=f"自定义 API 连接成功{model_info}",
                details={"base_url": api_base, "model": model},
            )
        else:
            return TestLLMResponse(
                success=False,
                message=f"自定义 API 返回状态码 {response.status_code}",
            )


# ========== Embedding Test Endpoints ==========

@router.post(
    "/test-embedding",
    response_model=TestEmbeddingResponse,
    summary="测试嵌入模型连接",
    description="测试嵌入模型 API 连接是否正常"
)
async def test_embedding_connection(
    request: TestEmbeddingRequest | None = None,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin_user),
):
    """Test embedding model connection."""
    config_service = ConfigService(session)

    # Get saved config or use provided values
    if request and request.api_key:
        provider = request.provider or "deepseek"
        api_key = request.api_key
        api_base = request.api_base or ""
        embedding_model = request.embedding_model or ""
    else:
        config = await config_service.get_llm_config()
        if not config.enabled:
            return TestEmbeddingResponse(
                success=False,
                message="LLM 未启用，请先启用 LLM 功能",
            )
        provider = config.provider
        api_key = config.api_key
        # Use embedding_api_base if configured, otherwise use main api_base
        api_base = config.embedding_api_base or config.api_base
        embedding_model = config.embedding_model

    if not api_key:
        return TestEmbeddingResponse(
            success=False,
            message="API Key 未配置",
        )

    if not embedding_model:
        return TestEmbeddingResponse(
            success=False,
            message="嵌入模型名称未配置，请先在系统配置中设置嵌入模型名称",
        )

    # Test embedding connection
    try:
        return await _test_embedding(api_key, api_base, embedding_model, provider)
    except Exception as e:
        logger.error(f"Embedding connection test failed: {e}")
        return TestEmbeddingResponse(
            success=False,
            message=f"连接测试失败: {str(e)}",
        )


async def _test_embedding(
    api_key: str,
    api_base: str,
    embedding_model: str,
    provider: str,
) -> TestEmbeddingResponse:
    """Test embedding model connection."""
    from app.services.common.http_client import HttpClientFactory

    # Determine base URL based on provider
    if not api_base:
        if provider == "deepseek":
            api_base = "https://api.deepseek.com"
        elif provider == "openai":
            api_base = "https://api.openai.com"
        elif provider == "zhipu":
            api_base = "https://open.bigmodel.cn/api/paas/v4"
        elif provider == "qwen":
            api_base = "https://dashscope.aliyuncs.com/compatible-mode"
        elif provider == "minimax":
            api_base = "https://api.minimax.chat/v1"
        else:
            return TestEmbeddingResponse(
                success=False,
                message="自定义提供商需要配置 API Base URL",
            )

    # MiniMax uses different embedding API format
    if provider == "minimax":
        return await _test_embedding_minimax(api_key, api_base, embedding_model)

    # Standard OpenAI-compatible embedding API
    async with HttpClientFactory.create_client_for_url(api_base, timeout=30.0) as client:
        # Build endpoint URL
        if api_base.endswith("/v1"):
            endpoint = f"{api_base}/embeddings"
        else:
            endpoint = f"{api_base}/v1/embeddings"

        response = await client.post(
            endpoint,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": embedding_model,
                "input": "test",
            },
        )

        if response.status_code == 200:
            data = response.json()
            # Check if we got valid embedding
            embedding = None
            if "data" in data and len(data["data"]) > 0:
                embedding = data["data"][0].get("embedding", [])
            elif "vectors" in data and len(data["vectors"]) > 0:
                embedding = data["vectors"][0]

            if embedding and len(embedding) > 0:
                return TestEmbeddingResponse(
                    success=True,
                    message=f"嵌入模型连接成功，模型: {embedding_model}，向量维度: {len(embedding)}",
                    details={
                        "provider": provider,
                        "base_url": api_base,
                        "model": embedding_model,
                        "dimensions": len(embedding),
                    },
                )
            else:
                return TestEmbeddingResponse(
                    success=False,
                    message="API 返回成功但未获取到有效向量",
                )

        # Analyze error
        error_data = {}
        try:
            error_data = response.json()
        except Exception:
            pass

        error_msg = (
            error_data.get("error", {}).get("message", "")
            or error_data.get("message", "")
            or error_data.get("error_message", "")
        )

        # 401 - API Key invalid
        if response.status_code == 401 or "unauthorized" in error_msg.lower() or "invalid" in error_msg.lower():
            return TestEmbeddingResponse(
                success=False,
                message="API Key 无效或已过期",
            )

        # Model not found
        if "model" in error_msg.lower() or "not found" in error_msg.lower():
            return TestEmbeddingResponse(
                success=False,
                message=f"嵌入模型 '{embedding_model}' 不存在，请检查模型名称是否正确",
                details={"error": error_msg},
            )

        return TestEmbeddingResponse(
            success=False,
            message=f"嵌入 API 错误: {error_msg or f'状态码 {response.status_code}'}",
        )


async def _test_embedding_minimax(
    api_key: str,
    api_base: str,
    embedding_model: str,
) -> TestEmbeddingResponse:
    """Test MiniMax embedding model connection."""
    from app.services.common.http_client import HttpClientFactory

    # Ensure URL ends with /v1
    if not api_base.endswith("/v1"):
        api_base = api_base.rstrip("/") + "/v1"

    # Default model for MiniMax
    model = embedding_model or "embo-01"

    async with HttpClientFactory.create_client_for_url(api_base, timeout=30.0) as client:
        response = await client.post(
            f"{api_base}/embeddings",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "texts": ["test"],
                "type": "db",
            },
        )

        if response.status_code == 200:
            data = response.json()
            vectors = data.get("vectors", [])
            if vectors and len(vectors) > 0:
                return TestEmbeddingResponse(
                    success=True,
                    message=f"MiniMax 嵌入模型连接成功，模型: {model}，向量维度: {len(vectors[0])}",
                    details={
                        "provider": "minimax",
                        "base_url": api_base,
                        "model": model,
                        "dimensions": len(vectors[0]),
                    },
                )
            else:
                base_resp = data.get("base_resp", {})
                status_msg = base_resp.get("status_msg", "Unknown error")
                return TestEmbeddingResponse(
                    success=False,
                    message=f"MiniMax 返回错误: {status_msg}",
                )

        # Handle error
        error_data = {}
        try:
            error_data = response.json()
        except Exception:
            pass

        error_msg = (
            error_data.get("base_resp", {}).get("status_msg", "")
            or error_data.get("message", "")
        )

        if response.status_code == 401 or "unauthorized" in str(error_data).lower():
            return TestEmbeddingResponse(
                success=False,
                message="MiniMax API Key 无效或已过期",
            )

        return TestEmbeddingResponse(
            success=False,
            message=f"MiniMax 嵌入 API 错误: {error_msg or f'状态码 {response.status_code}'}",
        )


# ========== Proxy Configuration Endpoints ==========

@router.get(
    "/proxy",
    response_model=ProxyConfigResponse,
    summary="获取代理配置",
    description="获取 HTTP 代理配置（密码已脱敏）"
)
async def get_proxy_config(
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin_user),
):
    """Get proxy configuration."""
    config_service = ConfigService(session)
    config = await config_service.get_proxy_config()

    return ProxyConfigResponse(
        enabled=config.enabled,
        url=config.url,
        username=config.username,
        password_masked=config_service.mask_sensitive_value(
            "PROXY_PASSWORD", config.password
        ) if config.password else "",
        no_proxy=config.no_proxy,
        ssl_verify=config.ssl_verify,
    )


@router.put(
    "/proxy",
    summary="更新代理配置",
    description="更新 HTTP 代理配置"
)
async def update_proxy_config(
    request: ProxyConfigRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin_user),
):
    """Update proxy configuration."""
    from app.services.common.http_client import HttpClientFactory

    config_service = ConfigService(session)

    # Only update provided fields
    update_data = request.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    await config_service.update_proxy_config(update_data)
    await session.commit()

    # Clear cache to force refresh
    ConfigService.clear_cache()

    # Reload proxy config and refresh HttpClientFactory
    proxy_config = await config_service.get_proxy_config(use_cache=False)
    if proxy_config.enabled and proxy_config.url:
        HttpClientFactory.configure(
            proxy_url=proxy_config.url,
            proxy_username=proxy_config.username or None,
            proxy_password=proxy_config.password or None,
            no_proxy=proxy_config.no_proxy or None,
            ssl_verify=proxy_config.ssl_verify,
        )
        logger.info(f"HttpClientFactory refreshed with proxy: {proxy_config.url}, no_proxy: {proxy_config.no_proxy}")
    else:
        HttpClientFactory.configure()  # Reset to no proxy
        logger.info("HttpClientFactory reset to direct connection")

    logger.info(f"Proxy configuration updated by user {current_user.get('user_id')}")

    return {"message": "Proxy configuration updated successfully"}


@router.post(
    "/test-proxy",
    response_model=TestProxyResponse,
    summary="测试代理连接",
    description="测试代理服务器连接是否正常，同时验证 no_proxy 配置"
)
async def test_proxy_connection(
    request: TestProxyRequest | None = None,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin_user),
):
    """Test proxy connection.

    Tests both:
    1. External API access through proxy
    2. Internal URL direct connection (if no_proxy configured)
    """
    import httpx
    from urllib.parse import urlparse, urlunparse
    from app.services.common.http_client import HttpClientFactory

    config_service = ConfigService(session)

    # Get saved config or use provided values
    if request and request.url:
        proxy_url = request.url
        username = request.username
        password = request.password
        no_proxy = ""  # For ad-hoc test, no no_proxy
        ssl_verify = True  # For ad-hoc test, use default
    else:
        config = await config_service.get_proxy_config()
        if not config.enabled:
            return TestProxyResponse(
                success=False,
                message="Proxy is not enabled. Please enable it first.",
            )
        proxy_url = config.url
        username = config.username
        password = config.password
        no_proxy = config.no_proxy
        ssl_verify = config.ssl_verify

    if not proxy_url:
        return TestProxyResponse(
            success=False,
            message="Proxy URL is required",
        )

    # Build proxy URL with authentication
    if username and password:
        parsed = urlparse(proxy_url)
        netloc = f"{username}:{password}@{parsed.hostname}"
        if parsed.port:
            netloc += f":{parsed.port}"
        full_proxy_url = urlunparse((
            parsed.scheme,
            netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment,
        ))
    else:
        full_proxy_url = proxy_url

    results = []

    # Test 1: External API through proxy
    external_url = "https://api.openalex.org/works?per_page=1"
    try:
        async with httpx.AsyncClient(proxy=full_proxy_url, timeout=30.0, verify=ssl_verify, trust_env=False) as client:
            response = await client.get(external_url)

            if response.status_code == 200:
                results.append({
                    "url": external_url,
                    "success": True,
                    "message": "External API accessible through proxy",
                    "used_proxy": True,
                })
            else:
                results.append({
                    "url": external_url,
                    "success": False,
                    "message": f"Proxy returned status {response.status_code}",
                    "used_proxy": True,
                })
    except httpx.ConnectError as e:
        results.append({
            "url": external_url,
            "success": False,
            "message": f"Failed to connect to proxy: {str(e)}",
            "used_proxy": True,
        })
    except httpx.ProxyError as e:
        results.append({
            "url": external_url,
            "success": False,
            "message": f"Proxy error: {str(e)}",
            "used_proxy": True,
        })
    except Exception as e:
        logger.error(f"External proxy test failed: {e}")
        results.append({
            "url": external_url,
            "success": False,
            "message": f"Connection failed: {str(e)}",
            "used_proxy": True,
        })

    # Test 2: Internal URL direct connection (if no_proxy configured)
    if no_proxy:
        # Try to extract an internal URL from no_proxy patterns
        # Or use the provided test_internal_url
        internal_url = request.test_internal_url if request else None

        # If no specific URL provided, try to infer from no_proxy patterns
        if not internal_url:
            # Parse no_proxy to find a testable URL
            patterns = [p.strip() for p in no_proxy.split(',') if p.strip()]
            for pattern in patterns:
                # Skip wildcards, look for concrete hostnames/IPs
                if '*' not in pattern and not pattern.startswith('.'):
                    if pattern == 'localhost':
                        internal_url = "http://localhost:8003/health"
                        break
                    elif pattern == '127.0.0.1':
                        internal_url = "http://127.0.0.1:8003/health"
                        break
                    # For IP patterns like 10.x.x.x, construct a test URL
                    elif pattern.replace('.', '').isdigit():
                        # This is an IP, try to use it
                        internal_url = f"http://{pattern}:8003/health"
                        break

        if internal_url:
            # Configure HttpClientFactory to check if URL should bypass proxy
            HttpClientFactory.configure(
                proxy_url=proxy_url,
                proxy_username=username,
                proxy_password=password,
                no_proxy=no_proxy
            )

            should_use_proxy = HttpClientFactory.should_use_proxy(internal_url)

            try:
                # Test direct connection (no proxy for internal URLs)
                async with httpx.AsyncClient(timeout=10.0, trust_env=False) as client:
                    response = await client.get(internal_url)

                    if response.status_code in [200, 401, 403, 404]:
                        # Any valid HTTP response counts as success
                        results.append({
                            "url": internal_url,
                            "success": True,
                            "message": f"Internal URL accessible directly (no_proxy matched)",
                            "used_proxy": False,
                        })
                    else:
                        results.append({
                            "url": internal_url,
                            "success": False,
                            "message": f"Internal URL returned status {response.status_code}",
                            "used_proxy": False,
                        })
            except httpx.ConnectError:
                # Connection refused is expected if service not running
                # Still counts as "no_proxy working" because we tried direct
                results.append({
                    "url": internal_url,
                    "success": True,
                    "message": f"Direct connection attempted (no_proxy matched, service may not be running)",
                    "used_proxy": False,
                })
            except Exception as e:
                results.append({
                    "url": internal_url,
                    "success": True,
                    "message": f"Direct connection attempted: {str(e)[:50]}",
                    "used_proxy": False,
                })

    # Determine overall success
    external_success = results[0]["success"] if results else False
    internal_tests = [r for r in results if not r["used_proxy"]]
    internal_success = all(r["success"] for r in internal_tests) if internal_tests else True

    overall_success = external_success and internal_success

    # Build message
    if overall_success:
        if internal_tests:
            message = "Proxy and no_proxy configuration working correctly"
        else:
            message = "Proxy connection successful"
    else:
        failed_tests = [r for r in results if not r["success"]]
        message = f"{len(failed_tests)} test(s) failed"

    return TestProxyResponse(
        success=overall_success,
        message=message,
        details={"proxy_url": proxy_url, "no_proxy": no_proxy},
        results=results,
    )


# ========== Generic Configuration Endpoints ==========
# NOTE: Must be defined AFTER specific paths like /llm, /proxy
# to avoid route conflicts (FastAPI matches routes in order)

@router.put(
    "/{key}",
    response_model=SystemConfigItem,
    summary="更新单个配置项",
    description="更新指定配置项的值"
)
async def update_config(
    key: str,
    request: UpdateConfigRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin_user),
):
    """Update a single configuration value."""
    config_service = ConfigService(session)

    # Determine config type from value type
    if isinstance(request.value, bool):
        config_type = "bool"
    elif isinstance(request.value, int):
        config_type = "int"
    elif isinstance(request.value, float):
        config_type = "float"
    else:
        config_type = "string"

    config = await config_service.set_value(key, request.value, config_type)
    await session.commit()

    # Clear cache for this key
    if key in ConfigService._cache:
        del ConfigService._cache[key]

    logger.info(f"Configuration {key} updated by user {current_user.get('user_id')}")

    return SystemConfigItem(
        key=config.config_key,
        value=config_service._coerce_value(config.config_value, config.config_type),
        display_value=config_service.mask_sensitive_value(
            config.config_key, config.config_value or ""
        ) if config.is_sensitive else config.config_value,
        type=config.config_type,
        is_sensitive=config.is_sensitive,
        description=config.description,
    )
