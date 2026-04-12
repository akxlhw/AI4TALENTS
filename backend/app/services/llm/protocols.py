"""
LLM Gateway Protocol definitions.
LLM 网关协议定义 - 支持依赖倒置和 Mock 测试
"""

from typing import Protocol, List, runtime_checkable
from dataclasses import dataclass, field


@dataclass
class JDFeatures:
    """JD 解析结果

    LLM 从职位描述中提取的结构化特征。

    Attributes:
        skills: 所需技能列表
        experience: 经验要求（如 "3年以上"）
        research_areas: 研究方向列表
        role_type: 角色类型 (engineer/researcher/intern/senior/lead)
        education_level: 学历要求 (bachelor/master/phd/any)
        keywords: 关键词列表
    """
    skills: List[str] = field(default_factory=list)
    experience: str = "未知"
    research_areas: List[str] = field(default_factory=list)
    role_type: str = "unknown"
    education_level: str | None = None
    keywords: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "skills": self.skills,
            "experience": self.experience,
            "research_areas": self.research_areas,
            "role_type": self.role_type,
            "education_level": self.education_level,
            "keywords": self.keywords,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "JDFeatures":
        """从字典创建"""
        return cls(
            skills=data.get("skills", []),
            experience=data.get("experience", "未知"),
            research_areas=data.get("research_areas", []),
            role_type=data.get("role_type", "unknown"),
            education_level=data.get("education_level"),
            keywords=data.get("keywords", []),
        )


@dataclass
class EmbeddingResult:
    """嵌入生成结果

    Attributes:
        embedding: 嵌入向量
        model: 使用的模型名称
        tokens_used: 消耗的 token 数量
    """
    embedding: List[float]
    model: str
    tokens_used: int = 0

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "embedding": self.embedding,
            "model": self.model,
            "tokens_used": self.tokens_used,
        }


@runtime_checkable
class LLMGatewayProtocol(Protocol):
    """LLM 网关抽象接口

    定义 LLM 网关必须实现的方法，便于：
    - Mock 测试
    - 不同 LLM 提供商的替换
    - 依赖注入
    """

    async def parse_jd(self, jd_text: str) -> JDFeatures:
        """解析 JD 文本，提取关键特征

        Args:
            jd_text: JD 文本内容

        Returns:
            JDFeatures: 解析出的特征

        Raises:
            LLMError: LLM API 调用失败
        """
        ...

    async def generate_embedding(self, text: str) -> EmbeddingResult:
        """生成文本嵌入向量

        Args:
            text: 输入文本

        Returns:
            EmbeddingResult: 嵌入结果

        Raises:
            LLMError: LLM API 调用失败
        """
        ...

    async def generate_embedding_batch(self, texts: List[str]) -> List[EmbeddingResult]:
        """批量生成嵌入向量

        Args:
            texts: 文本列表

        Returns:
            List[EmbeddingResult]: 嵌入结果列表

        Raises:
            LLMError: LLM API 调用失败
        """
        ...

    async def health_check(self) -> bool:
        """健康检查

        Returns:
            bool: 服务是否健康
        """
        ...
