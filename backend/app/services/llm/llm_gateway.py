"""
LLM Gateway implementation.
LLM 网关实现 - 支持 DeepSeek/OpenAI

Features:
- JD parsing
- Embedding generation
- Error handling with retry
- Fallback to rule-based parsing
- Proxy support for enterprise intranet
- Independent embedding API key support
"""

from __future__ import annotations

import json
import logging
import time
from typing import List, Optional, Any

import httpx
from openai import AsyncOpenAI, APIError, RateLimitError, APIConnectionError

from app.services.llm.protocols import LLMGatewayProtocol, JDFeatures, EmbeddingResult
from app.services.llm.errors import LLMError, LLMErrorType
from app.services.llm.retry import with_retry, with_timeout
from app.core.config import settings

logger = logging.getLogger(__name__)


# System prompt for JD parsing
# v1.4.1: Simplified to only output research_areas (English keywords)
JD_PARSE_PROMPT = """你是一个专业的招聘助手。请分析以下职位描述（JD），提取研究方向关键词。

请直接返回 JSON 格式，不要有任何分析过程或解释。

返回格式：
{
    "research_areas": ["area1", "area2", ...]
}

字段说明：
- research_areas: 学术研究领域，必须使用英文关键词，如 ["Natural Language Processing", "Computer Vision", "Deep Learning", "Machine Learning", "Speech Recognition", "Reinforcement Learning", "Generative AI", "Large Language Models"]

重要：research_areas 必须输出英文关键词，以便与学术数据库匹配。

直接返回 JSON 对象，从 { 开始，以 } 结束，不要有任何其他内容。"""


