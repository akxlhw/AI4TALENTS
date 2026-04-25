"""
Constants package for static configuration data.
"""

from app.constants.collect_task import (
    DEFAULT_START_YEAR,
    MIN_START_YEAR,
    TaskStatus,
    VenueType,
)
from app.constants.countries import (
    COUNTRY_NAMES,
    COUNTRY_NAMES_CN,
    COUNTRY_NAMES_EN,
    REGION_MAPPING,
    get_country_name_cn,
    get_country_name_en,
    get_region_for_country,
)
from app.constants.role_type import (
    LEGACY_ROLE_TYPE_MAP,
    RoleType,
    normalize_role_type,
)

__all__ = [
    # Role types
    "RoleType",
    "LEGACY_ROLE_TYPE_MAP",
    "normalize_role_type",
    # Task status
    "TaskStatus",
    "VenueType",
    "MIN_START_YEAR",
    "DEFAULT_START_YEAR",
    # Countries
    "COUNTRY_NAMES",
    "COUNTRY_NAMES_CN",
    "COUNTRY_NAMES_EN",
    "REGION_MAPPING",
    "get_country_name_cn",
    "get_country_name_en",
    "get_region_for_country",
]
