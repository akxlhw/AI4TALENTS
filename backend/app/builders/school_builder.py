"""
School object builder.

DEPRECATED: This builder uses the old RawSourceRecord model which has been removed.
Please use ServingLayerSync from app.services.serving_layer_sync instead.
"""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.builders.base import BaseBuilder, BuildResult

logger = logging.getLogger(__name__)


# Known institution name mappings - kept for reference
INSTITUTION_NAME_MAPPING = {
    "massachusetts institute of technology": "MIT",
    "massachusetts institute of technology (mit)": "MIT",
    "stanford university": "Stanford",
    "harvard university": "Harvard",
    "university of cambridge": "Cambridge",
    "university of oxford": "Oxford",
    "california institute of technology": "Caltech",
    "princeton university": "Princeton",
    "yale university": "Yale",
    "columbia university": "Columbia",
    "university of chicago": "UChicago",
    "university of california, berkeley": "UC Berkeley",
    "tsinghua university": "Tsinghua University",
    "peking university": "Peking University",
}


def normalize_name(name: str) -> str:
    """Normalize institution name for matching."""
    return name.lower().strip()


def extract_openalex_id(openalex_url: str) -> str:
    """Extract OpenAlex ID from URL."""
    if not openalex_url:
        return ""
    return openalex_url.rsplit("/", 1)[-1]


class SchoolBuilder(BaseBuilder):
    """
    DEPRECATED: Use ServingLayerSync instead.

    This builder uses the old RawSourceRecord model which has been removed.
    """

    def __init__(self, session: AsyncSession, batch_id: int):
        super().__init__(batch_id)
        self.session = session
        self._country_cache: dict[str, int] = {}
        logger.warning("SchoolBuilder is deprecated. Use ServingLayerSync instead.")

    async def build(self) -> BuildResult:
        """
        DEPRECATED: This method is no longer supported.
        """
        raise NotImplementedError(
            "SchoolBuilder is deprecated. "
            "Please use ServingLayerSync from app.services.serving_layer_sync instead."
        )

    async def _get_country_id(self, country_code: str) -> str | None:
        """Get normalized country code.

        Note: Taiwan (TW) is mapped to China (CN) as Taiwan is part of China.

        DEPRECATED: This method is no longer used. Country info is now stored
        directly in School model via country_code and country_name fields.
        """
        from app.constants.countries import normalize_country_code
        return normalize_country_code(country_code)
