"""Tests for `personas.insult.core.image_transcript` (v4.21.117).

The durable trace for image attachments: Postgres only stores text, so an
image-only message persisted as an empty row and every future turn rebuilt
context with no record the image ever existed — the 2026-07-05 incident
(a prescription/treatment-schedule image re-sent "mil veces", re-hallucinated
every time). These tests pin the best-effort contract: transcript appended
to the stored row, and every failure path degrading to a no-op instead of
touching the turn.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from personas.insult.core.image_transcript import (
    TRANSCRIPT_MAX_CHARS,
    persist_image_transcript,
    transcribe_images,
)

IMAGE_BLOCK = {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "AAAA"}}


def _judge(text: str | None = "1. Receta: HCQ 200mg, prednisona 5mg x3"):
    judge = AsyncMock()
    response = AsyncMock()
    response.text = text
    judge.utility_call = AsyncMock(return_value=response)
    return judge


@pytest.mark.asyncio
async def test_transcribe_returns_judge_text():
    judge = _judge()
    result = await transcribe_images([IMAGE_BLOCK], judge_client=judge)
    assert result == "1. Receta: HCQ 200mg, prednisona 5mg x3"
    messages = judge.utility_call.call_args.args[1]
    content = messages[0]["content"]
    assert content[0]["type"] == "text"
    assert IMAGE_BLOCK in content


@pytest.mark.asyncio
async def test_transcribe_no_blocks_returns_none_without_calling_judge():
    """Resistance: a text-only turn must never spend a judge call."""
    judge = _judge()
    assert await transcribe_images([], judge_client=judge) is None
    judge.utility_call.assert_not_called()


@pytest.mark.asyncio
async def test_transcribe_judge_failure_returns_none():
    """Best-effort: a dead/timing-out runner degrades to no transcript,
    never an exception into the background task."""
    judge = AsyncMock()
    judge.utility_call = AsyncMock(side_effect=RuntimeError("runner down"))
    assert await transcribe_images([IMAGE_BLOCK], judge_client=judge) is None


@pytest.mark.asyncio
async def test_transcribe_empty_judge_text_returns_none():
    assert await transcribe_images([IMAGE_BLOCK], judge_client=_judge("  ")) is None


@pytest.mark.asyncio
async def test_transcribe_caps_length():
    result = await transcribe_images([IMAGE_BLOCK], judge_client=_judge("x" * (TRANSCRIPT_MAX_CHARS + 500)))
    assert result is not None
    assert len(result) == TRANSCRIPT_MAX_CHARS


@pytest.mark.asyncio
async def test_persist_appends_marked_transcript():
    memory = AsyncMock()
    memory.append_to_message = AsyncMock(return_value=True)
    await persist_image_transcript(_judge(), memory, "msg_123", [IMAGE_BLOCK])
    memory.append_to_message.assert_awaited_once()
    discord_id, suffix = memory.append_to_message.call_args.args
    assert discord_id == "msg_123"
    assert suffix == "[Imagen adjunta: 1. Receta: HCQ 200mg, prednisona 5mg x3]"


@pytest.mark.asyncio
async def test_persist_skips_append_when_transcript_failed():
    """Resistance: no transcript → the stored row stays untouched."""
    judge = AsyncMock()
    judge.utility_call = AsyncMock(side_effect=RuntimeError("boom"))
    memory = AsyncMock()
    await persist_image_transcript(judge, memory, "msg_123", [IMAGE_BLOCK])
    memory.append_to_message.assert_not_called()


@pytest.mark.asyncio
async def test_persist_swallows_append_failure():
    """A DB failure on the append logs and returns — background tasks
    must never propagate into the task set as unhandled errors."""
    memory = AsyncMock()
    memory.append_to_message = AsyncMock(side_effect=RuntimeError("pg down"))
    await persist_image_transcript(_judge(), memory, "msg_123", [IMAGE_BLOCK])
