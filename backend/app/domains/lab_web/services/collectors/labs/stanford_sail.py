"""Stanford SAIL faculty-page collector.

Selectors now target the REAL ai.stanford.edu/faculty/ DOM, verified against a
5-person snapshot captured from the live site on 2026-06-29
(tests/fixtures/lab_web/stanford_sail_people.html).

Real DOM structure per faculty card (a div.row containing .name + .position):
    <div class="row">
      <div class="col-12">
        <div class="img-wrap"><img class="team-img" src="..."></div>
        <div class="text-wrap">
          <h3 class="name">Gill Bejerano</h3>
          <div class="position">
            <div class="category">Computational &amp; Experimental Genomics</div>
            <a class="link-bio" href="http://bejerano.stanford.edu/">Read More</a>
          </div>
        </div>
      </div>
    </div>

Field mapping caveats for SAIL specifically:
- The listing page exposes NO job title (no "Professor" text) and NO email.
  So title_raw and email_raw are always None for SAIL; role_type falls back to
  UNKNOWN. The .category div is a research area, stored in extra, not a title.
- The registry people_url for SAIL must point at /faculty/ (the /people/ path
  403s). Title/email could be recovered later by following each link-bio into
  the personal page — out of scope for v1.
"""

from __future__ import annotations

from typing import Any

from app.domains.lab_web.services.collectors.base_collector import (
    BaseLabCollector,
    RawPersonDraft,
)


class StanfordSailCollector(BaseLabCollector):
    """Collector for https://ai.stanford.edu/faculty/."""

    lab_code = "stanford_sail"
    request_delay = 1.0
    max_pages = 1  # faculty listing is single-page

    def parse_person_cards(self, response: Any) -> list[Any]:
        # A real card is a div.row that contains both a .name and a .position.
        return [row for row in response.css("div.row") if row.css(".name") and row.css(".position")]

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

        name_raw = _text("h3.name")
        research_area = _text("div.category")
        homepage_url = _attr("a.link-bio", "href")
        avatar_url = _attr("img.team-img", "src")

        if not name_raw:
            raise ValueError("faculty card missing name")

        return RawPersonDraft(
            name_raw=name_raw,
            # SAIL listing has no job title; research_area is NOT a title.
            title_raw=None,
            email_raw=None,
            homepage_url=homepage_url,
            avatar_url=avatar_url,
            source_url=homepage_url,
            extra={"research_area": research_area},
        )

    def get_next_page_url(self, response: Any) -> str | None:
        return None
