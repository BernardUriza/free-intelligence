"""Tests for vision input — TurnImage through Runner.run/run_stream into the
backend (OG118-IMAGE-UPLOAD-1).

The contract: images attach to the CURRENT turn only; a text-only turn calls
the backend with the exact pre-images signature (no ``images`` kwarg at all);
an image-only turn (empty text) is valid; a vision-less backend fails LOUD
instead of silently answering without the picture.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from fi_runner import BackendError, Runner, TurnImage, TurnResult
from fi_runner.backends import ClaudeCodeBackend

JPEG = TurnImage(media_type="image/jpeg", data="aGVsbG8=")
PNG = TurnImage(media_type="image/png", data="d29ybGQ=")


@dataclass
class _CapturingBackend:
    """Streaming backend that records every kwarg each turn receives."""

    calls: list[dict[str, Any]] = field(default_factory=list)

    async def run_turn(self, **kwargs) -> TurnResult:  # noqa: ANN003
        self.calls.append(kwargs)
        return TurnResult(text="ok")

    async def run_turn_stream(self, **kwargs):  # noqa: ANN003
        self.calls.append(kwargs)
        yield {"type": "text", "text": "ok"}
        yield {"type": "result", "result": TurnResult(text="ok")}


# --- TurnImage.from_any ------------------------------------------------------


def test_from_any_passes_instances_through():
    assert TurnImage.from_any(JPEG) is JPEG


def test_from_any_coerces_snake_and_camel_mappings():
    assert TurnImage.from_any({"media_type": "image/png", "data": "eA=="}) == TurnImage(
        media_type="image/png", data="eA=="
    )
    assert TurnImage.from_any({"mediaType": "image/png", "data": "eA=="}) == TurnImage(
        media_type="image/png", data="eA=="
    )


@pytest.mark.parametrize("bad", [None, 42, "raw", {}, {"media_type": "image/png"}, {"data": "eA=="}])
def test_from_any_rejects_untypeable_input(bad):
    with pytest.raises(ValueError, match="TurnImage"):
        TurnImage.from_any(bad)


# --- Runner passthrough ------------------------------------------------------


@pytest.mark.asyncio
async def test_run_stream_passes_images_to_backend():
    backend = _CapturingBackend()
    runner = Runner(backend=backend, persona="p", flow_narrator=None)
    _ = [ev async for ev in runner.run_stream("mira", images=[JPEG, PNG])]
    assert backend.calls[0]["images"] == [JPEG, PNG]


@pytest.mark.asyncio
async def test_run_stream_coerces_raw_mappings():
    backend = _CapturingBackend()
    runner = Runner(backend=backend, persona="p", flow_narrator=None)
    _ = [ev async for ev in runner.run_stream("mira", images=[{"media_type": "image/jpeg", "data": "aGk="}])]
    assert backend.calls[0]["images"] == [TurnImage(media_type="image/jpeg", data="aGk=")]


@pytest.mark.asyncio
async def test_text_only_turn_omits_the_images_kwarg_entirely():
    # The kwarg exists only on image turns — a fake/legacy backend whose
    # signature has no ``images`` keeps working for every text-only turn.
    backend = _CapturingBackend()
    runner = Runner(backend=backend, persona="p", flow_narrator=None)
    _ = [ev async for ev in runner.run_stream("hola")]
    await runner.run("hola de nuevo")
    assert all("images" not in call for call in backend.calls)


@pytest.mark.asyncio
async def test_image_only_turn_is_valid_but_empty_turn_still_rejects():
    backend = _CapturingBackend()
    runner = Runner(backend=backend, persona="p", flow_narrator=None)
    _ = [ev async for ev in runner.run_stream("", images=[JPEG])]  # picture IS the message
    assert backend.calls[0]["images"] == [JPEG]
    with pytest.raises(ValueError, match="user_message"):
        _ = [ev async for ev in runner.run_stream("   ")]


@pytest.mark.asyncio
async def test_run_passes_images_and_emits_light_telemetry():
    events: list[tuple[str, dict]] = []
    backend = _CapturingBackend()
    runner = Runner(
        backend=backend, persona="p", flow_narrator=None,
        on_event=lambda e, f: events.append((e, f)),
    )
    await runner.run("mira", images=[JPEG])
    assert backend.calls[0]["images"] == [JPEG]
    attached = [f for e, f in events if e == "images_attached"]
    assert attached and attached[0]["count"] == 1
    assert attached[0]["media_types"] == ["image/jpeg"]
    # Telemetry never carries the bytes.
    assert "data" not in attached[0] and "aGVsbG8=" not in str(attached[0])


# --- ClaudeCodeBackend query input (SDK-free builder) -------------------------


def test_build_query_input_text_only_stays_a_plain_string():
    assert ClaudeCodeBackend.build_query_input("hola", None) == "hola"
    assert ClaudeCodeBackend.build_query_input("hola", []) == "hola"


def test_build_query_input_images_before_text_blocks():
    blocks = ClaudeCodeBackend.build_query_input("¿qué es esto?", [JPEG, PNG])
    assert [b["type"] for b in blocks] == ["image", "image", "text"]
    assert blocks[0]["source"] == {"type": "base64", "media_type": "image/jpeg", "data": "aGVsbG8="}
    assert blocks[2] == {"type": "text", "text": "¿qué es esto?"}


def test_build_query_input_image_only_skips_the_text_block():
    blocks = ClaudeCodeBackend.build_query_input("  ", [PNG])
    assert [b["type"] for b in blocks] == ["image"]


# --- Vision-less backends fail loud -------------------------------------------


@pytest.mark.asyncio
async def test_subprocess_cli_backend_rejects_images():
    from fi_runner import CodexBackend

    backend = CodexBackend()
    with pytest.raises(BackendError, match="image"):
        await backend.run_turn(
            system_prompt="p", user_message="hola", mcp_servers=[],
            tool_policy=None, images=[JPEG],
        )
