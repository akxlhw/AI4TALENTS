"""Stanford SAIL People-page collector.

Selectors target the SIMPLIFIED fixture structure in
tests/fixtures/lab_web/stanford_sail_people.html, NOT the real ai.stanford.edu
DOM. Success criterion §10.3 (scrape all SAIL people) is therefore NOT yet
verified end-to-end (I3, acknowledged): before relying on this in production,
curl the live page, commit a real snapshot as the fixture, re-derive the
selectors below against the actual markup, and add a `slow`-marked live smoke
test (spec §9). The parsing contract (response.css(...)) is correct; only the
selector strings need to match the real DOM.
"""

from __future__ import annotations

from typing import Any

from app.domains.lab_web.services.collectors.base_collector import (
    BaseLabCollector,
    RawPersonDraft,
)


class StanfordSailCollector(BaseLabCollector):
    """Collector for https://ai.stanford.edu/people/."""

    lab_code = "stanford_sail"
    request_delay = 1.0
    max_pages = 1  # fixture is single-page; revisit if live site paginates

    def parse_person_cards(self, response: Any) -> list[Any]:
        return list(response.css("div.person-card"))

    def extract_person(self, card: Any) -> RawPersonDraft:
        def _text(selector: str) -> str | None:
            nodes = card.css(selector)
            if not nodes:
                return None
            text = nodes[0].text.strip() if hasattr(nodes[0], "text") else str(nodes[0]).strip()
            return text or None

        def _attr(selector: str, attr: str) -> str | None:
            nodes = card.css(selector)
            if not nodes:
                return None
            value = nodes[0].attrib.get(attr)
            return value.strip() if value else None

        name_raw = _text("a.person-name")
        title_raw = _text("span.person-title")
        email_raw = _text("a.person-email")
        homepage_url = _attr("a.person-homepage", "href")
        avatar_url = _attr("img.person-avatar", "src")
        source_url = _attr("a.person-name", "href")

        if not name_raw:
            raise ValueError("person card missing name")

        return RawPersonDraft(
            name_raw=name_raw,
            title_raw=title_raw,
            email_raw=email_raw,
            homepage_url=homepage_url,
            avatar_url=avatar_url,
            source_url=source_url,
        )

    def get_next_page_url(self, response: Any) -> str | None:
        # SAIL fixture is single-page; return None.
        return None
