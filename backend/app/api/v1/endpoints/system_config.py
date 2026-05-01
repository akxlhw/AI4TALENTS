"""
System configuration API endpoints.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import require_user
from app.core.database import get_async_session
from app.schemas.common import SuccessResponse
from app.schemas.system_config import (
    GitHubConfigRequest,
    GitHubConfigResponse,
    LLMConfigRequest,
    LLMConfigResponse,
    ProxyConfigRequest,
    ProxyConfigResponse,
    SystemConfigItem,
    SystemConfigListResponse,
    TestEmbeddingRequest,
    TestEmbeddingResponse,
    TestGitHubResponse,
    TestLLMRequest,
    TestLLMResponse,
    TestProxyRequest,
    TestProxyResponse,
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
    description="获取所有系统配置项",
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
    description="获取 LLM 相关配置（API Key 已脱敏）",
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
        embedding_enabled=config.embedding_enabled,
        api_format=config.api_format,
        api_key_masked=(
            config_service.mask_sensitive_value("LLM_API_KEY", config.api_key)
            if config.api_key
            else ""
        ),
        api_base=config.api_base,
        model=config.model,
        embedding_model=config.embedding_model,
        embedding_api_base=config.embedding_api_base,
        embedding_api_key_masked=(
            config_service.mask_sensitive_value("LLM_EMBEDDING_API_KEY", config.embedding_api_key)
            if config.embedding_api_key
            else ""
        ),
        embedding_api_format=config.embedding_api_format,
        embedding_dimension=config.embedding_dimension,
        timeout=config.timeout,
    )


@router.put("/llm", response_model=dict, summary="更新 LLM 配置", description="更新 LLM 相关配置")
async def update_llm_config(
    request: LLMConfigRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin_user),
):
    """Update LLM configuration."""
    config_service = ConfigService(session)

    # Get current config to check dimension change
    current_config = await config_service.get_llm_config()
    current_dimension = current_config.embedding_dimension

    # Only update provided fields
    update_data = request.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Check if dimension is changing
    new_dimension = update_data.get("embedding_dimension")
    dimension_changed = new_dimension is not None and new_dimension != current_dimension

    if dimension_changed:
        logger.info(
            f"[LLM Config] Dimension changed: {current_dimension} -> {new_dimension}, modifying database column"
        )
        result = await config_service.update_llm_config_with_dimension_change(
            update_data, new_dimension
        )
    else:
        await config_service.update_llm_config(update_data)
        result = {"message": "LLM configuration updated successfully"}

    # Clear cache to force refresh
    ConfigService.clear_cache()

    logger.info(f"LLM configuration updated by user {current_user.get('user_id')}")

    result = {"message": "LLM configuration updated successfully"}
    if dimension_changed:
        result["warning"] = (
            f"向量维度已从 {current_dimension} 变更为 {new_dimension}，现有向量数据已清空，请重新生成向量"
        )

    return result


@router.post(
    "/test-llm",
    response_model=TestLLMResponse,
    summary="测试对话模型连接",
    description="测试对话模型 API 连接是否正常",
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
        api_format = request.api_format or "openai"
        api_key = request.api_key
        api_base = request.api_base or ""
        model = request.model or ""
    else:
        config = await config_service.get_llm_config()
        if not config.enabled:
            return TestLLMResponse(
                success=False,
                message="对话模型未启用，请先启用对话模型功能",
            )
        api_format = config.api_format
        api_key = config.api_key
        api_base = config.api_base
        model = config.model

    if not api_key:
        return TestLLMResponse(
            success=False,
            message="API Key 未配置",
        )

    if not model:
        return TestLLMResponse(
            success=False,
            message="对话模型名称未配置",
        )

    # Test connection based on api_format
    try:
        return await _test_chat_model(api_key, api_base, model, api_format)
    except Exception as e:
        logger.error(f"LLM connection test failed: {e}")
        return TestLLMResponse(
            success=False,
            message=f"连接测试失败: {str(e)}",
        )


async def _test_chat_model(
    api_key: str,
    api_base: str,
    model: str,
    api_format: str,
) -> TestLLMResponse:
    """Test chat model connection."""
    from app.services.common.http_client import HttpClientFactory

    # Normalize API base URL (remove trailing slash to avoid double slashes)
    api_base = api_base.rstrip("/")

    logger.info(f"[Chat Test] Starting: api_format={api_format}, model={model}, base={api_base}")

    async with HttpClientFactory.create_client_for_url(api_base, timeout=30.0) as client:
        # Build endpoint URL
        if api_base.endswith("/v1"):
            chat_endpoint = f"{api_base}/chat/completions"
        else:
            chat_endpoint = f"{api_base}/v1/chat/completions"

        logger.debug(f"[Chat Test] Endpoint: {chat_endpoint}")

        # Build request body
        if api_format == "minimax":
            # MiniMax format
            request_body = {
                "model": model,
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 1,
            }
        else:
            # OpenAI format with response_format
            request_body = {
                "model": model,
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 1,
            }

        logger.debug(f"[Chat Test] Request body: {request_body}")

        # Build headers - only add Authorization if api_key is not empty
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        response = await client.post(
            chat_endpoint,
            headers=headers,
            json=request_body,
        )

        logger.info(f"[Chat Test] Response: status={response.status_code}")

        if response.status_code == 200:
            logger.info(f"[Chat Test] Success: model={model}")
            return TestLLMResponse(
                success=True,
                message=f"对话模型连接成功，模型: {model}",
                details={"api_format": api_format, "base_url": api_base, "model": model},
            )

        # Analyze error
        error_data = {}
        try:
            error_data = response.json()
        except Exception:
            # Response may not be JSON, continue with empty error_data
            logger.debug(f"[Chat Test] Non-JSON response: status={response.status_code}")

        error_msg = (
            error_data.get("error", {}).get("message", "")
            or error_data.get("message", "")
            or error_data.get("error_message", "")
        )

        logger.warning(
            f"[Chat Test] Failed: status={response.status_code}, error={error_msg or error_data}"
        )

        # 401 - API Key invalid
        if (
            response.status_code == 401
            or "unauthorized" in error_msg.lower()
            or "invalid" in error_msg.lower()
        ):
            return TestLLMResponse(
                success=False,
                message="API Key 无效或已过期",
            )

        # Model not found
        if "model" in error_msg.lower() or "not found" in error_msg.lower():
            return TestLLMResponse(
                success=False,
                message=f"模型 '{model}' 不存在，请检查模型名称",
                details={"error": error_msg},
            )

        return TestLLMResponse(
            success=False,
            message=f"API 错误: {error_msg or f'状态码 {response.status_code}'}",
        )


# ========== Embedding Test Endpoints ==========


@router.post(
    "/test-embedding",
    response_model=TestEmbeddingResponse,
    summary="测试嵌入模型连接",
    description="测试嵌入模型 API 连接是否正常",
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
        api_format = request.api_format or "openai"
        api_key = request.api_key
        api_base = request.api_base or ""
        embedding_model = request.embedding_model or ""
    else:
        config = await config_service.get_llm_config()
        if not config.embedding_enabled:
            return TestEmbeddingResponse(
                success=False,
                message="嵌入模型未启用，请先启用嵌入模型功能",
            )
        api_format = config.embedding_api_format or config.api_format
        api_key = config.embedding_api_key or ""  # 可以为空（本地部署）
        api_base = config.embedding_api_base
        embedding_model = config.embedding_model

    if not api_base:
        return TestEmbeddingResponse(
            success=False,
            message="嵌入 API 地址未配置，请配置嵌入模型的 API 地址",
        )

    if not embedding_model:
        return TestEmbeddingResponse(
            success=False,
            message="嵌入模型名称未配置，请先在系统配置中设置嵌入模型名称",
        )

    # Test embedding connection
    try:
        return await _test_embedding_model(api_key, api_base, embedding_model, api_format)
    except Exception as e:
        logger.error(f"Embedding connection test failed: {e}")
        return TestEmbeddingResponse(
            success=False,
            message=f"连接测试失败: {str(e)}",
        )


async def _test_embedding_model(
    api_key: str,
    api_base: str,
    embedding_model: str,
    api_format: str,
) -> TestEmbeddingResponse:
    """Test embedding model connection."""
    from app.services.common.http_client import HttpClientFactory

    if not api_base:
        return TestEmbeddingResponse(
            success=False,
            message="API Base URL 未配置",
        )

    # Normalize API base URL (remove trailing slash to avoid double slashes)
    api_base = api_base.rstrip("/")

    logger.info(
        f"[Embedding Test] Starting: api_format={api_format}, model={embedding_model}, base={api_base}"
    )

    async with HttpClientFactory.create_client_for_url(api_base, timeout=30.0) as client:
        # MiniMax uses different embedding API format
        if api_format == "minimax":
            # Ensure URL ends with /v1
            if not api_base.endswith("/v1"):
                api_base = api_base + "/v1"

            endpoint = f"{api_base}/embeddings"
            request_body = {
                "model": embedding_model or "embo-01",
                "texts": ["test"],
                "type": "db",
            }
            logger.debug(f"[Embedding Test] MiniMax endpoint: {endpoint}")
        else:
            # OpenAI-compatible embedding API
            endpoint = (
                f"{api_base}/embeddings"
                if api_base.endswith("/v1")
                else f"{api_base}/v1/embeddings"
            )
            request_body = {
                "model": embedding_model,
                "input": "test",
            }
            logger.debug(f"[Embedding Test] OpenAI endpoint: {endpoint}")

        logger.debug(f"[Embedding Test] Request body: {request_body}")

        # Build headers - only add Authorization if api_key is not empty
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        response = await client.post(
            endpoint,
            headers=headers,
            json=request_body,
        )

        logger.info(f"[Embedding Test] Response: status={response.status_code}")

        if response.status_code == 200:
            data = response.json()
            # Check if we got valid embedding
            embedding = None
            if "data" in data and len(data["data"]) > 0:
                embedding = data["data"][0].get("embedding", [])
            elif "vectors" in data and len(data["vectors"]) > 0:
                embedding = data["vectors"][0]

            if embedding and len(embedding) > 0:
                logger.info(
                    f"[Embedding Test] Success: model={embedding_model}, dimensions={len(embedding)}"
                )
                return TestEmbeddingResponse(
                    success=True,
                    message=f"嵌入模型连接成功，模型: {embedding_model}，向量维度: {len(embedding)}",
                    details={
                        "api_format": api_format,
                        "base_url": api_base,
                        "model": embedding_model,
                        "dimensions": len(embedding),
                    },
                )
            else:
                logger.warning(f"[Embedding Test] No embedding in response: {data}")
                return TestEmbeddingResponse(
                    success=False,
                    message="API 返回成功但未获取到有效向量",
                )

        # Analyze error
        error_data = {}
        try:
            error_data = response.json()
        except Exception:
            # Response may not be JSON, continue with empty error_data
            logger.debug(f"[Embedding Test] Non-JSON response: status={response.status_code}")

        error_msg = (
            error_data.get("error", {}).get("message", "")
            or error_data.get("message", "")
            or error_data.get("error_message", "")
            or error_data.get("base_resp", {}).get("status_msg", "")
        )

        logger.warning(
            f"[Embedding Test] Failed: status={response.status_code}, error={error_msg or error_data}"
        )

        # 401 - API Key invalid
        if response.status_code == 401 or "unauthorized" in str(error_data).lower():
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


# ========== Proxy Configuration Endpoints ==========


@router.get(
    "/proxy",
    response_model=ProxyConfigResponse,
    summary="获取代理配置",
    description="获取 HTTP 代理配置（密码已脱敏）",
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
        password_masked=(
            config_service.mask_sensitive_value("PROXY_PASSWORD", config.password)
            if config.password
            else ""
        ),
        no_proxy=config.no_proxy,
        ssl_verify=config.ssl_verify,
    )


@router.put(
    "/proxy",
    response_model=SuccessResponse,
    summary="更新代理配置",
    description="更新 HTTP 代理配置",
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
        logger.info(
            f"HttpClientFactory refreshed with proxy: {proxy_config.url}, no_proxy: {proxy_config.no_proxy}"
        )
    else:
        HttpClientFactory.configure()  # Reset to no proxy
        logger.info("HttpClientFactory reset to direct connection")

    logger.info(f"Proxy configuration updated by user {current_user.get('user_id')}")

    return SuccessResponse(message="Proxy configuration updated successfully")


@router.post(
    "/test-proxy",
    response_model=TestProxyResponse,
    summary="测试代理连接",
    description="测试代理服务器连接是否正常，同时验证 no_proxy 配置",
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
    from urllib.parse import urlparse, urlunparse

    import httpx

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
        full_proxy_url = urlunparse(
            (
                parsed.scheme,
                netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment,
            )
        )
    else:
        full_proxy_url = proxy_url

    results = []

    # Test 1: External API through proxy
    external_url = "https://api.openalex.org/works?per_page=1"
    try:
        async with httpx.AsyncClient(
            proxy=full_proxy_url, timeout=30.0, verify=ssl_verify, trust_env=False
        ) as client:
            response = await client.get(external_url)

            if response.status_code == 200:
                results.append(
                    {
                        "url": external_url,
                        "success": True,
                        "message": "External API accessible through proxy",
                        "used_proxy": True,
                    }
                )
            else:
                results.append(
                    {
                        "url": external_url,
                        "success": False,
                        "message": f"Proxy returned status {response.status_code}",
                        "used_proxy": True,
                    }
                )
    except httpx.ConnectError as e:
        results.append(
            {
                "url": external_url,
                "success": False,
                "message": f"Failed to connect to proxy: {str(e)}",
                "used_proxy": True,
            }
        )
    except httpx.ProxyError as e:
        results.append(
            {
                "url": external_url,
                "success": False,
                "message": f"Proxy error: {str(e)}",
                "used_proxy": True,
            }
        )
    except Exception as e:
        logger.error(f"External proxy test failed: {e}")
        results.append(
            {
                "url": external_url,
                "success": False,
                "message": f"Connection failed: {str(e)}",
                "used_proxy": True,
            }
        )

    # Test 2: Internal URL direct connection (if no_proxy configured)
    if no_proxy:
        # Try to extract an internal URL from no_proxy patterns
        # Or use the provided test_internal_url
        internal_url = request.test_internal_url if request else None

        # If no specific URL provided, try to infer from no_proxy patterns
        if not internal_url:
            # Parse no_proxy to find a testable URL
            patterns = [p.strip() for p in no_proxy.split(",") if p.strip()]
            for pattern in patterns:
                # Skip wildcards, look for concrete hostnames/IPs
                if "*" not in pattern and not pattern.startswith("."):
                    if pattern == "localhost":
                        internal_url = "http://localhost:8003/health"
                        break
                    elif pattern == "127.0.0.1":
                        internal_url = "http://127.0.0.1:8003/health"
                        break
                    # For IP patterns like 10.x.x.x, construct a test URL
                    elif pattern.replace(".", "").isdigit():
                        # This is an IP, try to use it
                        internal_url = f"http://{pattern}:8003/health"
                        break

        if internal_url:
            # Configure HttpClientFactory to check if URL should bypass proxy
            HttpClientFactory.configure(
                proxy_url=proxy_url,
                proxy_username=username,
                proxy_password=password,
                no_proxy=no_proxy,
            )

            HttpClientFactory.should_use_proxy(internal_url)

            try:
                # Test direct connection (no proxy for internal URLs)
                async with httpx.AsyncClient(timeout=10.0, trust_env=False) as client:
                    response = await client.get(internal_url)

                    if response.status_code in [200, 401, 403, 404]:
                        # Any valid HTTP response counts as success
                        results.append(
                            {
                                "url": internal_url,
                                "success": True,
                                "message": "Internal URL accessible directly (no_proxy matched)",
                                "used_proxy": False,
                            }
                        )
                    else:
                        results.append(
                            {
                                "url": internal_url,
                                "success": False,
                                "message": f"Internal URL returned status {response.status_code}",
                                "used_proxy": False,
                            }
                        )
            except httpx.ConnectError:
                # Connection refused is expected if service not running
                # Still counts as "no_proxy working" because we tried direct
                results.append(
                    {
                        "url": internal_url,
                        "success": True,
                        "message": "Direct connection attempted (no_proxy matched, service may not be running)",
                        "used_proxy": False,
                    }
                )
            except Exception as e:
                results.append(
                    {
                        "url": internal_url,
                        "success": True,
                        "message": f"Direct connection attempted: {str(e)[:50]}",
                        "used_proxy": False,
                    }
                )

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


# ========== GitHub Configuration Endpoints ==========


@router.get(
    "/github",
    response_model=GitHubConfigResponse,
    summary="获取 GitHub API 配置",
    description="获取 GitHub API 相关配置（Token 已脱敏）",
)
async def get_github_config(
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin_user),
):
    """Get GitHub API configuration."""
    config_service = ConfigService(session)
    config = await config_service.get_github_config()

    return GitHubConfigResponse(
        tokens_masked=(
            config_service.mask_sensitive_value("GITHUB_TOKENS", config.tokens)
            if config.tokens
            else ""
        ),
        base_url=config.base_url,
        rate_limit=config.rate_limit,
    )


@router.put("/github", response_model=dict, summary="更新 GitHub 配置", description="更新 GitHub API 相关配置")
async def update_github_config(
    request: GitHubConfigRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin_user),
):
    """Update GitHub API configuration."""
    config_service = ConfigService(session)

    update_data = {}
    if request.tokens is not None:
        update_data["tokens"] = request.tokens
    if request.base_url is not None:
        update_data["base_url"] = request.base_url
    if request.rate_limit is not None:
        update_data["rate_limit"] = request.rate_limit

    await config_service.update_github_config(update_data)
    ConfigService.clear_cache()

    logger.info(f"[GitHub Config] Updated by user {current_user.get('user_id')}")
    return {"message": "GitHub 配置已保存"}


@router.post("/github/test", response_model=TestGitHubResponse, summary="测试 GitHub API 连接")
async def test_github_connection(
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin_user),
):
    """Test GitHub API connection using configured tokens."""
    import httpx

    config_service = ConfigService(session)
    config = await config_service.get_github_config()

    if not config.tokens:
        return TestGitHubResponse(success=False, message="未配置 GitHub Token")

    tokens = [t.strip() for t in config.tokens.split(",") if t.strip()]
    if not tokens:
        return TestGitHubResponse(success=False, message="Token 格式无效")

    results = []
    for token in tokens:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{config.base_url}/rate_limit",
                    headers={"Authorization": f"Bearer {token}"},
                )
                if response.status_code == 200:
                    data = response.json()
                    rate = data.get("rate", {})
                    results.append({
                        "token_prefix": token[:8] + "****",
                        "success": True,
                        "limit": rate.get("limit", 0),
                        "remaining": rate.get("remaining", 0),
                    })
                elif response.status_code == 401:
                    results.append({
                        "token_prefix": token[:8] + "****",
                        "success": False,
                        "error": "Token 无效或已过期",
                    })
                else:
                    results.append({
                        "token_prefix": token[:8] + "****",
                        "success": False,
                        "error": f"HTTP {response.status_code}",
                    })
        except Exception as e:
            results.append({
                "token_prefix": token[:8] + "****",
                "success": False,
                "error": str(e),
            })

    success_count = sum(1 for r in results if r["success"])
    if success_count == len(tokens):
        return TestGitHubResponse(
            success=True,
            message=f"全部 {len(tokens)} 个 Token 测试通过",
            details={"results": results},
        )
    elif success_count > 0:
        return TestGitHubResponse(
            success=True,
            message=f"{success_count}/{len(tokens)} 个 Token 可用",
            details={"results": results},
        )
    else:
        return TestGitHubResponse(
            success=False,
            message="所有 Token 均无法连接 GitHub API",
            details={"results": results},
        )


# ========== Generic Configuration Endpoints ==========
# NOTE: Must be defined AFTER specific paths like /llm, /proxy
# to avoid route conflicts (FastAPI matches routes in order)


@router.put(
    "/{key}",
    response_model=SystemConfigItem,
    summary="更新单个配置项",
    description="更新指定配置项的值",
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

    config = await config_service.set_and_commit(key, request.value, config_type)

    # Clear cache for this key
    if key in ConfigService._cache:
        del ConfigService._cache[key]

    logger.info(f"Configuration {key} updated by user {current_user.get('user_id')}")

    return SystemConfigItem(
        key=config.config_key,
        value=config_service._coerce_value(config.config_value, config.config_type),
        display_value=(
            config_service.mask_sensitive_value(config.config_key, config.config_value or "")
            if config.is_sensitive
            else config.config_value
        ),
        type=config.config_type,
        is_sensitive=config.is_sensitive,
        description=config.description,
    )
