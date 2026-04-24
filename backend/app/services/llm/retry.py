"""
LLM Retry decorator.
LLM 重试装饰器 - 指数退避重试策略
"""

import asyncio
import logging
from functools import wraps
from typing import Callable, TypeVar, ParamSpec, Awaitable

from app.services.llm.errors import LLMError, LLMErrorType

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    retryable_errors: tuple = (LLMError,)
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """指数退避重试装饰器

    Args:
        max_retries: 最大重试次数
        base_delay: 基础延迟（秒）
        max_delay: 最大延迟（秒）
        exponential_base: 指数基数
        retryable_errors: 可重试的错误类型

    Returns:
        装饰后的函数

    Example:
        @with_retry(max_retries=3)
        async def call_llm():
            ...
    """
    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_error: Exception | None = None

            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)

                except retryable_errors as e:
                    last_error = e

                    if isinstance(e, LLMError):
                        # 检查是否可重试
                        if not e.is_retryable():
                            raise

                        # 计算延迟
                        if e.error_type == LLMErrorType.RATE_LIMIT and e.retry_after:
                            delay = float(e.retry_after)
                        else:
                            delay = min(
                                base_delay * (exponential_base ** attempt),
                                max_delay
                            )

                        if attempt < max_retries - 1:
                            logger.warning(
                                f"LLM call failed (attempt {attempt + 1}/{max_retries}): {e}. "
                                f"Retrying in {delay:.1f}s..."
                            )
                            await asyncio.sleep(delay)
                    else:
                        if attempt < max_retries - 1:
                            delay = min(
                                base_delay * (exponential_base ** attempt),
                                max_delay
                            )
                            logger.warning(
                                f"Call failed (attempt {attempt + 1}/{max_retries}). "
                                f"Retrying in {delay:.1f}s..."
                            )
                            await asyncio.sleep(delay)

                except Exception as e:
                    # 非预期错误，不重试
                    raise

            # 所有重试都失败
            if last_error:
                raise last_error

            # 不应该到达这里
            raise RuntimeError("Unexpected state in retry logic")

        return wrapper
    return decorator


def with_timeout(timeout_seconds: float = 30.0) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """超时装饰器

    Args:
        timeout_seconds: 超时时间（秒）

    Returns:
        装饰后的函数
    """
    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                raise LLMError(
                    error_type=LLMErrorType.TIMEOUT,
                    message=f"LLM API 超时 ({timeout_seconds}s)"
                )
        return wrapper
    return decorator
