"""Parsing tests for the StanfordSailCollector (offline, against fixture HTML)."""

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


def test_parse_person_cards_finds_three(response):
    c = _make_collector()
    cards = c.parse_person_cards(response)
    assert len(cards) == 3


def test_extract_professor(response):
    c = _make_collector()
    cards = c.parse_person_cards(response)
    draft = c.extract_person(cards[0])
    assert draft.name_raw == "John Smith"
    assert draft.title_raw == "Assistant Professor"
    assert draft.email_raw is not None and "john" in draft.email_raw.lower()
    assert draft.homepage_url == "https://john.cs.stanford.edu"
    assert draft.avatar_url == "https://ai.stanford.edu/img/john.jpg"


def test_extract_phd_student(response):
    c = _make_collector()
    cards = c.parse_person_cards(response)
    draft = c.extract_person(cards[1])
    assert draft.name_raw == "Jane Doe"
    assert draft.title_raw == "PhD Candidate"


def test_extract_postdoc_missing_email(response):
    c = _make_collector()
    cards = c.parse_person_cards(response)
    draft = c.extract_person(cards[2])
    assert draft.name_raw == "Bob Lee"
    assert draft.title_raw == "Postdoctoral Researcher"
    assert draft.email_raw is None  # no email node present


def test_no_pagination(response):
    c = _make_collector()
    assert c.get_next_page_url(response) is None
