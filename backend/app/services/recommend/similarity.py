"""
Similarity Calculator.
相似度计算器 - v1.4

Provides various similarity metrics for vector comparison.
"""

import math


class SimilarityCalculator:
    """相似度计算器

    提供多种相似度计算方法。
    """

    def cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """
        计算余弦相似度

        Args:
            vec1: 向量1
            vec2: 向量2

        Returns:
            float: -1 到 1 的相似度
        """
        if not vec1 or not vec2:
            return 0.0

        if len(vec1) != len(vec2):
            raise ValueError(f"Vector dimensions must match: {len(vec1)} != {len(vec2)}")

        dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=False))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def euclidean_distance(self, vec1: list[float], vec2: list[float]) -> float:
        """
        计算欧氏距离

        Args:
            vec1: 向量1
            vec2: 向量2

        Returns:
            float: 欧氏距离
        """
        if not vec1 or not vec2:
            return float("inf")

        if len(vec1) != len(vec2):
            raise ValueError(f"Vector dimensions must match: {len(vec1)} != {len(vec2)}")

        return math.sqrt(sum((a - b) ** 2 for a, b in zip(vec1, vec2, strict=False)))

    def euclidean_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """
        计算欧氏相似度 (1 / (1 + distance))

        Args:
            vec1: 向量1
            vec2: 向量2

        Returns:
            float: 0 到 1 的相似度
        """
        distance = self.euclidean_distance(vec1, vec2)
        return 1 / (1 + distance)

    def dot_product(self, vec1: list[float], vec2: list[float]) -> float:
        """
        计算点积

        Args:
            vec1: 向量1
            vec2: 向量2

        Returns:
            float: 点积值
        """
        if not vec1 or not vec2:
            return 0.0

        if len(vec1) != len(vec2):
            raise ValueError(f"Vector dimensions must match: {len(vec1)} != {len(vec2)}")

        return sum(a * b for a, b in zip(vec1, vec2, strict=False))
