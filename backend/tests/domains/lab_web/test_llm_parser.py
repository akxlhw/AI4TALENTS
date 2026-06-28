"""Tests for llm_parser (LLM call + Pydantic schema validation). Mocks LLMGateway."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from app.domains.lab_web.schemas.lab_web_site import ParsedPerson
from app.domains.lab_web.services.collectors.llm_parser import (
    parse_persons_from_html,
)

pytestmark = pytest.mark.unit

SYSTEM_PROMPT = "test prompt"


def _mock_gateway(content: str):
    gw = MagicMock()
    gw.complete = AsyncMock(return_value=MagicMock(content=content, tokens_used=42))
    return gw


async def test_parse_valid_json():
    gw = _mock_gateway(
        '[{"name": "Alice Lee", "role_section": "PhD Students", "homepage": "https://alice.example", "department": "CS"}]'
    )
    result = await parse_persons_from_html(gw, "some html", SYSTEM_PROMPT)
    assert result.ok is True
    assert len(result.persons) == 1
    assert result.persons[0].name == "Alice Lee"
    assert result.persons[0].role_section == "PhD Students"
    assert result.tokens_used == 42


async def test_parse_empty_array_flagged():
    gw = _mock_gateway("[]")
    result = await parse_persons_from_html(gw, "some html", SYSTEM_PROMPT)
    assert result.ok is False
    assert result.error


async def test_parse_invalid_json_flagged():
    gw = _mock_gateway("not json at all {")
    result = await parse_persons_from_html(gw, "some html", SYSTEM_PROMPT)
    assert result.ok is False
    assert result.error


async def test_parse_missing_name_flagged():
    gw = _mock_gateway('[{"role_section": "Faculty"}]')
    result = await parse_persons_from_html(gw, "some html", SYSTEM_PROMPT)
    assert result.ok is False


async def test_parse_retries_once_then_fails():
    gw = MagicMock()
    gw.complete = AsyncMock(side_effect=Exception("LLM down"))
    result = await parse_persons_from_html(gw, "some html", SYSTEM_PROMPT)
    assert result.ok is False
    assert gw.complete.await_count == 2


async def test_parse_tolerates_code_fences():
    gw = _mock_gateway('```json\n[{"name": "Bob"}]\n```')
    result = await parse_persons_from_html(gw, "some html", SYSTEM_PROMPT)
    assert result.ok is True
    assert result.persons[0].name == "Bob"


class TestParsedPersonSchema:
    def test_valid(self):
        p = ParsedPerson(name="Bob", role_section="Faculty", homepage="https://b.example", department="EE")
        assert p.name == "Bob"

    def test_blank_name_rejected(self):
        with pytest.raises(ValidationError):
            ParsedPerson(name="   ")

    def test_invalid_homepage_rejected(self):
        with pytest.raises(ValidationError):
            ParsedPerson(name="Bob", homepage="not-a-url")

    def test_none_homepage_ok(self):
        p = ParsedPerson(name="Bob", homepage=None)
        assert p.homepage is None
