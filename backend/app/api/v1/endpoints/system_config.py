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
    SystemConfigItem,
    SystemConfigListResponse,
    TestLLMRequest,
    TestLLMResponse,
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

    if not api_key:
        return TestLLMResponse(
            success=False,
            message="API key is required",
        )

    # Test connection based on provider
    try:
        if provider == "deepseek":
            return await _test_deepseek(api_key, api_base)
        elif provider == "openai":
            return await _test_openai(api_key, api_base)
        elif provider == "zhipu":
            return await _test_zhipu(api_key, api_base)
        elif provider == "qwen":
            return await _test_qwen(api_key, api_base)
        elif provider == "minimax":
            return await _test_minimax(api_key, api_base)
        else:
            # Generic test for custom providers
            return await _test_generic(api_key, api_base)
    except Exception as e:
        logger.error(f"LLM connection test failed: {e}")
        return TestLLMResponse(
            success=False,
            message=f"Connection test failed: {str(e)}",
        )


async def _test_deepseek(api_key: str, api_base: str) -> TestLLMResponse:
    """Test DeepSeek API connection."""
    import httpx

    base_url = api_base or "https://api.deepseek.com"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{base_url}/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
        )

        if response.status_code == 200:
            return TestLLMResponse(
                success=True,
                message="DeepSeek API connection successful",
                details={"provider": "deepseek", "base_url": base_url},
            )
        else:
            return TestLLMResponse(
                success=False,
                message=f"DeepSeek API returned status {response.status_code}",
            )


async def _test_openai(api_key: str, api_base: str) -> TestLLMResponse:
    """Test OpenAI API connection."""
    import httpx

    base_url = api_base or "https://api.openai.com"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{base_url}/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
        )

        if response.status_code == 200:
            return TestLLMResponse(
                success=True,
                message="OpenAI API connection successful",
                details={"provider": "openai", "base_url": base_url},
            )
        else:
            return TestLLMResponse(
                success=False,
                message=f"OpenAI API returned status {response.status_code}",
            )


async def _test_zhipu(api_key: str, api_base: str) -> TestLLMResponse:
    """Test Zhipu AI API connection."""
    # Zhipu uses JWT token, simplified test
    return TestLLMResponse(
        success=True,
        message="Zhipu AI configuration saved (connection test not implemented)",
        details={"provider": "zhipu"},
    )


async def _test_qwen(api_key: str, api_base: str) -> TestLLMResponse:
    """Test Qwen (Alibaba Tongyi) API connection."""
    import httpx

    base_url = api_base or "https://dashscope.aliyuncs.com"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{base_url}/api/v1/services/aigc/text-generation/generation",
            headers={"Authorization": f"Bearer {api_key}"},
        )

        # Qwen API may return different status codes
        if response.status_code in [200, 400]:
            return TestLLMResponse(
                success=True,
                message="Qwen API connection successful",
                details={"provider": "qwen", "base_url": base_url},
            )
        else:
            return TestLLMResponse(
                success=False,
                message=f"Qwen API returned status {response.status_code}",
            )


async def _test_minimax(api_key: str, api_base: str) -> TestLLMResponse:
    """Test MiniMax API connection."""
    import httpx

    # MiniMax API base URL
    base_url = api_base or "https://api.minimax.chat/v1"

    # 确保 URL 以 /v1 结尾
    if not base_url.endswith("/v1"):
        base_url = base_url.rstrip("/") + "/v1"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # MiniMax 使用 chat/completions 测试连接
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "abab6.5s-chat",
                    "messages": [{"role": "user", "content": "hi"}],
                    "max_tokens": 1,
                },
            )

            if response.status_code == 200:
                return TestLLMResponse(
                    success=True,
                    message="MiniMax API 连接成功",
                    details={"provider": "minimax", "base_url": base_url},
                )
            elif response.status_code == 401:
                return TestLLMResponse(
                    success=False,
                    message="MiniMax API Key 无效",
                )
            else:
                return TestLLMResponse(
                    success=False,
                    message=f"MiniMax API 返回状态码 {response.status_code}: {response.text[:200]}",
                )
        except httpx.ConnectError as e:
            return TestLLMResponse(
                success=False,
                message=f"无法连接到 MiniMax API: {str(e)}",
            )
        except Exception as e:
            return TestLLMResponse(
                success=False,
                message=f"连接测试失败: {str(e)}",
            )


async def _test_generic(api_key: str, api_base: str) -> TestLLMResponse:
    """Generic API connection test."""
    if not api_base:
        return TestLLMResponse(
            success=False,
            message="API base URL is required for custom providers",
        )

    import httpx

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                f"{api_base}/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )

            if response.status_code == 200:
                return TestLLMResponse(
                    success=True,
                    message="Custom API connection successful",
                    details={"base_url": api_base},
                )
            else:
                return TestLLMResponse(
                    success=False,
                    message=f"API returned status {response.status_code}",
                )
        except Exception as e:
            return TestLLMResponse(
                success=False,
                message=f"Connection failed: {str(e)}",
            )