class LLMGateway(LLMGatewayProtocol):
    """LLM 网关实现

    支持 DeepSeek、OpenAI 等兼容 OpenAI API 的服务。
    支持企业内网代理访问（通过 HttpClientFactory 统一管理）。
    支持独立的嵌入 API Key 和地址。
    """

    def __init__(
        self,
        api_key: str | None = None,
        api_base: str | None = None,
        model: str | None = None,
        embedding_model: str | None = None,
        embedding_api_key: str | None = None,
        embedding_api_base: str | None = None,
        timeout: float | None = None,
        enable_fallback: bool = True,
        cache: Any = None,
    ):
        """
        初始化 LLM 网关

        Args:
            api_key: API 密钥
            api_base: API 基础 URL
            model: 聊天模型名称
            embedding_model: 嵌入模型名称
            embedding_api_key: 嵌入服务独立 API Key（可选，留空则使用 api_key）
            embedding_api_base: 嵌入服务独立 API 地址（可选）
            timeout: 超时时间（秒）
            enable_fallback: 是否启用降级策略
            cache: 缓存管理器
        """
        from app.services.common.http_client import HttpClientFactory

        self.api_key = api_key or settings.LLM_API_KEY
        self.api_base = api_base or settings.LLM_API_BASE
        self.model = model or settings.LLM_MODEL
        self.embedding_model = embedding_model or settings.LLM_EMBEDDING_MODEL
        self.embedding_api_key = embedding_api_key or ""
        self.embedding_api_base = embedding_api_base or ""
        self.timeout = timeout or settings.LLM_TIMEOUT
        self.enable_fallback = enable_fallback
        self.cache = cache

        # Provider name for logging/metrics
        self.provider = self._detect_provider()

        # Create HTTP client using factory (handles proxy/no_proxy automatically)
        http_client = HttpClientFactory.create_client_for_url(self.api_base, timeout=self.timeout)
        if HttpClientFactory.should_use_proxy(self.api_base):
            logger.info(f"LLM Gateway using proxy for: {self.api_base}")
        else:
            logger.info(f"LLM Gateway using direct connection for: {self.api_base}")

        # Initialize main OpenAI client
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.api_base,
            timeout=self.timeout,
            http_client=http_client,
        )

        # Initialize embedding client (may use different API key/base)
        if self.embedding_api_key or self.embedding_api_base:
            logger.info("LLM Gateway using separate embedding client")
            embedding_api_url = self.embedding_api_base or self.api_base

            # Create HTTP client for embedding API using factory
            embedding_http_client = HttpClientFactory.create_client_for_url(
                embedding_api_url, timeout=self.timeout
            )
            if HttpClientFactory.should_use_proxy(embedding_api_url):
                logger.info(f"Embedding client using proxy for: {embedding_api_url}")
            else:
                logger.info(f"Embedding client using direct connection for: {embedding_api_url}")

            self.embedding_client = AsyncOpenAI(
                api_key=self.embedding_api_key or self.api_key,
                base_url=self.embedding_api_base or self.api_base,
                timeout=self.timeout,
                http_client=embedding_http_client,
            )
        else:
            self.embedding_client = self.client

    def _detect_provider(self) -> str:
        """检测 LLM 提供商"""
        url_lower = self.api_base.lower()
        if "deepseek" in url_lower:
            return "deepseek"
        elif "openai" in url_lower:
            return "openai"
        elif "zhipu" in url_lower:
            return "zhipu"
        elif "dashscope" in url_lower or "qwen" in url_lower:
            return "qwen"
        elif "minimax" in url_lower:
            return "minimax"
        return "custom"

    @with_retry(max_retries=5)
    @with_timeout(timeout_seconds=60.0)
    async def parse_jd(self, jd_text: str) -> JDFeatures:
        """
        解析 JD 文本

        Args:
            jd_text: JD 文本内容

        Returns:
            JDFeatures: 解析出的特征

        Raises:
            LLMError: LLM API 调用失败
        """
        # 检查缓存
        if self.cache:
            cached = await self.cache.get_jd_features(jd_text)
            if cached:
                logger.debug(f"JD features cache hit for text hash")
                return cached

        try:
            start_time = time.time()

            # MiniMax 不支持 response_format 参数
            request_params = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": JD_PARSE_PROMPT},
                    {"role": "user", "content": jd_text}
                ],
                "temperature": 0.1,  # 低温度保证稳定性
            }

            # 只有非 MiniMax 提供商才使用 response_format
            if self.provider != "minimax":
                request_params["response_format"] = {"type": "json_object"}

            response = await self.client.chat.completions.create(**request_params)

            elapsed = time.time() - start_time
            logger.info(f"JD parsing completed in {elapsed:.2f}s")

            # 解析响应
            content = response.choices[0].message.content
            logger.info(f"LLM raw response (first 500 chars): {content[:500] if content else 'None'}")
            if not content:
                raise LLMError(
                    error_type=LLMErrorType.INVALID_RESPONSE,
                    message="Empty response from LLM"
                )

            # MiniMax 可能返回包含额外文本的响应，需要提取 JSON 部分
            if self.provider == "minimax":
                # 尝试找到 JSON 对象的开始和结束位置
                json_start = content.find('{')
                json_end = content.rfind('}')
                if json_start != -1 and json_end != -1 and json_end > json_start:
                    content = content[json_start:json_end + 1]
                    logger.info(f"Extracted JSON from MiniMax response: {content[:200]}...")
                else:
                    logger.warning(f"No JSON object found in MiniMax response")

            data = json.loads(content)
            logger.info(f"Parsed JSON data: {data}")
            features = JDFeatures.from_dict(data)

            # 写入缓存
            if self.cache:
                await self.cache.set_jd_features(jd_text, features)

            return features

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            if self.enable_fallback:
                return self._fallback_parse(jd_text)
            raise LLMError(
                error_type=LLMErrorType.INVALID_RESPONSE,
                message=f"Invalid JSON response: {e}"
            )

        except RateLimitError as e:
            logger.warning(f"Rate limit hit: {e}")
            raise LLMError(
                error_type=LLMErrorType.RATE_LIMIT,
                message="Rate limit exceeded",
                retry_after=getattr(e, 'retry_after', 60)
            )

        except APIConnectionError as e:
            logger.error(f"API connection error: {e}")
            raise LLMError(
                error_type=LLMErrorType.NETWORK_ERROR,
                message=str(e)
            )

        except APIError as e:
            # 检查是否是 529 服务过载错误
            status_code = getattr(e, 'status_code', None)
            if status_code == 529:
                logger.warning(f"Service overloaded (529), will retry: {e}")
                raise LLMError(
                    error_type=LLMErrorType.API_ERROR,
                    message=f"Service overloaded: {e}"
                )
            # 其他 API 错误
            logger.error(f"API error: {e}")
            raise LLMError(
                error_type=LLMErrorType.API_ERROR,
                message=str(e)
            )

        except LLMError:
            # 让 LLMError 继续向上传播给重试装饰器
            raise

        except Exception as e:
            logger.error(f"Unexpected error during JD parsing: {e}")
            raise LLMError(
                error_type=LLMErrorType.API_ERROR,
                message=f"Unexpected error: {e}"
            )

    async def parse_jd_with_fallback(self, jd_text: str) -> JDFeatures:
        """
        解析 JD 文本

        v1.4.1: 移除 fallback，如果 LLM 解析失败直接抛出错误给用户

        Args:
            jd_text: JD 文本内容

        Returns:
            JDFeatures: 解析出的特征

        Raises:
            LLMError: LLM API 调用失败
        """
        return await self.parse_jd(jd_text)

    @with_retry(max_retries=3)
    @with_timeout(timeout_seconds=60.0)
    async def generate_embedding(self, text: str) -> EmbeddingResult:
        """
        生成文本嵌入向量

        Args:
            text: 输入文本

        Returns:
            EmbeddingResult: 嵌入结果

        Raises:
            LLMError: LLM API 调用失败
        """
        try:
            start_time = time.time()

            # MiniMax 使用不同的 API 格式
            if self.provider == "minimax":
                results = await self._generate_embedding_batch_minimax([text])
                return results[0] if results else EmbeddingResult(
                    embedding=[],
                    model=self.embedding_model,
                    tokens_used=0
                )

            response = await self.embedding_client.embeddings.create(
                model=self.embedding_model,
                input=text,
            )

            elapsed = time.time() - start_time
            logger.debug(f"Embedding generated in {elapsed:.2f}s")

            embedding = response.data[0].embedding
            tokens_used = response.usage.total_tokens

            return EmbeddingResult(
                embedding=embedding,
                model=self.embedding_model,
                tokens_used=tokens_used
            )

        except RateLimitError as e:
            logger.warning(f"Rate limit hit during embedding: {e}")
            raise LLMError(
                error_type=LLMErrorType.RATE_LIMIT,
                message="Rate limit exceeded",
                retry_after=getattr(e, 'retry_after', 60)
            )

        except APIError as e:
            logger.error(f"API error during embedding: {e}")
            raise LLMError(
                error_type=LLMErrorType.API_ERROR,
                message=str(e)
            )

    @with_retry(max_retries=3)
    @with_timeout(timeout_seconds=120.0)
    async def generate_embedding_batch(self, texts: List[str]) -> List[EmbeddingResult]:
        """
        批量生成嵌入向量

        Args:
            texts: 文本列表

        Returns:
            List[EmbeddingResult]: 嵌入结果列表

        Raises:
            LLMError: LLM API 调用失败
        """
        if not texts:
            return []

        try:
            start_time = time.time()

            logger.info(f"Calling embedding API: model={self.embedding_model}, texts_count={len(texts)}, provider={self.provider}")

            # MiniMax 使用不同的 API 格式
            if self.provider == "minimax":
                logger.info("Using MiniMax-specific embedding API")
                return await self._generate_embedding_batch_minimax(texts)

            response = await self.embedding_client.embeddings.create(
                model=self.embedding_model,
                input=texts,
            )

            elapsed = time.time() - start_time
            logger.info(f"Batch embedding ({len(texts)} items) completed in {elapsed:.2f}s")
            logger.debug(f"Response data count: {len(response.data) if response.data else 0}")

            if not response.data:
                logger.error(f"Empty response from embedding API. Raw response: {response}")
                raise LLMError(
                    error_type=LLMErrorType.INVALID_RESPONSE,
                    message="No embedding data received from API"
                )

            results = []
            for i, item in enumerate(response.data):
                if not item.embedding:
                    logger.warning(f"Empty embedding at index {i}")
                    continue
                results.append(EmbeddingResult(
                    embedding=item.embedding,
                    model=self.embedding_model,
                    tokens_used=response.usage.total_tokens // len(texts)  # 平均
                ))

            return results

        except RateLimitError as e:
            logger.warning(f"Rate limit hit during batch embedding: {e}")
            raise LLMError(
                error_type=LLMErrorType.RATE_LIMIT,
                message="Rate limit exceeded",
                retry_after=getattr(e, 'retry_after', 60)
            )

        except APIError as e:
            logger.error(f"API error during batch embedding: {e}")
            raise LLMError(
                error_type=LLMErrorType.API_ERROR,
                message=str(e)
            )

    async def _generate_embedding_batch_minimax(self, texts: List[str]) -> List[EmbeddingResult]:
        """MiniMax 专用的嵌入生成方法

        性能优化说明：
        - MiniMax embo-01 模型支持每批最多 16 个文本
        - RPM 限制约 60，即每秒 1 个请求
        - 批次间延迟 1 秒足以满足速率限制
        """
        import asyncio

        start_time = time.time()

        # Determine the API key to use for embedding
        embedding_api_key = self.embedding_api_key or self.api_key

        # Create HTTP client with proxy if configured
        if self.proxy_url:
            client = httpx.AsyncClient(proxy=self.proxy_url, timeout=self.timeout)
        else:
            client = httpx.AsyncClient(timeout=self.timeout)

        # MiniMax 嵌入 API 使用不同的请求格式
        async with client:
            # MiniMax 的嵌入模型名称
            model = self.embedding_model
            if not model or model.lower() in ["minimax", "embo-01", "abab-embedding-001"]:
                # 默认使用 embo-01
                model = "embo-01"

            # MiniMax embo-01 支持：
            # - 每批最多 16 个文本（根据文本长度可能更少）
            # - RPM 约 60，即每秒 1 个请求
            max_batch_size = 16  # 提高批次大小
            batch_delay = 1.0    # 减少批次间延迟到 1 秒
            all_results = []

            for i in range(0, len(texts), max_batch_size):
                batch = texts[i:i + max_batch_size]
                batch_num = i // max_batch_size + 1
                total_batches = (len(texts) + max_batch_size - 1) // max_batch_size

                logger.info(f"MiniMax batch {batch_num}/{total_batches}: processing {len(batch)} texts")

                # 重试机制
                max_retries = 3
                for retry in range(max_retries):
                    try:
                        # MiniMax 嵌入 API 请求格式
                        response = await client.post(
                            f"{self.api_base}/embeddings",
                            headers={
                                "Authorization": f"Bearer {embedding_api_key}",
                                "Content-Type": "application/json",
                            },
                            json={
                                "model": model,
                                "texts": batch,
                                "type": "db",  # db 类型用于文档存储和检索
                            }
                        )

                        if response.status_code != 200:
                            error_text = response.text[:500]
                            logger.error(f"MiniMax API error: {response.status_code} - {error_text}")
                            if retry < max_retries - 1:
                                wait_time = 10 * (retry + 1)
                                logger.info(f"Retrying in {wait_time}s (attempt {retry + 2}/{max_retries})...")
                                await asyncio.sleep(wait_time)
                                continue
                            raise LLMError(
                                error_type=LLMErrorType.API_ERROR,
                                message=f"MiniMax API error: {response.status_code}"
                            )

                        data = response.json()

                        # MiniMax 返回格式: {"vectors": [[...], ...], "total_tokens": 123, "base_resp": {...}}
                        if "vectors" not in data or not data["vectors"]:
                            base_resp = data.get("base_resp", {})
                            status_msg = base_resp.get("status_msg", "Unknown error")

                            # 如果是速率限制错误，等待后重试
                            if "rate limit" in status_msg.lower():
                                logger.warning(f"Rate limit hit: {status_msg}")
                                if retry < max_retries - 1:
                                    wait_time = 30 * (retry + 1)  # 30s, 60s, 90s
                                    logger.info(f"Waiting {wait_time}s before retry (attempt {retry + 2}/{max_retries})...")
                                    await asyncio.sleep(wait_time)
                                    continue
                                else:
                                    logger.error(f"Max retries reached for batch {batch_num}")
                                    raise LLMError(
                                        error_type=LLMErrorType.RATE_LIMIT,
                                        message=f"MiniMax rate limit exceeded after {max_retries} retries"
                                    )
                            else:
                                logger.error(f"MiniMax returned no vectors: {status_msg}")
                                raise LLMError(
                                    error_type=LLMErrorType.INVALID_RESPONSE,
                                    message=f"MiniMax API error: {status_msg}"
                                )

                        # 成功获取向量
                        vectors = data["vectors"]
                        total_tokens = data.get("total_tokens", 0)

                        # 验证向量数量与请求数量一致
                        if len(vectors) != len(batch):
                            logger.error(
                                f"MiniMax returned {len(vectors)} vectors for {len(batch)} texts. "
                                f"This may cause data mismatch!"
                            )
                            # 如果向量数量不对，视为失败，重试
                            if retry < max_retries - 1:
                                wait_time = 10 * (retry + 1)
                                logger.info(f"Retrying due to vector count mismatch (attempt {retry + 2}/{max_retries})...")
                                await asyncio.sleep(wait_time)
                                continue
                            else:
                                raise LLMError(
                                    error_type=LLMErrorType.INVALID_RESPONSE,
                                    message=f"MiniMax returned {len(vectors)} vectors for {len(batch)} texts"
                                )

                        for j, vector in enumerate(vectors):
                            all_results.append(EmbeddingResult(
                                embedding=vector,
                                model=model,
                                tokens_used=total_tokens // len(batch) if batch else 0
                            ))

                        logger.info(f"MiniMax batch {batch_num}/{total_batches} success: {len(vectors)} vectors")
                        break  # 成功，跳出重试循环

                    except LLMError:
                        raise
                    except Exception as e:
                        logger.error(f"Unexpected error in batch {batch_num}: {e}")
                        if retry < max_retries - 1:
                            await asyncio.sleep(10)
                            continue
                        raise

                # 批次间增加延迟，避免速率限制
                if i + max_batch_size < len(texts):
                    logger.debug(f"Waiting {batch_delay}s before next batch...")
                    await asyncio.sleep(batch_delay)

            elapsed = time.time() - start_time
            logger.info(f"MiniMax embedding completed: {len(texts)} items in {elapsed:.2f}s")

            return all_results

    async def health_check(self) -> bool:
        """
        健康检查

        Returns:
            bool: 服务是否健康
        """
        try:
            # 简单的模型列表请求来检查连接
            await self.client.models.list()
            return True
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False


