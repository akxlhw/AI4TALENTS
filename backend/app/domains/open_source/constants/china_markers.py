"""中国背景人才判定常量（开源域搜索筛选用）。

判定规则（满足其一即为中国背景）：
1. 地区命中：location 包含中国相关词（China / 中国 / 主要城市拼音）
2. 姓名命中百家姓：name 的首个或末尾词元（空格分隔）是百家姓拼音
3. 姓名含中文字符：最强信号，直接命中

说明：
- 姓氏匹配限定词元边界（仅首/尾词），降低 "Sun"/"Long" 等英文词误伤；
- 该筛选为召回导向（宁可多不可漏），招聘场景下由人工二次确认；
- 词表可按需扩充，保持小写即可（匹配走 ILIKE / ~* 大小写不敏感）。
"""

from __future__ import annotations

# 中国相关地区词（location ILIKE %token%，大小写不敏感）
CHINA_LOCATION_TOKENS: list[str] = [
    "china",
    "中国",
    "beijing",
    "shanghai",
    "shenzhen",
    "hangzhou",
    "guangzhou",
    "chengdu",
    "nanjing",
    "wuhan",
    "xi'an",
    "xian",
    "suzhou",
    "tianjin",
    "chongqing",
    "hong kong",
    "hongkong",
    "macau",
    "macao",
    "taipei",
]

# 百家姓常见拼音姓氏
CHINESE_SURNAMES: list[str] = sorted(
    {
        "wang",
        "li",
        "zhang",
        "liu",
        "chen",
        "yang",
        "huang",
        "zhao",
        "wu",
        "zhou",
        "xu",
        "sun",
        "ma",
        "zhu",
        "hu",
        "guo",
        "he",
        "gao",
        "lin",
        "luo",
        "zheng",
        "liang",
        "xie",
        "song",
        "tang",
        "han",
        "feng",
        "deng",
        "cao",
        "peng",
        "lu",
        "xiao",
        "yan",
        "jiang",
        "shen",
        "qin",
        "jin",
        "tao",
        "wei",
        "jia",
        "xia",
        "fu",
        "fang",
        "zou",
        "xiong",
        "bai",
        "meng",
        "dong",
        "yuan",
        "yao",
        "tan",
        "gu",
        "du",
        "ding",
        "cheng",
        "qian",
        "cai",
        "pan",
        "tian",
        "zeng",
        "yu",
        "wen",
        "shi",
        "dai",
        "kong",
        "ye",
        "ren",
        "fan",
        "liao",
        "wan",
        "hong",
        "ni",
        "qiu",
        "gong",
        "shao",
        "qiao",
        "hou",
        "long",
        "duan",
        "yin",
        "chang",
        "mao",
        "che",
        "zhuo",
        "chu",
        "jing",
        "zhuang",
        "chai",
        "qu",
        "rong",
        "weng",
        "mu",
        "mi",
        "lv",
        "pei",
        "lan",
        "kan",
        "zhan",
    }
)

# 姓氏交替组（长音优先，避免短姓遮蔽长姓）
_SURNAME_ALT = "|".join(sorted(CHINESE_SURNAMES, key=len, reverse=True))

# 姓名首词元为姓氏："Zhang Wei ..."（要求后随空白，排除单词名/登录名）
NAME_FIRST_SURNAME_RE = rf"^(?:{_SURNAME_ALT})\s"
# 姓名末词元为姓氏："... Wei Zhang"
NAME_LAST_SURNAME_RE = rf"\s(?:{_SURNAME_ALT})$"
# 姓名含 CJK 字符
NAME_CJK_RE = r"[\u4e00-\u9fff]"
