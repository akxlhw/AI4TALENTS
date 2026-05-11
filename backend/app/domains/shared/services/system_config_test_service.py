"""System configuration test service.

Extracted test logic from system_config API to reduce endpoint file size.
"""

from __future__ import annotations

import logging
import time

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


