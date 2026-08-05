"""
LLM Error types and handling.
LLM 错误类型定义

错误处理契约：LLM 调用链内部只 raise `LLMError`，底层 SDK 异常统一经
`llm_error_from_exception` 转换；边界处（health probe / API 层）再统一
转换为布尔或 HTTP 响应，禁止布尔/元组/字符串状态码作为错误通道。
"""

from dataclasses import dataclass
from enum import Enum

from openai import APIConnectionError, APIError, RateLimitError

# Default wait (seconds) when a rate-limit error carries no retry-after hint
DEFAULT_RATE_LIMIT_RETRY_AFTER = 60

# Upstream service overloaded HTTP status (e.g. DeepSeek 529)
HTTP_STATUS_SERVICE_OVERLOADED = 529


class LLMErrorType(Enum):
    """LLM 错误类型"""

    TIMEOUT = "timeout"  # API 超时
    RATE_LIMIT = "rate_limit"  # 触发速率限制
    API_ERROR = "api_error"  # API 错误
    INVALID_RESPONSE = "invalid_response"  # 响应格式错误
    AUTH_ERROR = "auth_error"  # 认证错误
    MODEL_NOT_FOUND = "model_not_found"  # 模型不存在
    CONTENT_FILTER = "content_filter"  # 内容过滤
    NETWORK_ERROR = "network_error"  # 网络错误
    CONFIG_ERROR = "config_error"  # 配置缺失（如嵌入服务未配置）


@dataclass
class LLMError(Exception):
    """LLM 错误

    Attributes:
        error_type: 错误类型
        message: 错误信息
        retry_after: 重试等待时间（秒），仅对 RATE_LIMIT 有效
        original_error: 原始异常
    """

    error_type: LLMErrorType
    message: str
    retry_after: int | None = None
    original_error: Exception | None = None

    def __str__(self) -> str:
        if self.retry_after:
            return f"[{self.error_type.value}] {self.message} (retry_after={self.retry_after}s)"
        return f"[{self.error_type.value}] {self.message}"

    def is_retryable(self) -> bool:
        """错误是否可重试"""
        return self.error_type in (
            LLMErrorType.TIMEOUT,
            LLMErrorType.RATE_LIMIT,
            LLMErrorType.NETWORK_ERROR,
            LLMErrorType.API_ERROR,
        )


def llm_error_from_exception(exc: Exception) -> LLMError:
    """统一将底层 SDK 异常转换为领域异常 LLMError（唯一转换点）。

    LLM 调用方一律 raise 本函数产出的 LLMError，由边界处统一转换，
    禁止以布尔/元组/字符串状态码传递错误。
    """
    if isinstance(exc, LLMError):
        return exc
    if isinstance(exc, RateLimitError):
        return LLMError(
            error_type=LLMErrorType.RATE_LIMIT,
            message="Rate limit exceeded",
            retry_after=getattr(exc, "retry_after", DEFAULT_RATE_LIMIT_RETRY_AFTER),
            original_error=exc,
        )
    if isinstance(exc, APIConnectionError):
        return LLMError(error_type=LLMErrorType.NETWORK_ERROR, message=str(exc), original_error=exc)
    if isinstance(exc, APIError):
        status_code = getattr(exc, "status_code", None)
        if status_code == HTTP_STATUS_SERVICE_OVERLOADED:
            return LLMError(
                error_type=LLMErrorType.API_ERROR,
                message=f"Service overloaded: {exc}",
                original_error=exc,
            )
        return LLMError(error_type=LLMErrorType.API_ERROR, message=str(exc), original_error=exc)
    return LLMError(
        error_type=LLMErrorType.API_ERROR,
        message=f"Unexpected error: {exc}",
        original_error=exc,
    )


class SearchError(Exception):
    """搜索错误基类"""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class EmptyQueryError(SearchError):
    """空查询错误"""

    def __init__(self) -> None:
        super().__init__("搜索关键词不能为空")


class InvalidSearchModeError(SearchError):
    """无效搜索模式错误"""

    def __init__(self, mode: str) -> None:
        super().__init__(f"无效的搜索模式: {mode}")


class EmbeddingError(Exception):
    """嵌入错误基类"""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class TalentNotFoundError(EmbeddingError):
    """人才不存在错误"""

    def __init__(self, talent_id: int) -> None:
        super().__init__(f"人才不存在: {talent_id}")


class JDMatchError(Exception):
    """岗位匹配错误基类"""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class EmptyJDError(JDMatchError):
    """空 JD 错误"""

    def __init__(self) -> None:
        super().__init__("JD 文本不能为空")


class RecommendError(Exception):
    """推荐错误基类"""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class InvalidReferenceError(RecommendError):
    """无效参考人才错误"""

    def __init__(self, talent_id: int) -> None:
        super().__init__(f"参考人才不存在: {talent_id}")


class EmptyReferenceError(RecommendError):
    """空参考列表错误"""

    def __init__(self) -> None:
        super().__init__("参考人才列表不能为空")


# ========================================
# 搜索相关异常 (Search-specific errors)
# ========================================


class SemanticSearchError(SearchError):
    """语义搜索失败错误"""

    def __init__(self, message: str, original_error: Exception | None = None) -> None:
        super().__init__(message)
        self.original_error = original_error


class FulltextSearchError(SearchError):
    """全文搜索失败错误"""

    def __init__(self, message: str, original_error: Exception | None = None) -> None:
        super().__init__(message)
        self.original_error = original_error


class VectorParseError(SearchError):
    """向量解析失败错误"""

    def __init__(self, message: str = "向量格式解析失败") -> None:
        super().__init__(message)


class EmbeddingServiceError(SearchError):
    """嵌入服务错误"""

    def __init__(self, message: str = "嵌入服务不可用") -> None:
        super().__init__(message)
