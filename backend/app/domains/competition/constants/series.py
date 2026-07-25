"""Contest series registry — single source of truth for seeding and display.

Codes follow the user's priority list (2026-07-18): ICPC, IOI/IMO/IPhO,
IMC, CTF, Kaggle, RoboCup, ASC/SC/ISC supercomputing; AtCoder is a
companion source. IChO/IBO are deferred (not pre-seeded).
"""

from __future__ import annotations

SERIES: list[dict] = [
    {
        "code": "icpc",
        "name": "国际大学生程序设计竞赛",
        "name_en": "ICPC",
        "homepage": "https://icpc.global",
        "description": "International Collegiate Programming Contest（3 人团队赛）",
        "is_enabled": True,  # M2（CLIST 榜单源，已验证导入）
    },
    {
        "code": "ioi",
        "name": "国际信息学奥林匹克竞赛",
        "name_en": "IOI",
        "homepage": "https://ioinformatics.org",
        "description": "International Olympiad in Informatics",
        "is_enabled": True,  # M2（stats.ioinformatics.org，已验证导入）
    },
    {
        "code": "imo",
        "name": "国际数学奥林匹克竞赛",
        "name_en": "IMO",
        "homepage": "https://www.imo-official.org",
        "description": "International Mathematical Olympiad",
        "is_enabled": True,  # M2（imo-official.org，已验证导入）
    },
    {
        "code": "ipho",
        "name": "国际物理奥林匹克竞赛",
        "name_en": "IPhO",
        "homepage": "https://ipho-unofficial.org",
        "description": "International Physics Olympiad（官方站 DNS 异常，采用 ipho-unofficial 存档源）",
        "is_enabled": True,  # M2（ipho-unofficial.org，已验证导入）
    },
    {
        "code": "kaggle",
        "name": "Kaggle 大数据科学竞赛",
        "name_en": "Kaggle",
        "homepage": "https://www.kaggle.com",
        "description": "数据科学与机器学习竞赛平台（个人/团队混合）",
        "is_enabled": False,  # M2-M3
    },
    {
        "code": "imc",
        "name": "国际大学生数学竞赛",
        "name_en": "IMC",
        "homepage": "https://www.imc-math.org.uk",
        "description": "International Mathematics Competition for University Students",
        "is_enabled": False,  # M3
    },
    {
        "code": "ctf",
        "name": "CTF 安全夺旗赛",
        "name_en": "CTF",
        "homepage": "https://ctftime.org",
        "description": "网络安全夺旗赛（团队赛，先落队伍级数据）",
        "is_enabled": False,  # M3
    },
    {
        "code": "robocup",
        "name": "机器人世界杯",
        "name_en": "RoboCup",
        "homepage": "https://www.robocup.org",
        "description": "Robot World Cup（团队赛，先落队伍级数据）",
        "is_enabled": False,  # M3
    },
    {
        "code": "asc",
        "name": "ASC 世界大学生超级计算机竞赛",
        "name_en": "ASC",
        "homepage": "http://www.asc-events.org",
        "description": "Asia Student Supercomputer Challenge（团队赛）",
        "is_enabled": False,  # M3
    },
    {
        "code": "sc",
        "name": "SC 国际大学生超级计算机竞赛",
        "name_en": "SC SCC",
        "homepage": "https://sc.conference.org",
        "description": "Student Cluster Competition @ SC（团队赛）",
        "is_enabled": False,  # M3
    },
    {
        "code": "isc",
        "name": "ISC 国际大学生超级计算机竞赛",
        "name_en": "ISC SCC",
        "homepage": "https://isc-hpcac.com",
        "description": "ISC Student Cluster Competition（团队赛）",
        "is_enabled": False,  # M3
    },
    {
        "code": "atcoder",
        "name": "AtCoder",
        "name_en": "AtCoder",
        "homepage": "https://atcoder.jp",
        "description": "日本算法竞赛平台（候选插入源）",
        "is_enabled": False,  # 视优先级插 M2-M3
    },
]

SERIES_BY_CODE: dict[str, dict] = {s["code"]: s for s in SERIES}
