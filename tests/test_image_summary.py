"""Tests for insult.core.image_summary — the Haiku-vision-backed memory aid.

The module is deliberately best-effort: any failure returns None so the caller
can fall back to plain text storage. These tests lock in that contract."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from insult.core.image_summary import summarize_images
from insult.core.llm import LLMResponse


def _mk_image_block(data: str = "fakebase64") -> dict:
    """A minimal Claude API-shaped image block."""
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": "image/png", "data": data},
    }


def _mk_llm_with_text(text: str) -> MagicMock:
    """Mock LLMClient.utility_call that returns the given text."""
    llm = MagicMock()
    llm.utility_call = AsyncMock(return_value=LLMResponse(text=text, stop_reason="end_turn"))
    return llm


@pytest.mark.asyncio
async def test_returns_description_for_valid_images():
    """Happy path: one image → Haiku returns a line → function returns it verbatim."""
    llm = _mk_llm_with_text("1. Gráfica de barras trimestrales.")
    result = await summarize_images(
        [_mk_image_block()],
        llm=llm,
        model="claude-haiku-4-5-20251001",
    )
    assert result == "1. Gráfica de barras trimestrales."
    # Haiku was actually called — not silently short-circuited.
    assert llm.utility_call.await_count == 1
    call_kwargs = llm.utility_call.await_args.kwargs
    assert call_kwargs["model"] == "claude-haiku-4-5-20251001"
    # The image block was included in the content payload sent to Claude.
    sent_content = llm.utility_call.await_args.args[1][0]["content"]
    assert any(c.get("type") == "image" for c in sent_content)


@pytest.mark.asyncio
async def test_empty_list_returns_none_without_api_call():
    """No images → no Haiku call, no tokens burned, return None."""
    llm = _mk_llm_with_text("should not be called")
    result = await summarize_images(
        [],
        llm=llm,
        model="claude-haiku-4-5-20251001",
    )
    assert result is None
    assert llm.utility_call.await_count == 0


@pytest.mark.asyncio
async def test_api_error_returns_none_without_raising():
    """Haiku call explodes → function swallows and returns None so the
    caller can fall back to plain text. No crash bubbles to _respond."""
    llm = MagicMock()
    llm.utility_call = AsyncMock(side_effect=RuntimeError("kaboom"))
    result = await summarize_images(
        [_mk_image_block()],
        llm=llm,
        model="claude-haiku-4-5-20251001",
    )
    assert result is None


@pytest.mark.asyncio
async def test_empty_text_response_returns_none():
    """Haiku returns an empty string → treat as 'no useful description', return None."""
    llm = _mk_llm_with_text("   ")
    result = await summarize_images(
        [_mk_image_block()],
        llm=llm,
        model="claude-haiku-4-5-20251001",
    )
    assert result is None
