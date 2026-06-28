"""HTML preprocessing for lab_web_site LLM parsing.

Raw People-page HTML can be large (NLP Group ~184KB) with scripts/styles/nav
that bloat LLM tokens and distract parsing. This module strips noise, keeps
people-relevant text, and caps size so the LLM gets a clean, focused input.
"""

from __future__ import annotations

import re

_WHITESPACE = re.compile(r"\s+")
TRUNCATION_MARKER = "...[truncated]"


def preprocess_html(html: str, max_chars: int = 50000) -> str:
    """Strip noise from People-page HTML and cap size for LLM input.

    - Removes <script>, <style>, <nav>, <footer>, <header> nodes.
    - Strips remaining tags, keeps text content.
    - Collapses whitespace.
    - Truncates to max_chars with a marker if still too long.
    """
    text = html
    for tag in ("script", "style", "nav", "footer", "header"):
        text = re.sub(rf"<{tag}\b[^>]*>.*?</{tag}>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = _WHITESPACE.sub(" ", text).strip()
    if len(text) > max_chars:
        text = text[:max_chars] + TRUNCATION_MARKER
    return text
