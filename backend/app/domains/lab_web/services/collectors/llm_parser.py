"""LLM call + Pydantic schema validation for lab-site People-page parsing."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from pydantic import TypeAdapter, ValidationError

from app.domains.lab_web.schemas.lab_web_site import ParsedPerson

logger = logging.getLogger(__name__)

_persons_adapter: TypeAdapter[list[ParsedPerson]] = TypeAdapter(list[ParsedPerson])


@dataclass
class ParseResult:
    """Outcome of one LLM parse attempt (after retries)."""

    ok: bool
    persons: list[ParsedPerson] | None = None
    error: str = ""
    tokens_used: int = 0


async def parse_persons_from_html(
    llm_gateway: Any,
    html: str,
    system_prompt: str,
) -> ParseResult:
    """Call the LLM, validate output against ParsedPerson schema, retry once.

    Returns ParseResult(ok=False) on schema failure after one retry, or when the
    LLM returns zero persons (a People page should have people).
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": html},
    ]
    last_error = ""
    for attempt in range(2):  # initial + 1 retry
        try:
            result = await llm_gateway.complete(messages, temperature=0.1, json_mode=False)
            content = result.content.strip()
            # Tolerate markdown code fences around JSON.
            if content.startswith("```"):
                content = content.strip("`")
                if content.lower().startswith("json"):
                    content = content[4:]
            persons = _persons_adapter.validate_json(content)
            if not persons:
                return ParseResult(
                    ok=False,
                    error="LLM returned 0 persons (empty array)",
                    tokens_used=result.tokens_used,
                )
            return ParseResult(ok=True, persons=persons, tokens_used=result.tokens_used)
        except (ValidationError, ValueError, json.JSONDecodeError) as exc:
            last_error = f"schema/parse error: {exc}"
            logger.warning("LLM parse attempt %d failed: %s", attempt + 1, last_error)
        except Exception as exc:
            last_error = f"LLM call error: {exc}"
            logger.warning("LLM call attempt %d failed: %s", attempt + 1, last_error)
    return ParseResult(ok=False, error=last_error)