def create_llm_gateway(
    provider: str | None = None,
    api_key: str | None = None,
    api_base: str | None = None,
    embedding_api_key: str | None = None,
    embedding_api_base: str | None = None,
    **kwargs
) -> LLMGateway | None:
    """
    工厂函数：创建 LLM 网关

    注意：代理配置由 HttpClientFactory 全局管理，在应用启动时配置。

    Args:
        provider: 提供商名称
        api_key: API 密钥
        api_base: API 基础 URL
        embedding_api_key: 嵌入服务独立 API Key
        embedding_api_base: 嵌入服务独立 API 地址
        **kwargs: 其他参数

    Returns:
        LLMGateway | None: LLM 网关实例，如果未配置则返回 None
    """
    # 检查是否启用 LLM
    if not settings.LLM_ENABLED and not api_key:
        logger.info("LLM features are disabled")
        return None

    # 使用配置或参数
    final_api_key = api_key or settings.LLM_API_KEY
    if not final_api_key:
        logger.warning("No LLM API key configured")
        return None

    return LLMGateway(
        api_key=final_api_key,
        api_base=api_base or settings.LLM_API_BASE,
        model=kwargs.get('model') or settings.LLM_MODEL,
        embedding_model=kwargs.get('embedding_model') or settings.LLM_EMBEDDING_MODEL,
        embedding_api_key=embedding_api_key,
        embedding_api_base=embedding_api_base,
        timeout=kwargs.get('timeout') or settings.LLM_TIMEOUT,
        enable_fallback=kwargs.get('enable_fallback', settings.LLM_ENABLE_FALLBACK),
    )
