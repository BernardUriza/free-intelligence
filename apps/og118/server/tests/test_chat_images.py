"""OG118-IMAGE-UPLOAD-1 — /chat/stream vision input.

Pins the consumer seam: request `images` reach `Runner.run_stream(images=...)`
as plain {media_type, data} dicts, an image-only send (empty message) is valid,
the boundary validation (media type allowlist, count cap, base64/size checks)
rejects hostile payloads as 422 before the runner, and an external-engine
element refuses images with an in-stream error instead of silently answering
text-only. The model-side folding is covered in fi-runner's test_images.py.
"""

from __future__ import annotations

import base64
from collections.abc import AsyncIterator
from types import SimpleNamespace

import app as app_module
from fastapi.testclient import TestClient

JPEG_B64 = base64.b64encode(b"not-really-a-jpeg-but-valid-b64").decode()


class _SpyRunner:
    """Records the kwargs the route handed run_stream; yields one result event."""

    def __init__(self) -> None:
        self.seen: dict = {}

    async def run_stream(
        self, message, *, session_id=None, request_id=None, history=None, context=None, images=None
    ) -> AsyncIterator[dict]:  # noqa: ANN001
        self.seen = {"message": message, "images": images}
        yield {"type": "result", "result": {"text": "ok"}}


def _client(monkeypatch) -> tuple[_SpyRunner, TestClient]:
    spy = _SpyRunner()
    monkeypatch.setattr(app_module, "_runner", spy)
    return spy, TestClient(app_module.app)


def test_chat_stream_forwards_images_to_the_runner(monkeypatch) -> None:
    spy, client = _client(monkeypatch)
    resp = client.post(
        "/chat/stream",
        json={
            "message": "¿qué dice esta foto?",
            "images": [{"media_type": "image/jpeg", "data": JPEG_B64}],
        },
    )
    assert resp.status_code == 200
    assert spy.seen["images"] == [{"media_type": "image/jpeg", "data": JPEG_B64}]


def test_chat_stream_image_only_send_is_valid(monkeypatch) -> None:
    spy, client = _client(monkeypatch)
    resp = client.post(
        "/chat/stream",
        json={"message": "", "images": [{"media_type": "image/png", "data": JPEG_B64}]},
    )
    assert resp.status_code == 200
    assert spy.seen["message"] == ""
    assert spy.seen["images"][0]["media_type"] == "image/png"


def test_chat_stream_without_images_passes_none(monkeypatch) -> None:
    spy, client = _client(monkeypatch)
    resp = client.post("/chat/stream", json={"message": "hola"})
    assert resp.status_code == 200
    assert spy.seen["images"] is None


def test_rejects_unknown_media_type(monkeypatch) -> None:
    _, client = _client(monkeypatch)
    resp = client.post(
        "/chat/stream",
        json={"message": "x", "images": [{"media_type": "application/pdf", "data": JPEG_B64}]},
    )
    assert resp.status_code == 422


def test_rejects_invalid_base64(monkeypatch) -> None:
    _, client = _client(monkeypatch)
    resp = client.post(
        "/chat/stream",
        json={"message": "x", "images": [{"media_type": "image/jpeg", "data": "no vale!!"}]},
    )
    assert resp.status_code == 422


def test_rejects_too_many_images(monkeypatch) -> None:
    _, client = _client(monkeypatch)
    too_many = [{"media_type": "image/jpeg", "data": JPEG_B64}] * (
        app_module.MAX_IMAGES_PER_MESSAGE + 1
    )
    resp = client.post("/chat/stream", json={"message": "x", "images": too_many})
    assert resp.status_code == 422


def test_rejects_oversized_image(monkeypatch) -> None:
    _, client = _client(monkeypatch)
    huge = "A" * (app_module._MAX_IMAGE_B64_CHARS + 4)
    resp = client.post(
        "/chat/stream", json={"message": "x", "images": [{"media_type": "image/jpeg", "data": huge}]}
    )
    assert resp.status_code == 422


def test_external_element_refuses_images_in_stream(monkeypatch) -> None:
    spy, client = _client(monkeypatch)
    external_element = SimpleNamespace(
        id="element-008-o-oxigeno",
        display_label="8 · O · Oxígeno",
        display_name="Oxígeno",
        symbol="O",
        engine_label="Vultur",
        engine_binding=SimpleNamespace(is_external=True, persona_id="vultur"),
    )
    monkeypatch.setattr(
        app_module, "_runner_and_element", lambda token: (spy, external_element)
    )
    resp = client.post(
        "/chat/stream",
        json={
            "message": "mira",
            "element": "oxigeno",
            "images": [{"media_type": "image/jpeg", "data": JPEG_B64}],
        },
    )
    assert resp.status_code == 200
    body = resp.text
    assert '"type": "error"' in body
    assert "no acepta im" in body  # the human-readable refusal
    assert spy.seen == {}  # the runner never ran
