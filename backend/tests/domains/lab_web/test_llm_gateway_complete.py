"""Tests for LLMGateway.complete (the generic chat method added for v2)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domains.shared.services.llm.llm_gateway import LLMGateway

pytestmark = pytest.mark.unit


def _make_gateway_with_mock_client(response_content: str) -> tuple[LLMGateway, MagicMock]:
    """Build a gateway whose OpenAI client is mocked to return response_content."""
    gw = LLMGateway(
        api_key="test-key",
        api_base="https://api.test.example",
        model="test-model",
        api_format="openai",
    )
    mock_choice = MagicMock()
    mock_choice.message.content = response_content
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=20, total_tokens=30)
    gw.client = MagicMock()
    gw.client.chat = MagicMock()
    gw.client.chat.completions = MagicMock()
    gw.client.chat.completions.create = AsyncMock(return_value=mock_response)
    return gw, mock_response


async def test_complete_returns_content_string():
    gw, _ = _make_gateway_with_mock_client('{"name": "Alice"}')
    messages = [{"role": "user", "content": "hi"}]
    result = await gw.complete(messages)
    assert result.content == '{"name": "Alice"}'


async def test_complete_passes_temperature_and_json_mode():
    gw, _ = _make_gateway_with_mock_client("{}")
    messages = [{"role": "user", "content": "hi"}]
    await gw.complete(messages, temperature=0.2, json_mode=True)
    gw.client.chat.completions.create.assert_awaited_once()
    call_kwargs = gw.client.chat.completions.create.await_args.kwargs
    assert call_kwargs["temperature"] == 0.2
    assert call_kwargs.get("response_format") == {"type": "json_object"}


async def test_complete_returns_token_usage():
    gw, _ = _make_gateway_with_mock_client("{}")
    result = await gw.complete([{"role": "user", "content": "hi"}])
    assert result.tokens_used == 30


async def test_complete_raises_on_empty_response():
    gw, _ = _make_gateway_with_mock_client("")
    with pytest.raises(Exception):
        await gw.complete([{"role": "user", "content": "hi"}])
