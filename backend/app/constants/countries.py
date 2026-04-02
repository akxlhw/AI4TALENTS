"""
Country constants for the talent system.

This module contains static country data that was previously stored in the
core_country table. Countries are identified by their ISO 3166-1 alpha-2 codes.
"""
from __future__ import annotations

# Country names mapping: country_code -> {cn, en}
# Ordered by academic activity/importance
COUNTRY_NAMES: dict[str, dict[str, str]] = {
    # Major academic countries
    "US": {"cn": "美国", "en": "United States"},
    "CN": {"cn": "中国", "en": "China"},
    "GB": {"cn": "英国", "en": "United Kingdom"},
    "DE": {"cn": "德国", "en": "Germany"},
    "JP": {"cn": "日本", "en": "Japan"},
    "FR": {"cn": "法国", "en": "France"},
    "CA": {"cn": "加拿大", "en": "Canada"},
    "AU": {"cn": "澳大利亚", "en": "Australia"},
    "SG": {"cn": "新加坡", "en": "Singapore"},
    "KR": {"cn": "韩国", "en": "South Korea"},
    "CH": {"cn": "瑞士", "en": "Switzerland"},
    "NL": {"cn": "荷兰", "en": "Netherlands"},
    "SE": {"cn": "瑞典", "en": "Sweden"},
    "IT": {"cn": "意大利", "en": "Italy"},
    "ES": {"cn": "西班牙", "en": "Spain"},
    # Other important countries
    "IN": {"cn": "印度", "en": "India"},
    "RU": {"cn": "俄罗斯", "en": "Russia"},
    "BR": {"cn": "巴西", "en": "Brazil"},
    "HK": {"cn": "香港", "en": "Hong Kong"},
    "PL": {"cn": "波兰", "en": "Poland"},
    "VN": {"cn": "越南", "en": "Vietnam"},
    "FI": {"cn": "芬兰", "en": "Finland"},
    "NO": {"cn": "挪威", "en": "Norway"},
    "DK": {"cn": "丹麦", "en": "Denmark"},
    "AT": {"cn": "奥地利", "en": "Austria"},
    "BE": {"cn": "比利时", "en": "Belgium"},
    "IL": {"cn": "以色列", "en": "Israel"},
    "NZ": {"cn": "新西兰", "en": "New Zealand"},
    "IE": {"cn": "爱尔兰", "en": "Ireland"},
    "PT": {"cn": "葡萄牙", "en": "Portugal"},
    "CZ": {"cn": "捷克", "en": "Czech Republic"},
    "GR": {"cn": "希腊", "en": "Greece"},
    "MY": {"cn": "马来西亚", "en": "Malaysia"},
    "TH": {"cn": "泰国", "en": "Thailand"},
    "ZA": {"cn": "南非", "en": "South Africa"},
    "MX": {"cn": "墨西哥", "en": "Mexico"},
    "AE": {"cn": "阿联酋", "en": "United Arab Emirates"},
    "SA": {"cn": "沙特阿拉伯", "en": "Saudi Arabia"},
    "TR": {"cn": "土耳其", "en": "Turkey"},
    "ID": {"cn": "印度尼西亚", "en": "Indonesia"},
    "PH": {"cn": "菲律宾", "en": "Philippines"},
    "AR": {"cn": "阿根廷", "en": "Argentina"},
    "CL": {"cn": "智利", "en": "Chile"},
    "CO": {"cn": "哥伦比亚", "en": "Colombia"},
    "EG": {"cn": "埃及", "en": "Egypt"},
    "NG": {"cn": "尼日利亚", "en": "Nigeria"},
    "PK": {"cn": "巴基斯坦", "en": "Pakistan"},
    "BD": {"cn": "孟加拉国", "en": "Bangladesh"},
    "HU": {"cn": "匈牙利", "en": "Hungary"},
    "RO": {"cn": "罗马尼亚", "en": "Romania"},
    "UA": {"cn": "乌克兰", "en": "Ukraine"},
    "RS": {"cn": "塞尔维亚", "en": "Serbia"},
    "SI": {"cn": "斯洛文尼亚", "en": "Slovenia"},
    "SK": {"cn": "斯洛伐克", "en": "Slovakia"},
    "BG": {"cn": "保加利亚", "en": "Bulgaria"},
    "HR": {"cn": "克罗地亚", "en": "Croatia"},
    "LT": {"cn": "立陶宛", "en": "Lithuania"},
    "LV": {"cn": "拉脱维亚", "en": "Latvia"},
    "EE": {"cn": "爱沙尼亚", "en": "Estonia"},
    "IS": {"cn": "冰岛", "en": "Iceland"},
    "LU": {"cn": "卢森堡", "en": "Luxembourg"},
    "MT": {"cn": "马耳他", "en": "Malta"},
    "CY": {"cn": "塞浦路斯", "en": "Cyprus"},
    # Middle East and North Africa
    "IQ": {"cn": "伊拉克", "en": "Iraq"},
    "IR": {"cn": "伊朗", "en": "Iran"},
    "MM": {"cn": "缅甸", "en": "Myanmar"},
    "MN": {"cn": "蒙古", "en": "Mongolia"},
    "KP": {"cn": "朝鲜", "en": "North Korea"},
    "LK": {"cn": "斯里兰卡", "en": "Sri Lanka"},
    "NP": {"cn": "尼泊尔", "en": "Nepal"},
    "JO": {"cn": "约旦", "en": "Jordan"},
    "LB": {"cn": "黎巴嫩", "en": "Lebanon"},
    "MA": {"cn": "摩洛哥", "en": "Morocco"},
    "TN": {"cn": "突尼斯", "en": "Tunisia"},
    "DZ": {"cn": "阿尔及利亚", "en": "Algeria"},
    # Africa
    "KE": {"cn": "肯尼亚", "en": "Kenya"},
    "GH": {"cn": "加纳", "en": "Ghana"},
    "ET": {"cn": "埃塞俄比亚", "en": "Ethiopia"},
    "UG": {"cn": "乌干达", "en": "Uganda"},
    "TZ": {"cn": "坦桑尼亚", "en": "Tanzania"},
    "CM": {"cn": "喀麦隆", "en": "Cameroon"},
    # South America
    "PE": {"cn": "秘鲁", "en": "Peru"},
    "VE": {"cn": "委内瑞拉", "en": "Venezuela"},
    "UY": {"cn": "乌拉圭", "en": "Uruguay"},
    "PY": {"cn": "巴拉圭", "en": "Paraguay"},
    "BO": {"cn": "玻利维亚", "en": "Bolivia"},
    "EC": {"cn": "厄瓜多尔", "en": "Ecuador"},
    # Central America and Caribbean
    "CU": {"cn": "古巴", "en": "Cuba"},
    "JM": {"cn": "牙买加", "en": "Jamaica"},
    "CR": {"cn": "哥斯达黎加", "en": "Costa Rica"},
    "PA": {"cn": "巴拿马", "en": "Panama"},
    "DO": {"cn": "多米尼加", "en": "Dominican Republic"},
    "GT": {"cn": "危地马拉", "en": "Guatemala"},
    # Unknown/Other
    "XX": {"cn": "未知", "en": "Unknown"},
}

