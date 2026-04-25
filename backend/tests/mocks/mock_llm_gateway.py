"""
Mock LLM Gateway for testing.
Mock LLM 网关实现，用于单元测试

v1.4.1: Simplified to only output research_areas
"""

from dataclasses import dataclass


@dataclass
class JDFeatures:
    """JD 解析结果

    v1.4.1: Simplified to only output research_areas
    """

    research_areas: list[str]


@dataclass
class EmbeddingResult:
    """嵌入生成结果"""

    embedding: list[float]
    model: str
    tokens_used: int


class MockLLMGateway:
    """Mock LLM 网关，用于单元测试

    实现与 LLMGatewayProtocol 相同的接口，返回预设的测试数据。
    """

    def __init__(
        self,
        jd_features: JDFeatures | None = None,
        embedding: list[float] | None = None,
        should_fail: bool = False,
        fail_count: int = 0,
    ):
        """初始化 Mock

        Args:
            jd_features: 预设的 JD 解析结果
            embedding: 预设的嵌入向量
            should_fail: 是否模拟失败
            fail_count: 失败次数（用于测试重试）
        """
        self._jd_features = jd_features or JDFeatures(
            research_areas=["Natural Language Processing", "Deep Learning", "Machine Learning"]
        )
        self._embedding = embedding or [0.1] * 1536
        self._should_fail = should_fail
        self._fail_count = fail_count
        self._current_fail_count = 0
        self._call_count = 0

    async def parse_jd(self, jd_text: str) -> JDFeatures:
        """解析 JD 文本

        Args:
            jd_text: JD 文本内容

        Returns:
            JDFeatures: 解析出的特征

        Raises:
            Exception: 如果 should_fail=True
        """
        self._call_count += 1

        if self._should_fail and self._current_fail_count < self._fail_count:
            self._current_fail_count += 1
            raise RuntimeError("Mock LLM API error")

        return self._jd_features

    async def parse_jd_with_fallback(self, jd_text: str) -> JDFeatures:
        """解析 JD 文本

        v1.4.1: 移除 fallback，如果解析失败直接抛出错误

        Args:
            jd_text: JD 文本内容

        Returns:
            JDFeatures: 解析出的特征

        Raises:
            Exception: 如果 should_fail=True
        """
        return await self.parse_jd(jd_text)

    async def generate_embedding(self, text: str) -> EmbeddingResult:
        """生成嵌入向量

        Args:
            text: 输入文本

        Returns:
            EmbeddingResult: 嵌入结果
        """
        self._call_count += 1

        if self._should_fail and self._current_fail_count < self._fail_count:
            self._current_fail_count += 1
            raise RuntimeError("Mock embedding API error")

        return EmbeddingResult(
            embedding=self._embedding, model="mock-embedding-model", tokens_used=len(text.split())
        )

    async def generate_embedding_batch(self, texts: list[str]) -> list[EmbeddingResult]:
        """批量生成嵌入向量

        Args:
            texts: 文本列表

        Returns:
            List[EmbeddingResult]: 嵌入结果列表
        """
        self._call_count += 1

        if self._should_fail and self._current_fail_count < self._fail_count:
            self._current_fail_count += 1
            raise RuntimeError("Mock batch embedding API error")

        return [
            EmbeddingResult(
                embedding=self._embedding,
                model="mock-embedding-model",
                tokens_used=len(text.split()),
            )
            for text in texts
        ]

    async def health_check(self) -> bool:
        """健康检查

        Returns:
            bool: 服务是否健康
        """
        return not self._should_fail

    @property
    def call_count(self) -> int:
        """获取调用次数"""
        return self._call_count

    def reset(self):
        """重置状态"""
        self._call_count = 0
        self._current_fail_count = 0
