"""
OpenAlex utility functions.
"""

from __future__ import annotations

from app.core.config import settings

# OpenAlex API base URL — single source of truth from settings
OPENALEX_API_BASE = settings.OPENALEX_BASE_URL

# Rate limiting: 10 requests per second for polite pool
REQUEST_DELAY = 0.1  # 100ms between requests


def extract_short_id(openalex_url: str | None) -> str:
    """Extract short ID from OpenAlex URL

    Examples:
        https://openalex.org/A123456789 -> A123456789
        https://openalex.org/W123456789 -> W123456789
    """
    if not openalex_url:
        return ""
    return openalex_url.split("/")[-1]
