"""LLM service module."""

from app.domains.shared.services.llm.errors import LLMError, LLMErrorType
from app.domains.shared.services.llm.llm_gateway import LLMGateway, create_llm_gateway
from app.domains.shared.services.llm.protocols import EmbeddingResult, JDFeatures, LLMGatewayProtocol
from app.domains.shared.services.llm.retry import with_retry, with_timeout

__all__ = [
    "LLMGatewayProtocol",
    "JDFeatures",
    "EmbeddingResult",
    "LLMError",
    "LLMErrorType",
    "LLMGateway",
    "create_llm_gateway",
    "with_retry",
    "with_timeout",
]
