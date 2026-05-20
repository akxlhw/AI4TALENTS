"""
Match Scorer implementation.
匹配评分器实现

- Research score: keyword match against openalex_topics + paper titles (max_required=3)
- Impact score: log-normalized h-index
- Overall = research × w_research + impact × w_impact
"""

import logging
import math
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class MatchScorer:
    """匹配评分器

    研究方向匹配 + h-index 学术影响力加权融合评分。
    """

    def calculate_research_score(
        self,
        jd_areas: list[str],
        candidate_matchable: list[str],
    ) -> float:
        """
        计算研究方向匹配分数（支持子串匹配）

        Args:
            jd_areas: JD 要求的研究方向（英文关键词）
            candidate_matchable: 候选人的可匹配内容（研究方向 + 论文标题）

        Returns:
            float: 0-100 的分数
        """
        if not jd_areas:
            return 50.0

        if not candidate_matchable:
            return 0.0

        # 标准化
        jd_keywords = [a.lower() for a in jd_areas]
        candidate_lower = [a.lower() for a in candidate_matchable]

        # 子串匹配：检查 JD 关键词是否出现在候选人的研究方向或论文标题中
        matched = set()
        for jd_kw in jd_keywords:
            for cand_item in candidate_lower:
                # 双向子串匹配
                if jd_kw in cand_item or cand_item in jd_kw:
                    matched.add(jd_kw)
                    logger.debug(f"Research matched: JD '{jd_kw}' <-> Candidate '{cand_item}'")
                    break

        # 按3个计要求数，超过封顶
        max_required = 3
        required_count = min(len(jd_keywords), max_required)
        matched_count = min(len(matched), max_required)

        # 分数 = 匹配数 / 要求数
        score = matched_count / required_count * 100

        logger.info(
            f"Research score: {score:.1f} "
            f"(matched={len(matched)}/{required_count}, JD={jd_keywords})"
        )

        return min(100.0, score)

    def calculate_h_index_score(self, h_index: int) -> float:
        """
        计算学术影响力分数（对数归一化）

        h_index 经对数变换映射到 0-100：
        score = min(ln(h + 1) / ln(H_REF + 1), 1.0) × 100

        Args:
            h_index: 候选人的 h-index 值

        Returns:
            float: 0-100 的分数
        """
        if h_index <= 0:
            return 0.0

        h_ref = settings.JD_MATCH_H_REF
        score = math.log(h_index + 1) / math.log(h_ref + 1) * 100
        return min(100.0, score)

    def calculate_overall_score(
        self,
        research_score: float,
        h_index: int = 0,
    ) -> tuple[float, float]:
        """
        计算综合分数（研究方向 + 学术影响力加权求和）

        Args:
            research_score: 研究方向分数 (0-100)
            h_index: 候选人的 h-index 值

        Returns:
            tuple[float, float]: (overall_score, impact_score)
        """
        impact_score = self.calculate_h_index_score(h_index)
        weights = settings.JD_MATCH_WEIGHTS
        overall = research_score * weights["research"] + impact_score * weights["impact"]
        return min(100.0, max(0.0, overall)), impact_score

    def generate_match_reasons(
        self,
        jd_features: Any,
        candidate: dict[str, Any],
    ) -> list[str]:
        """
        生成匹配原因

        Args:
            jd_features: JD 特征
            candidate: 候选人信息

        Returns:
            List[str]: 匹配原因列表
        """
        reasons = []

        # 研究方向匹配（子串匹配）
        research_topics = candidate.get("research_topics", [])
        paper_titles = candidate.get("paper_titles", [])

        # 合并研究方向和论文标题
        all_matchable = research_topics + paper_titles

        if all_matchable and jd_features.research_areas:
            jd_areas = [a.lower() for a in jd_features.research_areas]
            candidate_items = [item.lower() for item in all_matchable]
            matched_areas = set()

            for jd_kw in jd_areas:
                for cand_item in candidate_items:
                    if jd_kw in cand_item or cand_item in jd_kw:
                        matched_areas.add(jd_kw)
                        break

            if matched_areas:
                reasons.append(f"研究方向匹配：{', '.join(list(matched_areas)[:5])}")

        # 引用量
        if candidate.get("h_index", 0) >= 10:
            reasons.append(f"高影响力学者：H-index {candidate['h_index']}")

        return reasons
