"""LinkedIn discovery fallback: combine known info into a Google search URL.

Used by domains that have no real LinkedIn profile URL for a person (the
academic domain has no LinkedIn data source; the lab domain uses this only
when its crawler found no real profile link). A real profile URL, whenever
one exists, always takes precedence over this fallback.
"""

from __future__ import annotations

from urllib.parse import quote_plus


def build_linkedin_search_url(name: str, affiliation: str = "") -> str:
    """Build a Google search URL like: "Wei Wang" MIT linkedin.

    The quoted exact-name phrase + affiliation + the "linkedin" keyword gives
    a high-precision people-search query on Google.
    """
    parts = [f'"{name.strip()}"']
    if affiliation.strip():
        parts.append(affiliation.strip())
    parts.append("linkedin")
    return "https://www.google.com/search?q=" + quote_plus(" ".join(parts))
