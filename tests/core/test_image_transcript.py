"""An image must leave a trace once its turn is over.

An image reaches the model as base64 inside ONE live turn and then evaporates —
the stored row keeps the words and nothing else, so the persona is blind to it
two days later. The sink survived the purge fully wired and tested
(`append_to_message`), and the runner's JudgeRequest grew `attachments` in
v4.21.117 explicitly for this. Only the PRODUCER died — this is its guard.

Resistance cases matter: this fires on every image-bearing turn and spends a
judge call, so a false fire is real cost, and any fault must cost the trace and
never the turn (the reply is already delivered when it runs).
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from persona_gateway.vision import ImageTranscriber

IMAGE = {
    "type": "image",
    "source": {"type": "url", "url": "https://cdn.discordapp.com/attachments/1/2/a.png?ex=ffffffff&is=0&hm=abc"},
}
TEXT_BLOCK = {"type": "text", "text": "mira esto"}
DOC = {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": "b"}}


def _judge(text: str = "Captura de una receta: hidroxicloroquina 200mg cada 12h.") -> MagicMock:
    j = MagicMock()
    j.utility_call = AsyncMock(return_value=SimpleNamespace(text=text, stop_reason="end_turn"))
    return j


def _transcriber() -> tuple[ImageTranscriber, MagicMock, set]:
    memory = MagicMock()
    memory.append_to_message = AsyncMock(return_value=True)
    tasks: set[asyncio.Task] = set()
    return ImageTranscriber(memory, tasks), memory, tasks


async def _drain(tasks: set[asyncio.Task]) -> None:
    if tasks:
        await asyncio.gather(*list(tasks), return_exceptions=True)


async def test_image_transcript_is_appended_to_the_stored_row():
    t, memory, tasks = _transcriber()
    judge = _judge()
    t.spawn(judge, "msg-1", [TEXT_BLOCK, IMAGE])
    await _drain(tasks)
    memory.append_to_message.assert_awaited_once()
    msg_id, suffix = memory.append_to_message.await_args.args
    assert msg_id == "msg-1"
    assert suffix.startswith("[Imagen adjunta: ")
    assert "hidroxicloroquina 200mg" in suffix, "el texto clínico legible debe sobrevivir"


async def test_the_image_block_reaches_the_judge():
    """The judge must actually SEE the image — a text-only call would invent."""
    t, _, tasks = _transcriber()
    judge = _judge()
    t.spawn(judge, "msg-1", [IMAGE])
    await _drain(tasks)
    _, messages = judge.utility_call.await_args.args
    blocks = messages[0]["content"]
    assert any(b.get("type") == "image" for b in blocks)


async def test_every_image_of_a_multi_image_message_is_transcribed():
    t, memory, tasks = _transcriber()
    t.spawn(_judge(), "msg-1", [IMAGE, IMAGE, IMAGE])
    await _drain(tasks)
    assert memory.append_to_message.await_count == 3


async def test_no_images_no_judge_call():
    """RESISTANCE: a text-only turn must not spend a vision call."""
    t, memory, tasks = _transcriber()
    judge = _judge()
    t.spawn(judge, "msg-1", [TEXT_BLOCK])
    await _drain(tasks)
    judge.utility_call.assert_not_awaited()
    memory.append_to_message.assert_not_awaited()


async def test_documents_are_not_treated_as_images():
    """RESISTANCE: only `type: image` — a PDF is a different lane."""
    t, memory, tasks = _transcriber()
    judge = _judge()
    t.spawn(judge, "msg-1", [DOC])
    await _drain(tasks)
    judge.utility_call.assert_not_awaited()
    assert not memory.append_to_message.await_count


async def test_without_a_judge_client_it_is_a_noop():
    """RESISTANCE: no judge wired → silently off, never a crash."""
    t, memory, tasks = _transcriber()
    t.spawn(None, "msg-1", [IMAGE])
    await _drain(tasks)
    memory.append_to_message.assert_not_awaited()


async def test_a_judge_fault_never_raises_into_the_turn():
    """RESISTANCE: the reply already shipped; a vision fault costs the trace only."""
    t, memory, tasks = _transcriber()
    judge = MagicMock()
    judge.utility_call = AsyncMock(side_effect=RuntimeError("runner down"))
    t.spawn(judge, "msg-1", [IMAGE])
    await _drain(tasks)
    memory.append_to_message.assert_not_awaited()


async def test_an_empty_description_is_not_stored():
    """RESISTANCE: an empty '[Imagen adjunta: ]' is noise in the transcript."""
    t, memory, tasks = _transcriber()
    t.spawn(_judge(text="   "), "msg-1", [IMAGE])
    await _drain(tasks)
    memory.append_to_message.assert_not_awaited()


async def test_a_runaway_description_is_capped():
    t, memory, tasks = _transcriber()
    t.spawn(_judge(text="x" * 5000), "msg-1", [IMAGE])
    await _drain(tasks)
    _, suffix = memory.append_to_message.await_args.args
    assert len(suffix) < 700


@pytest.mark.parametrize("bad_id", ["", None])
async def test_without_a_message_id_there_is_nowhere_to_append(bad_id):
    """RESISTANCE: the append is keyed on the Discord id — no key, no call."""
    t, _memory, tasks = _transcriber()
    judge = _judge()
    t.spawn(judge, bad_id, [IMAGE])
    await _drain(tasks)
    judge.utility_call.assert_not_awaited()
