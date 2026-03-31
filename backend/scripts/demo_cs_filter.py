"""
CS背景得分筛选机制演示脚本

演示不同学科背景的作者如何被计算CS得分并决定是否入库。
"""
import json
import sys
import io

# 设置标准输出为UTF-8编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.services.normalizers.author import AuthorNormalizer
from app.services.common.cs_concepts import CORE_CS_CONCEPTS, CS_SCORE_THRESHOLD


def create_demo_data():
    """创建演示数据 - 不同学科背景的作者"""
    return [
        {
            "name": "AI领域专家 (AI Expert)",
            "description": "主要研究人工智能、机器学习",
            "raw_json": json.dumps({
                "x_concepts": [
                    {"id": "https://openalex.org/C154945302", "display_name": "Artificial intelligence", "score": 0.87},
                    {"id": "https://openalex.org/C119857082", "display_name": "Machine learning", "score": 0.75},
                    {"id": "https://openalex.org/C41008148", "display_name": "Computer science", "score": 0.92},
                ]
            })
        },
        {
            "name": "计算机视觉研究员 (CV Researcher)",
            "description": "主要研究计算机视觉、深度学习",
            "raw_json": json.dumps({
                "x_concepts": [
                    {"id": "https://openalex.org/C31972630", "display_name": "Computer vision", "score": 0.88},
                    {"id": "https://openalex.org/C154945302", "display_name": "Artificial intelligence", "score": 0.65},
                    {"id": "https://openalex.org/C41008148", "display_name": "Computer science", "score": 0.90},
                ]
            })
        },
        {
            "name": "生物学家 (Biologist)",
            "description": "主要研究生物学、医学，无CS背景",
            "raw_json": json.dumps({
                "x_concepts": [
                    {"id": "https://openalex.org/C86803240", "display_name": "Biology", "score": 0.95},
                    {"id": "https://openalex.org/C54427621", "display_name": "Chemistry", "score": 0.72},
                    {"id": "https://openalex.org/C71924100", "display_name": "Medicine", "score": 0.80},
                ]
            })
        },
        {
            "name": "化学家 (Chemist)",
            "description": "主要研究化学，无CS背景",
            "raw_json": json.dumps({
                "x_concepts": [
                    {"id": "https://openalex.org/C54427621", "display_name": "Chemistry", "score": 0.92},
                    {"id": "https://openalex.org/C178315738", "display_name": "Organic chemistry", "score": 0.78},
                ]
            })
        },
        {
            "name": "跨学科研究者 (Bioinformatics)",
            "description": "生物信息学，有部分CS背景",
            "raw_json": json.dumps({
                "x_concepts": [
                    {"id": "https://openalex.org/C86803240", "display_name": "Biology", "score": 0.85},
                    {"id": "https://openalex.org/C41008148", "display_name": "Computer science", "score": 0.45},
                    {"id": "https://openalex.org/C2522767166", "display_name": "Data science", "score": 0.35},
                ]
            })
        },
        {
            "name": "软件工程师 (Software Engineer)",
            "description": "主要研究软件工程",
            "raw_json": json.dumps({
                "x_concepts": [
                    {"id": "https://openalex.org/C115903868", "display_name": "Software engineering", "score": 0.82},
                    {"id": "https://openalex.org/C41008148", "display_name": "Computer science", "score": 0.88},
                    {"id": "https://openalex.org/C199360897", "display_name": "Programming language", "score": 0.65},
                ]
            })
        },
        {
            "name": "网络与通信研究者",
            "description": "主要研究计算机网络",
            "raw_json": json.dumps({
                "x_concepts": [
                    {"id": "https://openalex.org/C31258907", "display_name": "Computer network", "score": 0.80},
                    {"id": "https://openalex.org/C76155785", "display_name": "Telecommunications", "score": 0.75},
                    {"id": "https://openalex.org/C41008148", "display_name": "Computer science", "score": 0.85},
                ]
            })
        },
        {
            "name": "信息安全专家",
            "description": "主要研究信息安全",
            "raw_json": json.dumps({
                "x_concepts": [
                    {"id": "https://openalex.org/C527648132", "display_name": "Information security", "score": 0.78},
                    {"id": "https://openalex.org/C41008148", "display_name": "Computer science", "score": 0.82},
                ]
            })
        },
        {
            "name": "机器人学研究者",
            "description": "主要研究机器人学",
            "raw_json": json.dumps({
                "x_concepts": [
                    {"id": "https://openalex.org/C90509273", "display_name": "Robot", "score": 0.85},
                    {"id": "https://openalex.org/C34413123", "display_name": "Robotics", "score": 0.80},
                    {"id": "https://openalex.org/C31972630", "display_name": "Computer vision", "score": 0.55},
                    {"id": "https://openalex.org/C41008148", "display_name": "Computer science", "score": 0.70},
                ]
            })
        },
        {
            "name": "物理学家 (Physicist)",
            "description": "主要研究物理学，无CS背景",
            "raw_json": json.dumps({
                "x_concepts": [
                    {"id": "https://openalex.org/C121681514", "display_name": "Physics", "score": 0.95},
                    {"id": "https://openalex.org/C178790665", "display_name": "Quantum mechanics", "score": 0.72},
                ]
            })
        },
    ]


def main():
    """运行演示"""
    normalizer = AuthorNormalizer(None)  # 不需要session，只用计算方法

    demo_authors = create_demo_data()

    print("=" * 80)
    print("CS背景得分筛选机制演示")
    print("=" * 80)
    print(f"\n核心CS学科概念数: {len(CORE_CS_CONCEPTS)}")
    print(f"过滤阈值: {CS_SCORE_THRESHOLD}")
    print("\n" + "-" * 80)

    results = {
        "passed": [],
        "filtered": []
    }

    for author in demo_authors:
        cs_score = normalizer._calculate_cs_score(author["raw_json"])
        will_sync = cs_score >= CS_SCORE_THRESHOLD

        status = "[PASS] 入库" if will_sync else "[FILTER] 过滤"

        print(f"\n【{author['name']}】")
        print(f"  描述: {author['description']}")
        print(f"  CS得分: {cs_score:.2f}")
        print(f"  结果: {status}")

        if will_sync:
            results["passed"].append(author["name"])
        else:
            results["filtered"].append(author["name"])

    print("\n" + "=" * 80)
    print("汇总结果")
    print("=" * 80)
    print(f"\n[PASS] 将入库: {len(results['passed'])} 人")
    for name in results["passed"]:
        print(f"   - {name}")

    print(f"\n[FILTER] 被过滤: {len(results['filtered'])} 人")
    for name in results["filtered"]:
        print(f"   - {name}")

    print(f"\n过滤率: {len(results['filtered']) / len(demo_authors) * 100:.0f}%")
    print("=" * 80)


if __name__ == "__main__":
    main()
