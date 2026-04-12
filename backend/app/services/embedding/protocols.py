"""
Embedding Service Protocol definitions.
嵌入服务协议定义
"""

from typing import Protocol, List, runtime_checkable


@runtime_checkable
class EmbedServiceProtocol(Protocol):
    """嵌入服务抽象接口

    定义嵌入服务必须实现的方法。
    """

    async def get_or_create_embedding(self, talent_id: int) -> List[float]:
        """获取或创建人才嵌入向量

        优先从缓存/数据库获取，不存在则生成。

        Args:
            talent_id: 人才 ID

        Returns:
            List[float]: 嵌入向量

        Raises:
            TalentNotFoundError: 人才不存在
            EmbeddingError: 嵌入生成失败
        """
        ...

    async def batch_generate_embeddings(
        self,
        talent_ids: List[int],
        batch_size: int = 100
    ) -> int:
        """批量生成嵌入向量

        Args:
            talent_ids: 人才 ID 列表
            batch_size: 批次大小

        Returns:
            int: 成功生成的数量
        """
        ...

    async def get_average_embedding(self, talent_ids: List[int]) -> List[float]:
        """获取多个人才的平均嵌入向量

        Args:
            talent_ids: 人才 ID 列表

        Returns:
            List[float]: 平均嵌入向量
        """
        ...

    async def get_query_embedding(self, query: str) -> List[float]:
        """获取查询文本的嵌入向量

        Args:
            query: 查询文本

        Returns:
            List[float]: 嵌入向量
        """
        ...
