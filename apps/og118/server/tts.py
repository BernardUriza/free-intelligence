"""og118 TTS — minimal, decoupled text-to-speech provider client.

WHY THIS LIVES HERE (and not in fi-glass/core or a shared backend package):
og118 is the canary for the Free Intelligence framework. The pain it surfaced is
real — the backend exposed no voice endpoint, so no `VoiceAdapter.synthesize`
could ever resolve. The *frontend* contract (core's `VoiceAdapter`, fi-glass's
`useVoice`/`SpeakButton`) is already framework-level and reusable. The *backend*
provider client below is conceptually reusable too, BUT there is currently no
shared backend substrate package that og118 imports for this — og118 depends only
on `fi-core` + `fi-runner` (the agent runtime), and a raw TTS HTTP client is not
agent-runtime scope. AURITY's `backend/services/tts/` is reusable but lives in the
AURITY monolith, which og118 does NOT depend on (copying it here would be exactly
the "consumer-local sediment" the canary rule forbids).

So this module is a deliberately MINIMAL, self-contained prototype with a clean
`TTSProvider` Protocol, kept thin and side-effect-free so extraction is trivial.
EXTRACTION GATE (next framework cut, B3-VOICE-FIGLASS-1 / a future `fi-voice`
substrate package): when a second consumer needs backend TTS, lift `TTSProvider`
+ `AzureOpenAITTSProvider` into a shared package and have og118 import it. Until
then, this stays here — and that intent is documented, not buried.

No heavy logic in the route: the FastAPI handler in app.py only validates +
maps errors; all provider/transport detail lives here. No secrets are logged or
embedded; config is read from the ambient environment (cloud injects it).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

import httpx

# --- Contract knobs -----------------------------------------------------------

# Mirror AURITY's cap so the two backends agree on the contract a shared
# VoiceAdapter will eventually depend on.
MAX_TEXT_CHARS = 4096

# response_format -> HTTP Content-Type. Drives the audio blob the frontend
# `VoiceAdapter.synthesize` turns into an `AudioSource`.
_CONTENT_TYPES: dict[str, str] = {
    "mp3": "audio/mpeg",
    "opus": "audio/opus",
    "aac": "audio/aac",
    "flac": "audio/flac",
    "wav": "audio/wav",
    "pcm": "audio/pcm",
}

DEFAULT_FORMAT = "mp3"
DEFAULT_VOICE = "nova"  # same default as AURITY's adapter; keeps the contract aligned


# --- Errors (mapped to safe HTTP status by the route; never carry secrets) ----


class TTSNotConfiguredError(RuntimeError):
    """Raised when the TTS provider env config is absent/incomplete. The route
    maps this to a 503 so staging fails *explicitly and safely* instead of
    pretending voice works. Message names the MISSING var keys only — never any
    value."""


class TTSValidationError(ValueError):
    """Raised for bad client input (empty/too-long text, unknown format, bad
    speed). The route maps this to a 400."""


class TTSUpstreamError(RuntimeError):
    """Raised when the provider call fails (network/HTTP). The route maps this to
    a 502. Carries a short, secret-free reason."""


# --- Validation (pure; shared by the route and tests) -------------------------


def content_type_for(response_format: str) -> str:
    fmt = (response_format or "").lower()
    if fmt not in _CONTENT_TYPES:
        raise TTSValidationError(
            f"unsupported response_format '{response_format}'; "
            f"expected one of {sorted(_CONTENT_TYPES)}"
        )
    return _CONTENT_TYPES[fmt]


def validate_request(text: str, response_format: str, speed: float) -> None:
    """Validate a synthesis request. Raises TTSValidationError on bad input.
    Pure — no I/O, no provider, no secrets."""
    if not text or not text.strip():
        raise TTSValidationError("text cannot be empty")
    if len(text) > MAX_TEXT_CHARS:
        raise TTSValidationError(
            f"text too long ({len(text)} chars; max {MAX_TEXT_CHARS})"
        )
    content_type_for(response_format)  # raises on unknown format
    if not (0.25 <= speed <= 4.0):
        raise TTSValidationError("speed must be between 0.25 and 4.0")


# --- Config (read once from env; None when not configured) ---------------------


@dataclass(frozen=True)
class TTSConfig:
    """Azure OpenAI TTS configuration, namespaced OG118_TTS_* to match the
    existing OG118_* convention (OG118_MODEL, OG118_ACCESS_TOKEN, …). Cloud
    injects these as Container App secrets/vars; locally they live in
    .env.local. Absent → the endpoint is explicitly gated (503), not broken."""

    endpoint: str
    api_key: str
    deployment: str
    api_version: str
    model: str
    default_voice: str

    @classmethod
    def from_env(cls) -> "TTSConfig | None":
        endpoint = os.getenv("OG118_TTS_ENDPOINT", "").strip().rstrip("/")
        api_key = os.getenv("OG118_TTS_API_KEY", "").strip()
        deployment = os.getenv("OG118_TTS_DEPLOYMENT", "").strip()
        # Endpoint + key + deployment are the irreducible trio. Missing any one
        # means "not configured" — the route turns this into a clear 503.
        if not (endpoint and api_key and deployment):
            return None
        return cls(
            endpoint=endpoint,
            api_key=api_key,
            deployment=deployment,
            api_version=os.getenv("OG118_TTS_API_VERSION", "2025-03-01-preview").strip(),
            # Azure puts the deployment in the URL; the body `model` defaults to
            # the deployment name unless explicitly overridden.
            model=os.getenv("OG118_TTS_MODEL", deployment).strip() or deployment,
            default_voice=os.getenv("OG118_TTS_VOICE", DEFAULT_VOICE).strip() or DEFAULT_VOICE,
        )

    def missing_keys(self) -> list[str]:  # pragma: no cover - introspection helper
        return [
            k
            for k, v in (
                ("OG118_TTS_ENDPOINT", self.endpoint),
                ("OG118_TTS_API_KEY", self.api_key),
                ("OG118_TTS_DEPLOYMENT", self.deployment),
            )
            if not v
        ]


# --- Provider Protocol + Azure OpenAI implementation --------------------------


class TTSProvider(Protocol):
    """The seam a future shared `fi-voice` package would expose. Returns raw
    audio bytes for the given format; callers own the Content-Type."""

    async def synthesize(
        self, text: str, *, voice: str, response_format: str, speed: float
    ) -> bytes: ...


class AzureOpenAITTSProvider:
    """Calls Azure OpenAI's audio/speech deployment. Mirrors AURITY's provider
    surface so a shared adapter can later target either backend identically:
        POST {endpoint}/openai/deployments/{deployment}/audio/speech
             ?api-version={version}
        headers: api-key: <key>
        body:    {model, input, voice, response_format, speed}
        returns: binary audio bytes
    """

    def __init__(
        self,
        config: TTSConfig,
        *,
        client: httpx.AsyncClient | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._config = config
        self._client = client  # injectable for tests; None => per-call client
        self._timeout = timeout

    @property
    def default_voice(self) -> str:
        return self._config.default_voice

    def _url(self) -> str:
        c = self._config
        return (
            f"{c.endpoint}/openai/deployments/{c.deployment}/audio/speech"
            f"?api-version={c.api_version}"
        )

    async def synthesize(
        self, text: str, *, voice: str, response_format: str, speed: float
    ) -> bytes:
        body = {
            "model": self._config.model,
            "input": text,
            "voice": voice or self._config.default_voice,
            "response_format": response_format,
            "speed": speed,
        }
        headers = {
            "api-key": self._config.api_key,
            "Content-Type": "application/json",
        }
        try:
            if self._client is not None:
                resp = await self._client.post(
                    self._url(), json=body, headers=headers, timeout=self._timeout
                )
            else:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.post(self._url(), json=body, headers=headers)
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            # Surface status only — never the response body (could echo the key
            # or upstream internals) and never the request headers.
            raise TTSUpstreamError(
                f"tts provider returned HTTP {exc.response.status_code}"
            ) from None
        except httpx.HTTPError as exc:
            raise TTSUpstreamError(f"tts provider request failed: {type(exc).__name__}") from None
        return resp.content


def build_provider() -> TTSProvider | None:
    """Construct the configured provider, or None when TTS is not configured.
    Kept dependency-injectable in the route so tests can override with a fake."""
    config = TTSConfig.from_env()
    if config is None:
        return None
    return AzureOpenAITTSProvider(config)
