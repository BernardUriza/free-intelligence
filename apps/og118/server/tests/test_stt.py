"""Tests for the og118 STT foundation (B3-VOICE-BACKEND-2).

Two layers, mirroring test_tts.py:
  * Provider unit tests (stt.py) — validation, config-from-env, request
    construction and secret hygiene, driven by httpx.MockTransport so NOTHING
    touches the network and NO real key is ever needed.
  * Route contract tests (app.py) — the /stt/transcribe HTTP surface: explicit
    503 when unconfigured, 400 on bad input, 200 + {text} on success, 401 behind
    the bearer gate, and the invariant that error bodies never echo a secret.

The fake provider deliberately does NOT mask the fact that a real Azure OpenAI
Whisper deployment is required in staging: `test_unconfigured_returns_503` proves
the gate, and the provider-construction test proves the real call shape.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient

import app as app_module
import stt as stt_module

FAKE_AUDIO = b"OggS\x00fake-webm-opus-payload" + b"\x00" * 100
FAKE_KEY = "sk-test-do-not-leak-1234567890"


# --- Provider-layer unit tests (no network, no real secret) -------------------


def test_validate_audio_rejects_empty() -> None:
    with pytest.raises(stt_module.STTValidationError):
        stt_module.validate_audio(b"")


def test_validate_audio_rejects_too_short() -> None:
    with pytest.raises(stt_module.STTValidationError):
        stt_module.validate_audio(b"\x00" * (stt_module.MIN_AUDIO_BYTES - 1))


def test_validate_audio_rejects_too_large() -> None:
    with pytest.raises(stt_module.STTValidationError):
        stt_module.validate_audio(b"\x00" * (stt_module.MAX_AUDIO_BYTES + 1))


def test_validate_audio_accepts_reasonable_chunk() -> None:
    stt_module.validate_audio(FAKE_AUDIO)  # does not raise


def test_config_from_env_none_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("OG118_STT_ENDPOINT", "OG118_STT_API_KEY", "OG118_STT_DEPLOYMENT"):
        monkeypatch.delenv(key, raising=False)
    assert stt_module.STTConfig.from_env() is None


def test_config_from_env_none_when_partial(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OG118_STT_ENDPOINT", "https://x.openai.azure.com")
    monkeypatch.setenv("OG118_STT_API_KEY", FAKE_KEY)
    monkeypatch.delenv("OG118_STT_DEPLOYMENT", raising=False)  # missing the trio's 3rd
    assert stt_module.STTConfig.from_env() is None


def test_config_from_env_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OG118_STT_ENDPOINT", "https://x.openai.azure.com/")  # trailing slash trimmed
    monkeypatch.setenv("OG118_STT_API_KEY", FAKE_KEY)
    monkeypatch.setenv("OG118_STT_DEPLOYMENT", "whisper")
    cfg = stt_module.STTConfig.from_env()
    assert cfg is not None
    assert cfg.endpoint == "https://x.openai.azure.com"  # no trailing slash
    assert cfg.deployment == "whisper"
    assert cfg.model == "whisper"  # defaults to deployment
    assert cfg.api_version  # has a default


def _provider_with_mock(handler) -> stt_module.AzureOpenAISTTProvider:
    cfg = stt_module.STTConfig(
        endpoint="https://x.openai.azure.com",
        api_key=FAKE_KEY,
        deployment="whisper",
        api_version="2024-06-01",
        model="whisper",
    )
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return stt_module.AzureOpenAISTTProvider(cfg, client=client)


def test_provider_builds_correct_request_and_returns_text() -> None:
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["api_key"] = request.headers.get("api-key")
        seen["body"] = request.content  # raw multipart bytes
        return httpx.Response(200, json={"text": "hola og118"})

    provider = _provider_with_mock(handler)
    text = asyncio.run(provider.transcribe(FAKE_AUDIO))
    assert text == "hola og118"
    assert "/openai/deployments/whisper/audio/transcriptions" in seen["url"]
    assert "api-version=2024-06-01" in seen["url"]
    assert seen["api_key"] == FAKE_KEY  # key goes in the header, not the URL/body
    # The audio payload + the model field ride in the multipart body.
    assert FAKE_AUDIO in seen["body"]
    assert b"whisper" in seen["body"]


def test_provider_empty_text_body_returns_empty_string() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"text": ""})

    provider = _provider_with_mock(handler)
    assert asyncio.run(provider.transcribe(FAKE_AUDIO)) == ""


def test_provider_non_json_body_maps_to_upstream() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not json")

    provider = _provider_with_mock(handler)
    with pytest.raises(stt_module.STTUpstreamError):
        asyncio.run(provider.transcribe(FAKE_AUDIO))


def test_provider_http_error_maps_to_upstream_without_leaking_secret() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        # Upstream echoes the key in its error body (Azure sometimes does). The
        # provider must NOT surface it.
        return httpx.Response(401, text=f"Invalid api-key: {FAKE_KEY}")

    provider = _provider_with_mock(handler)
    with pytest.raises(stt_module.STTUpstreamError) as excinfo:
        asyncio.run(provider.transcribe(FAKE_AUDIO))
    msg = str(excinfo.value)
    assert "401" in msg
    assert FAKE_KEY not in msg  # the secret never reaches the error message


# --- Route-layer contract tests ----------------------------------------------


class _FakeProvider:
    """Stands in for a configured provider — records calls, returns fixed text.
    Used only to exercise the HTTP contract; it does not pretend the cloud needs
    no real deployment (see test_unconfigured_returns_503)."""

    def __init__(self, text: str = "transcripción de prueba") -> None:
        self.text = text
        self.calls: list[dict] = []

    async def transcribe(self, audio, *, filename, content_type) -> str:
        self.calls.append(
            {"len": len(audio), "filename": filename, "content_type": content_type}
        )
        return self.text


@pytest.fixture
def client() -> TestClient:
    return TestClient(app_module.app)


@pytest.fixture(autouse=True)
def _clean_state(monkeypatch: pytest.MonkeyPatch):
    # Default: no access token (open) unless a test sets one. Reset overrides after.
    monkeypatch.setattr(app_module, "_ACCESS_TOKEN", None)
    yield
    app_module.app.dependency_overrides.clear()


def _override_provider(provider) -> None:
    app_module.app.dependency_overrides[app_module.get_stt_provider] = lambda: provider


def _upload(data: bytes = FAKE_AUDIO) -> dict:
    return {"audio": ("chunk.webm", data, "audio/webm")}


def test_unconfigured_returns_503(client: TestClient) -> None:
    _override_provider(None)  # provider is None => not configured
    resp = client.post("/stt/transcribe", files=_upload())
    assert resp.status_code == 503
    assert resp.json()["detail"]["code"] == "STT_NOT_CONFIGURED"


def test_empty_audio_returns_400(client: TestClient) -> None:
    _override_provider(_FakeProvider())
    resp = client.post("/stt/transcribe", files=_upload(b""))
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "STT_INVALID_REQUEST"


def test_too_short_audio_returns_400(client: TestClient) -> None:
    _override_provider(_FakeProvider())
    resp = client.post(
        "/stt/transcribe", files=_upload(b"\x00" * (stt_module.MIN_AUDIO_BYTES - 1))
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "STT_INVALID_REQUEST"


def test_success_returns_text(client: TestClient) -> None:
    fake = _FakeProvider("hola og118, te escucho")
    _override_provider(fake)
    resp = client.post("/stt/transcribe", files=_upload())
    assert resp.status_code == 200
    assert resp.json() == {"text": "hola og118, te escucho"}
    assert len(fake.calls) == 1
    assert fake.calls[0]["filename"] == "chunk.webm"
    assert fake.calls[0]["content_type"] == "audio/webm"


def test_success_empty_transcript_is_ok(client: TestClient) -> None:
    _override_provider(_FakeProvider(""))
    resp = client.post("/stt/transcribe", files=_upload())
    assert resp.status_code == 200
    assert resp.json() == {"text": ""}


def test_bearer_gate_blocks_then_allows(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(app_module, "_ACCESS_TOKEN", "s3cr3t-token")
    _override_provider(_FakeProvider())

    # No bearer -> 401
    assert client.post("/stt/transcribe", files=_upload()).status_code == 401
    # Wrong bearer -> 401
    bad = client.post(
        "/stt/transcribe", files=_upload(), headers={"Authorization": "Bearer nope"}
    )
    assert bad.status_code == 401
    # Correct bearer -> 200
    ok = client.post(
        "/stt/transcribe",
        files=_upload(),
        headers={"Authorization": "Bearer s3cr3t-token"},
    )
    assert ok.status_code == 200


def test_upstream_error_maps_to_502_without_secret(client: TestClient) -> None:
    class _Boom:
        async def transcribe(self, audio, *, filename, content_type) -> str:
            raise stt_module.STTUpstreamError("stt provider returned HTTP 500")

    _override_provider(_Boom())
    resp = client.post("/stt/transcribe", files=_upload())
    assert resp.status_code == 502
    body = resp.text
    assert FAKE_KEY not in body
    assert resp.json()["detail"]["code"] == "STT_UPSTREAM_ERROR"
