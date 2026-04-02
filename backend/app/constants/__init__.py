"""
Constants package for static configuration data.
"""
from app.constants.countries import (
    COUNTRY_NAMES,
    COUNTRY_NAMES_CN,
    COUNTRY_NAMES_EN,
    REGION_MAPPING,
    get_country_name_cn,
    get_country_name_en,
    get_region_for_country,
)

__all__ = [
    "COUNTRY_NAMES",
    "COUNTRY_NAMES_CN",
    "COUNTRY_NAMES_EN",
    "REGION_MAPPING",
    "get_country_name_cn",
    "get_country_name_en",
    "get_region_for_country",
]
