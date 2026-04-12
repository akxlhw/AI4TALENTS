"""LLM service module."""
from app.services.llm.protocols import LLMGatewayProtocol, JDFeatures, EmbeddingResult
from app.services.llm.errors import LLMError, LLMErrorType
from app.services.llm.llm_gateway import LLMGateway, create_llm_gateway
from app.services.llm.retry import with_retry, with_timeout

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
