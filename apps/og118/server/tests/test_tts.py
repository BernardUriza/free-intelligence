"""Tests for the og118 TTS foundation (B3-VOICE-BACKEND-1).

Two layers:
  * Provider unit tests (tts.py) — validation, config-from-env, request
    construction and secret hygiene, driven by httpx.MockTransport so NOTHING
    touches the network and NO real key is ever needed.
  * Route contract tests (app.py) — the /tts/synthesize HTTP surface: explicit
    503 when unconfigured, 400 on bad input, 200 + audio on success, 401 behind
    the bearer gate, and the invariant that error bodies never echo a secret.

The fake provider deliberately does NOT mask the fact that a real Azure OpenAI
deployment is required in staging: `test_unconfigured_returns_503` proves the
gate, and the provider-construction tests prove the real call shape.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient

import app as app_module
import tts as tts_module

FAKE_AUDIO = b"ID3\x03fake-mp3-payload\x00\x01"
FAKE_KEY = "sk-test-do-not-leak-1234567890"


# --- Provider-layer unit tests (no network, no real secret) -------------------


def test_validate_request_rejects_empty_text() -> None:
    with pytest.raises(tts_module.TTSValidationError):
        tts_module.validate_request("", "mp3", 1.0)
    with pytest.raises(tts_module.TTSValidationError):
        tts_module.validate_request("   ", "mp3", 1.0)


def test_validate_request_rejects_too_long_text() -> None:
    too_long = "a" * (tts_module.MAX_TEXT_CHARS + 1)
    with pytest.raises(tts_module.TTSValidationError):
        tts_module.validate_request(too_long, "mp3", 1.0)


def test_validate_request_rejects_unknown_format() -> None:
    with pytest.raises(tts_module.TTSValidationError):
        tts_module.validate_request("hi", "ogg", 1.0)


def test_validate_request_rejects_out_of_range_speed() -> None:
    with pytest.raises(tts_module.TTSValidationError):
        tts_module.validate_request("hi", "mp3", 0.1)
    with pytest.raises(tts_module.TTSValidationError):
        tts_module.validate_request("hi", "mp3", 5.0)


def test_content_type_mapping() -> None:
    assert tts_module.content_type_for("mp3") == "audio/mpeg"
    assert tts_module.content_type_for("opus") == "audio/opus"
    assert tts_module.content_type_for("WAV") == "audio/wav"  # case-insensitive


def test_config_from_env_none_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("OG118_TTS_ENDPOINT", "OG118_TTS_API_KEY", "OG118_TTS_DEPLOYMENT"):
        monkeypatch.delenv(key, raising=False)
    assert tts_module.TTSConfig.from_env() is None


def test_config_from_env_none_when_partial(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OG118_TTS_ENDPOINT", "https://x.openai.azure.com")
    monkeypatch.setenv("OG118_TTS_API_KEY", FAKE_KEY)
    monkeypatch.delenv("OG118_TTS_DEPLOYMENT", raising=False)  # missing the trio's 3rd
    assert tts_module.TTSConfig.from_env() is None


def test_config_from_env_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OG118_TTS_ENDPOINT", "https://x.openai.azure.com/")  # trailing slash trimmed
    monkeypatch.setenv("OG118_TTS_API_KEY", FAKE_KEY)
    monkeypatch.setenv("OG118_TTS_DEPLOYMENT", "tts-hd")
    cfg = tts_module.TTSConfig.from_env()
    assert cfg is not None
    assert cfg.endpoint == "https://x.openai.azure.com"  # no trailing slash
    assert cfg.deployment == "tts-hd"
    assert cfg.model == "tts-hd"  # defaults to deployment
    assert cfg.default_voice == "nova"
    assert cfg.api_version  # has a default


def _provider_with_mock(handler) -> tts_module.AzureOpenAITTSProvider:
    cfg = tts_module.TTSConfig(
        endpoint="https://x.openai.azure.com",
        api_key=FAKE_KEY,
        deployment="tts-hd",
        api_version="2025-03-01-preview",
        model="tts-hd",
        default_voice="nova",
    )
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return tts_module.AzureOpenAITTSProvider(cfg, client=client)


def test_provider_builds_correct_request_and_returns_audio() -> None:
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        seen["url"] = str(request.url)
        seen["api_key"] = request.headers.get("api-key")
        seen["json"] = json.loads(request.content)
        return httpx.Response(200, content=FAKE_AUDIO)

    provider = _provider_with_mock(handler)
    audio = asyncio.run(
        provider.synthesize("hola", voice="nova", response_format="mp3", speed=1.0)
    )
    assert audio == FAKE_AUDIO
    assert "/openai/deployments/tts-hd/audio/speech" in seen["url"]
    assert "api-version=2025-03-01-preview" in seen["url"]
    assert seen["api_key"] == FAKE_KEY  # key goes in the header, not the URL/body
    assert seen["json"] == {
        "model": "tts-hd",
        "input": "hola",
        "voice": "nova",
        "response_format": "mp3",
        "speed": 1.0,
    }


def test_provider_http_error_maps_to_upstream_without_leaking_secret() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        # Upstream echoes the key in its error body (Azure sometimes does). The
        # provider must NOT surface it.
        return httpx.Response(401, text=f"Invalid api-key: {FAKE_KEY}")

    provider = _provider_with_mock(handler)
    with pytest.raises(tts_module.TTSUpstreamError) as excinfo:
        asyncio.run(provider.synthesize("hi", voice="nova", response_format="mp3", speed=1.0))
    msg = str(excinfo.value)
    assert "401" in msg
    assert FAKE_KEY not in msg  # the secret never reaches the error message


# --- Route-layer contract tests ----------------------------------------------


class _FakeProvider:
    """Stands in for a configured provider — records calls, returns fixed bytes.
    Used only to exercise the HTTP contract; it does not pretend the cloud needs
    no real deployment (see test_unconfigured_returns_503)."""

    default_voice = "nova"

    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def synthesize(self, text, *, voice, response_format, speed) -> bytes:
        self.calls.append(
            {"text": text, "voice": voice, "response_format": response_format, "speed": speed}
        )
        return FAKE_AUDIO


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
    app_module.app.dependency_overrides[app_module.get_tts_provider] = lambda: provider


def test_health_still_ok(client: TestClient) -> None:
    assert client.get("/health").json() == {"ok": True}


def test_unconfigured_returns_503(client: TestClient) -> None:
    _override_provider(None)  # provider is None => not configured
    resp = client.post("/tts/synthesize", json={"text": "hola"})
    assert resp.status_code == 503
    assert resp.json()["detail"]["code"] == "TTS_NOT_CONFIGURED"


def test_empty_text_returns_400(client: TestClient) -> None:
    _override_provider(_FakeProvider())
    resp = client.post("/tts/synthesize", json={"text": "   "})
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "TTS_INVALID_REQUEST"


def test_too_long_text_returns_400(client: TestClient) -> None:
    _override_provider(_FakeProvider())
    resp = client.post(
        "/tts/synthesize", json={"text": "a" * (tts_module.MAX_TEXT_CHARS + 1)}
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "TTS_INVALID_REQUEST"


def test_bad_format_returns_400(client: TestClient) -> None:
    _override_provider(_FakeProvider())
    resp = client.post("/tts/synthesize", json={"text": "hi", "response_format": "ogg"})
    assert resp.status_code == 400


def test_success_returns_audio_blob(client: TestClient) -> None:
    fake = _FakeProvider()
    _override_provider(fake)
    resp = client.post(
        "/tts/synthesize", json={"text": "hola og118", "voice": "shimmer", "speed": 1.1}
    )
    assert resp.status_code == 200
    assert resp.content == FAKE_AUDIO
    assert resp.headers["content-type"] == "audio/mpeg"
    assert fake.calls == [
        {"text": "hola og118", "voice": "shimmer", "response_format": "mp3", "speed": 1.1}
    ]


def test_success_opus_content_type(client: TestClient) -> None:
    _override_provider(_FakeProvider())
    resp = client.post("/tts/synthesize", json={"text": "hi", "response_format": "opus"})
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "audio/opus"


def test_bearer_gate_blocks_then_allows(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(app_module, "_ACCESS_TOKEN", "s3cr3t-token")
    _override_provider(_FakeProvider())

    # No bearer -> 401
    assert client.post("/tts/synthesize", json={"text": "hi"}).status_code == 401
    # Wrong bearer -> 401
    bad = client.post(
        "/tts/synthesize", json={"text": "hi"}, headers={"Authorization": "Bearer nope"}
    )
    assert bad.status_code == 401
    # Correct bearer -> 200
    ok = client.post(
        "/tts/synthesize",
        json={"text": "hi"},
        headers={"Authorization": "Bearer s3cr3t-token"},
    )
    assert ok.status_code == 200


def test_upstream_error_maps_to_502_without_secret(client: TestClient) -> None:
    class _Boom:
        default_voice = "nova"

        async def synthesize(self, text, *, voice, response_format, speed) -> bytes:
            raise tts_module.TTSUpstreamError("tts provider returned HTTP 500")

    _override_provider(_Boom())
    resp = client.post("/tts/synthesize", json={"text": "hi"})
    assert resp.status_code == 502
    body = resp.text
    assert FAKE_KEY not in body
    assert resp.json()["detail"]["code"] == "TTS_UPSTREAM_ERROR"
