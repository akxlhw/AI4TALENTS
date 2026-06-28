"""Normalization helpers for lab_web raw person data.

- normalize_email: de-obfuscate academic-page email formats
- normalize_name: trim/collapse whitespace, preserve case & script
- compute_content_hash: stable fingerprint for dedup across fetches
"""

from __future__ import annotations

import hashlib
import re

# Bracketed/upper obfuscation: "john [at] cs [dot] edu" / "[AT]" / "(ät)"
_AT_DOT_PATTERN = re.compile(r"\s*\[\s*at\s*\]\s*|\s*\(\s*ät\s*\)\s*", re.IGNORECASE)
_DOT_PATTERN = re.compile(r"\s*\[\s*dot\s*\]\s*", re.IGNORECASE)
# A JS-rendered email: contains "<script" or spliced strings
_JS_PATTERN = re.compile(r"<\s*script|document\.write|'\s*\+\s*'", re.IGNORECASE)
_WHITESPACE = re.compile(r"\s+")


def normalize_email(raw: str | None) -> str | None:
    """De-obfuscate common academic-page email formats to standard form.

    Returns None when input is missing/blank or the email is JS-rendered
    (not parseable in v1). The caller preserves the raw string in raw_data.
    """
    if not raw or not raw.strip():
        return None
    text = raw.strip()
    if _JS_PATTERN.search(text):
        return None
    text = _AT_DOT_PATTERN.sub("@", text)
    text = _DOT_PATTERN.sub(".", text)
    text = _WHITESPACE.sub("", text).lower()
    # Validate it now looks like an email.
    if "@" not in text or " " in text:
        return None
    return text


def normalize_name(raw: str | None) -> str | None:
    """Trim and collapse internal whitespace; preserve case and script."""
    if raw is None:
        return None
    return _WHITESPACE.sub(" ", raw).strip()


def compute_content_hash(
    lab_code: str,
    name: str | None,
    title: str | None,
    email: str | None,
    homepage: str | None,
) -> str:
    """Stable SHA-256 fingerprint of a person for cross-fetch dedup.

    Fields chosen intentionally: name/title/email/homepage identify a person
    and are stable; source_url and avatar_url are excluded because they may
    change while the person stays the same.

    Cross-source uniqueness (I2, acknowledged): this hash is written into
    core_talent.source_record_id, which has a GLOBAL unique constraint. In
    practice OpenAlex numeric ids never collide with a sha256 hex, so this is
    safe. Within one lab, two genuinely-different people sharing all of
    name/title/email/homepage would dedup to one row — rare for real People
    pages (which almost always publish a homepage or email) but a known edge.
    """
    payload = "|".join(
        [
            lab_code,
            name or "",
            title or "",
            email or "",
            homepage or "",
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
