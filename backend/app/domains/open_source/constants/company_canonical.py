"""公司名归一化（开源域洞察统计用）。

GitHub 资料的公司字段是自由文本：同一公司会出现大小写差异（NVIDIA/Nvidia）、
'@' 前缀（@Google）、法律后缀（Google LLC / NVIDIA Corporation）、中英文别名
（字节跳动/ByteDance）等变体。聚合统计时必须先归一到规范名，否则同一公司
被拆成多个条目。

归一规则（按序应用）：
1. 去首尾空白与 '@' 前缀
2. 剥除常见法律/通用后缀（Inc/Ltd/LLC/Corporation/Technologies 等）
3. 别名映射（大小写不敏感）→ 规范显示名；未命中则保留（处理后的）原文
"""

from __future__ import annotations

import re

# 法律/通用后缀（词边界，要求前有空格，避免误伤 "OpenAI"/"MetaAI" 这类名中含 AI 的公司）
_LEGAL_SUFFIX_RE = re.compile(
    r"\s+(inc\.?|ltd\.?|llc|llp|corp\.?|corporation|co\.,?\s*ltd\.?|gmbh|pty\.?\s*ltd\.?|"
    r"technologies|technology|tech|labs|lab|ai|group|holdings|incorporated)\.?$",
    re.IGNORECASE,
)

# 规范显示名 → 别名列表（全部小写比较；规范名自身自动纳入别名）
COMPANY_CANONICAL: dict[str, list[str]] = {
    # 全球大厂
    "Google": ["google", "谷歌", "alphabet"],
    "Microsoft": ["microsoft", "微软"],
    "Apple": ["apple", "苹果"],
    "Amazon": ["amazon", "亚马逊", "aws", "amazon web services"],
    "Meta": ["meta", "facebook", "meta platforms"],
    "NVIDIA": ["nvidia", "英伟达", "英伟达公司"],
    "Tesla": ["tesla", "特斯拉"],
    "Intel": ["intel", "英特尔"],
    "AMD": ["amd"],
    "IBM": ["ibm"],
    "Oracle": ["oracle", "甲骨文"],
    "Samsung": ["samsung", "三星"],
    "Qualcomm": ["qualcomm", "高通"],
    "Cisco": ["cisco", "思科"],
    "Netflix": ["netflix", "奈飞", "网飞"],
    "Uber": ["uber", "优步"],
    "Airbnb": ["airbnb", "爱彼迎"],
    "OpenAI": ["openai", "open ai"],
    "Anthropic": ["anthropic"],
    "xAI": ["xai", "x.ai"],
    "Mistral AI": ["mistral", "mistral ai", "mistralai"],
    "Hugging Face": ["hugging face", "huggingface"],
    "Cohere": ["cohere"],
    "Databricks": ["databricks"],
    "Scale AI": ["scale ai", "scale"],
    "Stripe": ["stripe"],
    "Shopify": ["shopify"],
    "Cloudflare": ["cloudflare"],
    "Snowflake": ["snowflake"],
    "Palantir": ["palantir"],
    # 国内头部
    "字节跳动": ["字节跳动", "字节", "bytedance", "tiktok", "抖音"],
    "阿里巴巴": ["阿里巴巴", "阿里", "alibaba", "alibaba group", "阿里巴巴集团"],
    "腾讯": ["腾讯", "tencent", "腾讯科技"],
    "百度": ["百度", "baidu"],
    "华为": ["华为", "huawei", "华为技术有限公司", "huawei technologies"],
    "美团": ["美团", "meituan", "美团点评"],
    "京东": ["京东", "jd", "jd.com", "jingdong"],
    "拼多多": ["拼多多", "pdd", "pinduoduo"],
    "网易": ["网易", "netease"],
    "小米": ["小米", "xiaomi", "小米科技"],
    "快手": ["快手", "kuaishou"],
    "哔哩哔哩": ["哔哩哔哩", "bilibili", "b站"],
    "滴滴": ["滴滴", "didi", "滴滴出行", "didichuxing", "didi global"],
    "蚂蚁集团": ["蚂蚁集团", "蚂蚁", "ant group", "antgroup", "蚂蚁金服", "支付宝", "alipay"],
    "商汤科技": ["商汤", "商汤科技", "sensetime"],
    "科大讯飞": ["科大讯飞", "iflytek", "讯飞"],
    "联想": ["联想", "lenovo"],
    "中兴": ["中兴", "zte", "中兴通讯"],
    # AI 初创（国内）
    "DeepSeek": ["deepseek", "深度求索", "深度求索公司"],
    "月之暗面": ["月之暗面", "moonshot", "moonshot ai", "moonshotai", "kimi"],
    "智谱AI": ["智谱", "智谱ai", "zhipu", "zhipu ai", "zhipuai"],
    "MiniMax": ["minimax", "稀宇科技"],
    "百川智能": ["百川智能", "百川", "baichuan", "baichuan ai"],
    "阶跃星辰": ["阶跃星辰", "阶跃", "stepfun", "step fun"],
    "面壁智能": ["面壁智能", "面壁", "modelbest"],
    "零一万物": ["零一万物", "01.ai", "01ai"],
    "昆仑万维": ["昆仑万维", "kunlun"],
    "旷视科技": ["旷视", "旷视科技", "megvii"],
    "大疆": ["大疆", "dji"],
    "米哈游": ["米哈游", "mihoyo", "hoyoverse"],
}

# 别名（小写）→ 规范显示名
_ALIAS_TO_CANONICAL: dict[str, str] = {}
for _canonical, _aliases in COMPANY_CANONICAL.items():
    _ALIAS_TO_CANONICAL[_canonical.casefold()] = _canonical
    for _alias in _aliases:
        _ALIAS_TO_CANONICAL[_alias.casefold()] = _canonical

# 全部规范显示名（归一结果是否命中映射的判断依据）
CANONICAL_NAMES: set[str] = set(COMPANY_CANONICAL)


def canonicalize_company(raw: str | None) -> str | None:
    """归一公司名；空值返回 None。"""
    if not raw:
        return None
    s = raw.strip().lstrip("@").strip()
    if not s:
        return None
    # 剥除法律后缀（连续剥两次覆盖 "Meta Platforms, Inc." 之类的双后缀情形）
    s = _LEGAL_SUFFIX_RE.sub("", s).strip().rstrip(",").strip()
    s = _LEGAL_SUFFIX_RE.sub("", s).strip().rstrip(",").strip()
    if not s:
        return None
    return _ALIAS_TO_CANONICAL.get(s.casefold(), s)
