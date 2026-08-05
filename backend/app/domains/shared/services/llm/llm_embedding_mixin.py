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

import asyncio
import logging
import time

from app.core.config import settings
from app.domains.shared.services.llm.errors import (
    LLMError,
    LLMErrorType,
    llm_error_from_exception,
)
from app.domains.shared.services.llm.protocols import (
    EmbeddingResult,
)
from app.domains.shared.services.llm.retry import with_retry

logger = logging.getLogger(__name__)


class LLMEmbeddingMixin:
    """Embedding generation mixin for LLM Gateway."""

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
        if not self.embedding_client:
            raise LLMError(
                LLMErrorType.CONFIG_ERROR, "嵌入模型未配置。请配置嵌入 API Key 和 API 地址。"
            )

        try:
            start_time = time.time()

            # MiniMax 使用不同的 API 格式
            if self.embedding_api_format == "minimax":
                results = await self._generate_embedding_batch_minimax([text])
                return (
                    results[0]
                    if results
                    else EmbeddingResult(embedding=[], model=self.embedding_model, tokens_used=0)
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
                embedding=embedding, model=self.embedding_model, tokens_used=tokens_used
            )

        except LLMError:
            raise

        except Exception as e:
            # 底层 SDK 异常统一转换为领域异常（唯一转换点见 errors.py）
            converted = llm_error_from_exception(e)
            if converted.error_type == LLMErrorType.RATE_LIMIT:
                logger.warning(f"Rate limit hit during embedding: {e}")
            else:
                logger.error(f"API error during embedding: {e}")
            raise converted from e

    @with_retry(max_retries=settings.LLM_MAX_RETRIES)
    async def generate_embedding_batch(self, texts: list[str]) -> list[EmbeddingResult]:
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

        if not self.embedding_client:
            raise LLMError(
                LLMErrorType.CONFIG_ERROR, "嵌入模型未配置。请配置嵌入 API Key 和 API 地址。"
            )

        # 动态超时：每条 2 秒，最少 LLM_TIMEOUT 秒
        timeout_seconds = max(settings.LLM_TIMEOUT, len(texts) * 2.0)

        try:
            start_time = time.time()

            logger.info(
                f"Calling embedding API: model={self.embedding_model}, texts_count={len(texts)}, api_format={self.embedding_api_format}, timeout={timeout_seconds}s"
            )

            # MiniMax 使用不同的 API 格式
            if self.embedding_api_format == "minimax":
                logger.info("Using MiniMax-specific embedding API")
                return await asyncio.wait_for(
                    self._generate_embedding_batch_minimax(texts),
                    timeout=timeout_seconds,
                )

            response = await asyncio.wait_for(
                self.embedding_client.embeddings.create(
                    model=self.embedding_model,
                    input=texts,
                ),
                timeout=timeout_seconds,
            )

            elapsed = time.time() - start_time
            logger.info(f"Batch embedding ({len(texts)} items) completed in {elapsed:.2f}s")
            logger.debug(f"Response data count: {len(response.data) if response.data else 0}")

            if not response.data:
                logger.error(f"Empty response from embedding API. Raw response: {response}")
                raise LLMError(
                    error_type=LLMErrorType.INVALID_RESPONSE,
                    message="No embedding data received from API",
                )

            results = []
            for i, item in enumerate(response.data):
                if not item.embedding:
                    logger.warning(f"Empty embedding at index {i}")
                    continue
                results.append(
                    EmbeddingResult(
                        embedding=item.embedding,
                        model=self.embedding_model,
                        tokens_used=response.usage.total_tokens // len(texts),  # 平均
                    )
                )

            return results

        except TimeoutError:
            raise LLMError(
                error_type=LLMErrorType.TIMEOUT,
                message=f"LLM API 超时 ({timeout_seconds}s)",
            ) from None

        except LLMError:
            raise

        except Exception as e:
            # 底层 SDK 异常统一转换为领域异常（唯一转换点见 errors.py）
            converted = llm_error_from_exception(e)
            if converted.error_type == LLMErrorType.RATE_LIMIT:
                logger.warning(f"Rate limit hit during batch embedding: {e}")
            else:
                logger.error(f"API error during batch embedding: {e}")
            raise converted from e

    async def _generate_embedding_batch_minimax(self, texts: list[str]) -> list[EmbeddingResult]:
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

        # Create HTTP client using factory (handles proxy/no_proxy automatically)
        from app.domains.shared.services.common.http_client import HttpClientFactory

        embedding_api_url = self.api_base
        client = HttpClientFactory.create_client_for_url(embedding_api_url, timeout=self.timeout)

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
            max_batch_size = settings.LLM_MAX_BATCH_SIZE
            batch_delay = 1.0  # 减少批次间延迟到 1 秒
            all_results = []

            for i in range(0, len(texts), max_batch_size):
                batch = texts[i : i + max_batch_size]
                batch_num = i // max_batch_size + 1
                total_batches = (len(texts) + max_batch_size - 1) // max_batch_size

                logger.info(
                    f"MiniMax batch {batch_num}/{total_batches}: processing {len(batch)} texts"
                )

                # 重试机制
                max_retries = settings.LLM_MAX_RETRIES
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
                            },
                        )

                        if response.status_code != 200:
                            error_text = response.text[:500]
                            logger.error(
                                f"MiniMax API error: {response.status_code} - {error_text}"
                            )
                            if retry < max_retries - 1:
                                wait_time = 10 * (retry + 1)
                                logger.info(
                                    f"Retrying in {wait_time}s (attempt {retry + 2}/{max_retries})..."
                                )
                                await asyncio.sleep(wait_time)
                                continue
                            raise LLMError(
                                error_type=LLMErrorType.API_ERROR,
                                message=f"MiniMax API error: {response.status_code}",
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
                                    logger.info(
                                        f"Waiting {wait_time}s before retry (attempt {retry + 2}/{max_retries})..."
                                    )
                                    await asyncio.sleep(wait_time)
                                    continue
                                else:
                                    logger.error(f"Max retries reached for batch {batch_num}")
                                    raise LLMError(
                                        error_type=LLMErrorType.RATE_LIMIT,
                                        message=f"MiniMax rate limit exceeded after {max_retries} retries",
                                    )
                            else:
                                logger.error(f"MiniMax returned no vectors: {status_msg}")
                                raise LLMError(
                                    error_type=LLMErrorType.INVALID_RESPONSE,
                                    message=f"MiniMax API error: {status_msg}",
                                )

                        # 成功获取向量
                        vectors = data["vectors"]
                        total_tokens = data.get("total_tokens", 0)

                        if len(vectors) != len(batch):
                            logger.error(
                                f"MiniMax returned {len(vectors)} vectors for {len(batch)} texts. "
                                f"This may cause data mismatch!"
                            )
                            # 如果向量数量不对，视为失败，重试
                            if retry < max_retries - 1:
                                wait_time = 10 * (retry + 1)
                                logger.info(
                                    f"Retrying due to vector count mismatch (attempt {retry + 2}/{max_retries})..."
                                )
                                await asyncio.sleep(wait_time)
                                continue
                            else:
                                raise LLMError(
                                    error_type=LLMErrorType.INVALID_RESPONSE,
                                    message=f"MiniMax returned {len(vectors)} vectors for {len(batch)} texts",
                                )

                        for _j, vector in enumerate(vectors):
                            all_results.append(
                                EmbeddingResult(
                                    embedding=vector,
                                    model=model,
                                    tokens_used=total_tokens // len(batch) if batch else 0,
                                )
                            )

                        logger.info(
                            f"MiniMax batch {batch_num}/{total_batches} success: {len(vectors)} vectors"
                        )
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
