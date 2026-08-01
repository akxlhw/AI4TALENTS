"""Manual school abbreviation / alias table for student detection.

These complement the school dictionary exported from the academic domain
(``school_dict.json``). Matching is word-boundary based for Latin names
and substring based for CJK names (see ``os_student_classifier``).
"""

# 手工缩写别名表：常见高校的英文缩写、简写与中文简称。
MANUAL_SCHOOL_ALIASES: list[str] = [
    # 英文缩写
    "MIT",
    "CMU",
    "EPFL",
    "ETH",
    "KAIST",
    "USTC",
    "UCLA",
    "NYU",
    "NUS",
    "NTU",
    "SJTU",
    "UC Berkeley",
    "Georgia Tech",
    # 英文简写
    "Tsinghua",
    "Peking",
    "Fudan",
    "Harvard",
    "Stanford",
    "Oxford",
    "Cambridge",
    "Princeton",
    "Yale",
    "Cornell",
    "Caltech",
    # 中文简称
    "清华大学",
    "北京大学",
    "浙江大学",
    "复旦大学",
    "上海交大",
    "中科大",
    "南京大学",
    "哈工大",
]
