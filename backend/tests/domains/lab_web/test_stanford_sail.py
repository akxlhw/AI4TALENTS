"""Parsing tests for the StanfordSailCollector.

The fixture is a 5-card snapshot of the REAL ai.stanford.edu/faculty/ DOM
(captured 2026-06-29), so these tests verify the selectors against actual
markup, not a fabricated structure.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.domains.lab_web.services.collectors.labs.stanford_sail import (
    StanfordSailCollector,
)

pytestmark = pytest.mark.unit

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "lab_web" / "stanford_sail_people.html"


@pytest.fixture
def response():
    """Return a real Scrapling Selector, exactly what ScraplingFetcher.fetch yields.

    This is the contract test for C1: the collector hooks must work against the
    actual Selector type (response.css(...)), not a faked wrapper.
    """
    from scrapling.parser import Selector

    return Selector(FIXTURE.read_text(encoding="utf-8"))


def _make_collector():
    # Hooks operate on the Scrapling Selector; repo/person_service unused here.
    return StanfordSailCollector(fetcher=None, lab=None, repo=None, person_service=None)


def test_parse_person_cards_finds_five(response):
    c = _make_collector()
    cards = c.parse_person_cards(response)
    assert len(cards) == 5


def test_extract_first_faculty(response):
    c = _make_collector()
    cards = c.parse_person_cards(response)
    draft = c.extract_person(cards[0])
    assert draft.name_raw == "Gill Bejerano"
    # SAIL listing page exposes no job title and no email.
    assert draft.title_raw is None
    assert draft.email_raw is None
    assert draft.homepage_url == "http://bejerano.stanford.edu/"
    assert draft.avatar_url is not None and draft.avatar_url.endswith("gill-bejerano.png")
    # research area is carried in extra, not as a title.
    assert draft.extra is not None
    assert "Genomics" in (draft.extra.get("research_area") or "")


def test_extract_third_faculty_has_name_and_homepage(response):
    c = _make_collector()
    cards = c.parse_person_cards(response)
    draft = c.extract_person(cards[2])
    assert draft.name_raw == "Emma Brunskill"
    assert draft.homepage_url  # every faculty card has a bio link


def test_no_pagination(response):
    c = _make_collector()
    assert c.get_next_page_url(response) is None
