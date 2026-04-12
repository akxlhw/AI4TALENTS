"""
Match Scorer implementation.
匹配评分器实现 - v1.4

Calculates match scores between JD features and candidate profiles.
"""

from typing import List, Dict, Any


class MatchScorer:
    """匹配评分器

    计算 JD 与候选人之间的匹配分数。
    """

    def calculate_skill_score(
        self,
        jd_skills: List[str],
        candidate_skills: List[str],
    ) -> float:
        """
        计算技能匹配分数

        Args:
            jd_skills: JD 要求的技能
            candidate_skills: 候选人具备的技能

        Returns:
            float: 0-100 的分数
        """
        if not jd_skills:
            return 50.0

        if not candidate_skills:
            return 0.0

        # 标准化为小写
        jd_set = set(s.lower() for s in jd_skills)
        candidate_set = set(s.lower() for s in candidate_skills)

        # 计算交集
        matched = jd_set & candidate_set

        # 分数 = 匹配数 / JD要求数
        score = len(matched) / len(jd_set) * 100

        return min(100.0, score)

    def calculate_research_score(
        self,
        jd_areas: List[str],
        candidate_areas: List[str],
    ) -> float:
        """
        计算研究方向匹配分数

        Args:
            jd_areas: JD 要求的研究方向
            candidate_areas: 候选人的研究方向

        Returns:
            float: 0-100 的分数
        """
        if not jd_areas:
            return 50.0

        if not candidate_areas:
            return 0.0

        # 标准化
        jd_set = set(a.lower() for a in jd_areas)
        candidate_set = set(a.lower() for a in candidate_areas)

        # 计算交集
        matched = jd_set & candidate_set

        score = len(matched) / len(jd_set) * 100

        return min(100.0, score)

    def calculate_overall_score(
        self,
        skill_score: float,
        research_score: float,
        experience_score: float,
        education_score: float,
        weights: Dict[str, float],
    ) -> float:
        """
        计算综合分数

        Args:
            skill_score: 技能分数
            research_score: 研究方向分数
            experience_score: 经验分数
            education_score: 学历分数
            weights: 权重配置

        Returns:
            float: 0-100 的综合分数
        """
        w = weights or {}
        total_weight = sum(w.values()) or 1.0

        overall = (
            skill_score * w.get("skill", 0.25) +
            research_score * w.get("research", 0.25) +
            experience_score * w.get("experience", 0.25) +
            education_score * w.get("education", 0.25)
        ) / total_weight

        return min(100.0, max(0.0, overall))

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

        # 技能匹配
        jd_skills = set(s.lower() for s in jd_features.skills)
        candidate_skills = set(s.lower() for s in candidate.get("skills", []))
        matched_skills = jd_skills & candidate_skills

        if matched_skills:
            reasons.append(f"技能匹配：{', '.join(matched_skills)}")

        # 研究方向匹配
        if candidate.get("research_interests"):
            jd_areas = set(a.lower() for a in jd_features.research_areas)
            research = candidate["research_interests"].lower()
            for area in jd_areas:
                if area in research:
                    reasons.append(f"研究方向匹配：{area}")
                    break

        # 引用量
        if candidate.get("h_index", 0) >= 10:
            reasons.append(f"高影响力学者：H-index {candidate['h_index']}")

        return reasons

    def get_highlight_skills(
        self,
        jd_skills: List[str],
        candidate_skills: List[str],
    ) -> List[str]:
        """
        获取高亮技能（匹配的技能）

        Args:
            jd_skills: JD 要求的技能
            candidate_skills: 候选人具备的技能

        Returns:
            List[str]: 匹配的技能列表
        """
        jd_set = set(s.lower() for s in jd_skills)
        candidate_set = set(s.lower() for s in candidate_skills)

        matched = jd_set & candidate_set

        # 返回原始大小写形式
        return [s for s in jd_skills if s.lower() in matched]
