"""System configuration test service.

Extracted test logic from system_config API to reduce endpoint file size.
"""

from __future__ import annotations

import logging

from app.domains.shared.schemas.system_config import (
    TestEmbeddingResponse,
    TestGitHubResponse,
    TestLLMResponse,
    TestProxyResponse,
)
from app.domains.shared.services.common.http_client import HttpClientFactory

logger = logging.getLogger(__name__)


async def _test_embedding_model(
    api_key: str,
    api_base: str,
    embedding_model: str,
    api_format: str,
) -> TestEmbeddingResponse:
    """Test embedding model connection."""
    from app.domains.shared.services.common.http_client import HttpClientFactory

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


async def _test_chat_model(
    api_key: str,
    api_base: str,
    model: str,
    api_format: str,
) -> TestLLMResponse:
    """Test chat model connection."""
    from app.domains.shared.services.common.http_client import HttpClientFactory

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
            or error_data.get("base_resp", {}).get("status_msg", "")
        )

        logger.warning(
            f"[Chat Test] Failed: status={response.status_code}, error={error_msg or error_data}"
        )

        # 401 - API Key invalid
        if (
            response.status_code == 401
            or "unauthorized" in error_msg.lower()
            or "invalid" in error_msg.lower()
            or "login fail" in error_msg.lower()
        ):
            return TestLLMResponse(
                success=False,
                message=f"API Key 无效或认证失败: {error_msg or '请检查 API Key 是否正确'}".strip(),
                details={"error": error_msg} if error_msg else None,
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


# ========== Proxy Test ==========


async def _test_proxy_connection(
    proxy_url: str,
    username: str | None,
    password: str | None,
    no_proxy: str,
    ssl_verify: bool,
    test_internal_url: str | None = None,
) -> TestProxyResponse:
    """Test proxy connection (external + internal no_proxy)."""
    import httpx

    from app.core.config import settings

    # Configure Factory early so both external and internal tests use it
    HttpClientFactory.configure(
        proxy_url=proxy_url,
        proxy_username=username,
        proxy_password=password,
        no_proxy=no_proxy,
        ssl_verify=ssl_verify,
    )

    results = []

    # Test 1: External API through proxy
    openalex_base = settings.OPENALEX_BASE_URL or "https://api.openalex.org"
    external_url = f"{openalex_base}/works?per_page=1"
    try:
        async with HttpClientFactory.create_client_for_url(external_url, timeout=30.0) as client:
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
        internal_url = test_internal_url

        # If no specific URL provided, try to infer from no_proxy patterns
        if not internal_url:
            patterns = [p.strip() for p in no_proxy.split(",") if p.strip()]
            # Backend port: Docker = 8000, local dev = 8003 (from config)
            backend_port = "8003"
            for pattern in patterns:
                if "*" not in pattern and not pattern.startswith("."):
                    if pattern == "localhost":
                        internal_url = f"http://localhost:{backend_port}/health"
                        break
                    elif pattern == "127.0.0.1":
                        internal_url = f"http://127.0.0.1:{backend_port}/health"
                        break
                    elif pattern.replace(".", "").isdigit():
                        internal_url = f"http://{pattern}:{backend_port}/health"
                        break

        if internal_url:
            HttpClientFactory.should_use_proxy(internal_url)

            try:
                async with HttpClientFactory.create_client_for_url(
                    internal_url, timeout=10.0
                ) as client:
                    response = await client.get(internal_url)

                    if response.status_code in [200, 401, 403, 404]:
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


# ========== GitHub Test ==========


async def _test_github_connection(
    tokens: str,
    base_url: str,
) -> TestGitHubResponse:
    """Test GitHub API connection using configured tokens."""
    if not tokens:
        return TestGitHubResponse(success=False, message="未配置 GitHub Token")

    token_list = [t.strip() for t in tokens.split(",") if t.strip()]
    if not token_list:
        return TestGitHubResponse(success=False, message="Token 格式无效")

    results = []
    for token in token_list:
        try:
            async with HttpClientFactory.create_client_for_url(
                base_url, timeout=10, headers={"Authorization": f"Bearer {token}"}
            ) as client:
                response = await client.get(f"{base_url}/rate_limit")
                if response.status_code == 200:
                    data = response.json()
                    rate = data.get("rate", {})
                    results.append(
                        {
                            "token_prefix": token[:8] + "****",
                            "success": True,
                            "limit": rate.get("limit", 0),
                            "remaining": rate.get("remaining", 0),
                        }
                    )
                elif response.status_code == 401:
                    results.append(
                        {
                            "token_prefix": token[:8] + "****",
                            "success": False,
                            "error": "Token 无效或已过期",
                        }
                    )
                else:
                    results.append(
                        {
                            "token_prefix": token[:8] + "****",
                            "success": False,
                            "error": f"HTTP {response.status_code}",
                        }
                    )
        except Exception as e:
            results.append(
                {
                    "token_prefix": token[:8] + "****",
                    "success": False,
                    "error": str(e),
                }
            )

    success_count = sum(1 for r in results if r["success"])
    if success_count == len(token_list):
        return TestGitHubResponse(
            success=True,
            message=f"全部 {len(token_list)} 个 Token 测试通过",
            details={"results": results},
        )
    elif success_count > 0:
        return TestGitHubResponse(
            success=True,
            message=f"{success_count}/{len(token_list)} 个 Token 可用",
            details={"results": results},
        )
    else:
        return TestGitHubResponse(
            success=False,
            message="所有 Token 均无法连接 GitHub API",
            details={"results": results},
        )
