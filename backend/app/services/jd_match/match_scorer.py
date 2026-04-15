"""
Match Scorer implementation.
匹配评分器实现 - v1.4.1

Simplified to only calculate research direction matching score.
- Matches research_areas against openalex_topics and paper titles
- Denominator limit changed from 3 to 5
"""

import logging
from typing import List, Dict, Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class MatchScorer:
    """匹配评分器

    v1.4.1: Simplified to only calculate research score.
    """

    def calculate_research_score(
        self,
        jd_areas: List[str],
        candidate_matchable: List[str],
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

        # v1.4.1: 按5个计要求数，超过计顶格
        max_required = 5
        required_count = min(len(jd_keywords), max_required)
        matched_count = min(len(matched), max_required)

        # 分数 = 匹配数 / 要求数
        score = matched_count / required_count * 100

        logger.info(
            f"Research score: {score:.1f} "
            f"(matched={len(matched)}/{required_count}, JD={jd_keywords})"
        )

        return min(100.0, score)

    def calculate_overall_score(
        self,
        research_score: float,
    ) -> float:
        """
        计算综合分数

        v1.4.1: Simplified to only use research score

        Args:
            research_score: 研究方向分数

        Returns:
            float: 0-100 的综合分数
        """
        return min(100.0, max(0.0, research_score))

    def generate_match_reasons(
        self,
        jd_features: Any,
        candidate: Dict[str, Any],
    ) -> List[str]:
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
