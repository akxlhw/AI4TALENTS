"""
LLM Error types and handling.
LLM 错误类型定义
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional


class LLMErrorType(Enum):
    """LLM 错误类型"""
    TIMEOUT = "timeout"                    # API 超时
    RATE_LIMIT = "rate_limit"              # 触发速率限制
    API_ERROR = "api_error"                # API 错误
    INVALID_RESPONSE = "invalid_response"  # 响应格式错误
    AUTH_ERROR = "auth_error"              # 认证错误
    MODEL_NOT_FOUND = "model_not_found"    # 模型不存在
    CONTENT_FILTER = "content_filter"      # 内容过滤
    NETWORK_ERROR = "network_error"        # 网络错误


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
    retry_after: Optional[int] = None
    original_error: Optional[Exception] = None

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


class SearchError(Exception):
    """搜索错误基类"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class EmptyQueryError(SearchError):
    """空查询错误"""

    def __init__(self):
        super().__init__("搜索关键词不能为空")


class InvalidSearchModeError(SearchError):
    """无效搜索模式错误"""

    def __init__(self, mode: str):
        super().__init__(f"无效的搜索模式: {mode}")


class EmbeddingError(Exception):
    """嵌入错误基类"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class TalentNotFoundError(EmbeddingError):
    """人才不存在错误"""

    def __init__(self, talent_id: int):
        super().__init__(f"人才不存在: {talent_id}")


class JDMatchError(Exception):
    """岗位匹配错误基类"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class EmptyJDError(JDMatchError):
    """空 JD 错误"""

    def __init__(self):
        super().__init__("JD 文本不能为空")


class RecommendError(Exception):
    """推荐错误基类"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class InvalidReferenceError(RecommendError):
    """无效参考人才错误"""

    def __init__(self, talent_id: int):
        super().__init__(f"参考人才不存在: {talent_id}")


class EmptyReferenceError(RecommendError):
    """空参考列表错误"""

    def __init__(self):
        super().__init__("参考人才列表不能为空")


# ========================================
# 搜索相关异常 (Search-specific errors)
# ========================================

class SemanticSearchError(SearchError):
    """语义搜索失败错误"""

    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.original_error = original_error


class FulltextSearchError(SearchError):
    """全文搜索失败错误"""

    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.original_error = original_error


class VectorParseError(SearchError):
    """向量解析失败错误"""

    def __init__(self, message: str = "向量格式解析失败"):
        super().__init__(message)


class EmbeddingServiceError(SearchError):
    """嵌入服务错误"""

    def __init__(self, message: str = "嵌入服务不可用"):
        super().__init__(message)
