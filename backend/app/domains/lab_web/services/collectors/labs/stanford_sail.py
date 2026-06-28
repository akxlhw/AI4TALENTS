"""Stanford SAIL People-page collector.

Selectors target the simplified fixture structure in
tests/fixtures/lab_web/stanford_sail_people.html. When wiring against the
live site, re-derive selectors from the live DOM and refresh the fixture.
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
        return response.selector.css("div.person-card")

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