# Convenience mappings for Chinese names only
COUNTRY_NAMES_CN: dict[str, str] = {
    code: names["cn"] for code, names in COUNTRY_NAMES.items()
}

# Convenience mappings for English names only
COUNTRY_NAMES_EN: dict[str, str] = {
    code: names["en"] for code, names in COUNTRY_NAMES.items()
}

# Region mapping for UI display
# Groups countries by geographic region for the CountrySchoolPage tabs
REGION_MAPPING: dict[str, set[str]] = {
    "north_america": {"US", "CA"},
    "asia_pacific": {
        "CN", "JP", "KR", "SG", "AU", "NZ", "HK", "IN", "MY", "TH",
        "TW",  # Taiwan is part of China but listed separately for UI grouping
    },
    "europe": {
        "GB", "DE", "FR", "CH", "NL", "IT", "ES", "SE", "AT", "BE",
        "DK", "FI", "NO", "IE", "PT", "PL", "RU", "HU", "RO", "UA",
        "RS", "SI", "SK", "BG", "HR", "LT", "LV", "EE", "IS", "LU",
        "MT", "CY", "GR", "CZ",
    },
    # "other" region is dynamically computed in the UI
}


def get_country_name_cn(country_code: str | None) -> str:
    """
    Get Chinese name for a country code.

    Args:
        country_code: ISO 3166-1 alpha-2 country code

    Returns:
        Chinese name, or the country code itself if not found
    """
    if not country_code:
        return "未知"

    # Taiwan is part of China - map TW to CN for display
    code = country_code.upper()
    if code == "TW":
        code = "CN"

    return COUNTRY_NAMES_CN.get(code, country_code)


def get_country_name_en(country_code: str | None) -> str:
    """
    Get English name for a country code.

    Args:
        country_code: ISO 3166-1 alpha-2 country code

    Returns:
        English name, or the country code itself if not found
    """
    if not country_code:
        return "Unknown"

    # Taiwan is part of China - map TW to CN for display
    code = country_code.upper()
    if code == "TW":
        code = "CN"

    return COUNTRY_NAMES_EN.get(code, country_code)


def get_region_for_country(country_code: str | None) -> str:
    """
    Get the region for a country code.

    Args:
        country_code: ISO 3166-1 alpha-2 country code

    Returns:
        Region key ('north_america', 'asia_pacific', 'europe', or 'other')
    """
    if not country_code:
        return "other"

    code = country_code.upper()

    for region, codes in REGION_MAPPING.items():
        if code in codes:
            return region

    return "other"


def normalize_country_code(country_code: str | None) -> str:
    """
    Normalize country code, mapping Taiwan to China.

    Args:
        country_code: ISO 3166-1 alpha-2 country code

    Returns:
        Normalized country code (TW -> CN)
    """
    if not country_code:
        return "XX"

    code = country_code.upper()
    if code == "TW":
        return "CN"

    return code
