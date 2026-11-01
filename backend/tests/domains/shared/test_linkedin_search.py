"""build_linkedin_search_url: name/affiliation → Google search fallback link."""

from __future__ import annotations

from urllib.parse import parse_qs, quote_plus, urlparse

from app.domains.shared.services.common.linkedin_search import build_linkedin_search_url


def _query(url: str) -> str:
    return parse_qs(urlparse(url).query)["q"][0]


def test_combines_quoted_name_affiliation_and_keyword() -> None:
    url = build_linkedin_search_url("Wei Wang", "MIT")
    assert url.startswith("https://www.google.com/search?q=")
    q = _query(url)
    assert '"Wei Wang"' in q
    assert "MIT" in q
    assert "linkedin" in q


def test_name_only_when_no_affiliation() -> None:
    q = _query(build_linkedin_search_url("Wei Wang"))
    assert '"Wei Wang"' in q and "linkedin" in q


def test_chinese_name_is_url_encoded() -> None:
    url = build_linkedin_search_url("王伟", "清华大学")
    assert quote_plus("王伟") in url


def test_strips_whitespace_parts() -> None:
    q = _query(build_linkedin_search_url("  Wei Wang  ", "  "))
    assert q == '"Wei Wang" linkedin'
