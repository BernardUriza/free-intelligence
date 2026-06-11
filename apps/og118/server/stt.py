"""og118 STT — minimal, decoupled speech-to-text provider client.

WHY THIS LIVES HERE (mirrors tts.py): og118 is the canary for the Free
Intelligence framework. The *frontend* contract (core's `VoiceAdapter.transcribe`,
fi-glass's `useDictation`/`ComposerMicSlot`) is already framework-level and
reusable. The *backend* provider client below is conceptually reusable too, BUT
there is no shared backend substrate package og118 imports for this — og118
depends only on `fi-core` + `fi-runner` (the agent runtime), and a raw STT HTTP
client is not agent-runtime scope. AURITY's transcription stack lives in the
AURITY monolith, which og118 does NOT depend on (copying it here would be the
"consumer-local sediment" the canary rule forbids).

So this module is a deliberately MINIMAL, self-contained prototype with a clean
`STTProvider` Protocol, kept thin and side-effect-free so extraction is trivial.
EXTRACTION GATE (a future `fi-voice` substrate package): when a second consumer
needs backend STT, lift `STTProvider` + `AzureOpenAISTTProvider` into the shared
package alongside the TTS pair and have og118 import both. Until then this stays
here — intent documented, not buried.

No heavy logic in the route: the FastAPI handler in app.py only validates + maps
errors; all provider/transport detail lives here. No secrets are logged or
embedded; config is read from the ambient environment (cloud injects it).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

import httpx

# --- Contract knobs -----------------------------------------------------------

# Azure OpenAI Whisper rejects uploads over 25 MB. Cap a little under that so the
# route fails fast with a clear 400 instead of bouncing off the upstream limit.
MAX_AUDIO_BYTES = 25 * 1024 * 1024

# A recording chunk shorter than this is almost certainly silence/an accidental
# tap; transcribing it wastes an upstream call. Reject with a clear 400.
MIN_AUDIO_BYTES = 64

# The filename handed to the multipart upload. Azure uses the extension to pick a
# decoder; webm/opus is what MediaRecorder produces in the browser by default, so
# that is the contract the og118 frontend recorder targets.
DEFAULT_UPLOAD_FILENAME = "chunk.webm"
DEFAULT_UPLOAD_CONTENT_TYPE = "audio/webm"

# MIME types the Azure OpenAI Whisper deployment accepts. Conservative list:
# only types a browser can actually produce (webm, wav) plus common cross-browser
# formats. Unsupported types get a 400 with a stable code so the frontend can
# conserve the artifact and show a recoverable error instead of a silent 502.
SUPPORTED_MIME_TYPES: frozenset[str] = frozenset(
    {
        "audio/webm",
        "audio/wav",
        "audio/x-wav",
        "audio/mp3",
        "audio/mpeg",
        "audio/ogg",
        "audio/flac",
        "audio/mp4",
        "audio/x-m4a",
        "audio/m4a",
    }
)

# Maps a MIME base type to the extension Azure uses to pick the right decoder.
# Anything not in this table falls back to the webm default.
_MIME_TO_EXT: dict[str, str] = {
    "audio/webm": "webm",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/mp3": "mp3",
    "audio/mpeg": "mp3",
    "audio/ogg": "ogg",
    "audio/flac": "flac",
    "audio/mp4": "mp4",
    "audio/x-m4a": "m4a",
    "audio/m4a": "m4a",
}


# --- Errors (mapped to safe HTTP status by the route; never carry secrets) ----


class STTNotConfiguredError(RuntimeError):
    """Raised when the STT provider env config is absent/incomplete. The route
    maps this to a 503 so staging fails *explicitly and safely* instead of
    pretending dictation works. Message names the MISSING var keys only — never
    any value."""


class STTValidationError(ValueError):
    """Raised for bad client input (empty/too-large audio). The route maps this
    to a 400."""


class STTUpstreamError(RuntimeError):
    """Raised when the provider call fails (network/HTTP). The route maps this to
    a 502. Carries a short, secret-free reason."""


# --- Validation (pure; shared by the route and tests) -------------------------


def validate_audio(data: bytes) -> None:
    """Validate a transcription request payload. Raises STTValidationError on bad
    input. Pure — no I/O, no provider, no secrets."""
    if not data:
        raise STTValidationError("audio cannot be empty")
    if len(data) < MIN_AUDIO_BYTES:
        raise STTValidationError(
            f"audio too short ({len(data)} bytes; min {MIN_AUDIO_BYTES})"
        )
    if len(data) > MAX_AUDIO_BYTES:
        raise STTValidationError(
            f"audio too large ({len(data)} bytes; max {MAX_AUDIO_BYTES})"
        )


def validate_mime(content_type: str) -> None:
    """Validate the audio MIME type is one the provider accepts. Strips codec
    parameters before checking (e.g. 'audio/webm; codecs=opus' → 'audio/webm').
    Raises STTValidationError with a stable, client-facing message so the
    frontend can show a recoverable error and conserve the artifact for retry."""
    base = content_type.split(";")[0].strip().lower()
    if base not in SUPPORTED_MIME_TYPES:
        raise STTValidationError(
            f"unsupported audio MIME type: {base!r}; "
            f"accepted: {', '.join(sorted(SUPPORTED_MIME_TYPES))}"
        )


def safe_filename_for_mime(content_type: str) -> str:
    """Derive a safe upload filename from a MIME type so the provider picks the
    right decoder. Strips codec parameters before mapping. Falls back to the
    webm default for unknown types (callers should validate_mime first)."""
    base = content_type.split(";")[0].strip().lower()
    ext = _MIME_TO_EXT.get(base, "webm")
    return f"chunk.{ext}"


# --- Config (read once from env; None when not configured) ---------------------


@dataclass(frozen=True)
class STTConfig:
    """Azure OpenAI Whisper configuration, namespaced OG118_STT_* to match the
    existing OG118_* convention (OG118_MODEL, OG118_TTS_*, …). Cloud injects
    these as Container App secrets/vars; locally they live in .env.local. Absent
    → the endpoint is explicitly gated (503), not broken."""

    endpoint: str
    api_key: str
    deployment: str
    api_version: str
    model: str

    @classmethod
    def from_env(cls) -> "STTConfig | None":
        endpoint = os.getenv("OG118_STT_ENDPOINT", "").strip().rstrip("/")
        api_key = os.getenv("OG118_STT_API_KEY", "").strip()
        deployment = os.getenv("OG118_STT_DEPLOYMENT", "").strip()
        # Endpoint + key + deployment are the irreducible trio. Missing any one
        # means "not configured" — the route turns this into a clear 503.
        if not (endpoint and api_key and deployment):
            return None
        return cls(
            endpoint=endpoint,
            api_key=api_key,
            deployment=deployment,
            # Whisper transcriptions reached GA at 2024-06-01; overridable for
            # deployments pinned to a newer preview.
            api_version=os.getenv("OG118_STT_API_VERSION", "2024-06-01").strip(),
            # Azure puts the deployment in the URL; the body `model` defaults to
            # the deployment name unless explicitly overridden.
            model=os.getenv("OG118_STT_MODEL", deployment).strip() or deployment,
        )

    def missing_keys(self) -> list[str]:  # pragma: no cover - introspection helper
        return [
            k
            for k, v in (
                ("OG118_STT_ENDPOINT", self.endpoint),
                ("OG118_STT_API_KEY", self.api_key),
                ("OG118_STT_DEPLOYMENT", self.deployment),
            )
            if not v
        ]


# --- Provider Protocol + Azure OpenAI implementation --------------------------


class STTProvider(Protocol):
    """The seam a future shared `fi-voice` package would expose. Takes raw audio
    bytes for one recorded chunk and returns the recognized text (possibly
    empty)."""

    async def transcribe(
        self,
        audio: bytes,
        *,
        filename: str = DEFAULT_UPLOAD_FILENAME,
        content_type: str = DEFAULT_UPLOAD_CONTENT_TYPE,
    ) -> str: ...


class AzureOpenAISTTProvider:
    """Calls Azure OpenAI's audio/transcriptions (Whisper) deployment. Mirrors the
    TTS provider surface so a shared adapter can later target either capability
    identically:
        POST {endpoint}/openai/deployments/{deployment}/audio/transcriptions
             ?api-version={version}
        headers:   api-key: <key>
        multipart: file=<audio bytes>, model=<model>, response_format=json
        returns:   {"text": "..."}
    """

    def __init__(
        self,
        config: STTConfig,
        *,
        client: httpx.AsyncClient | None = None,
        timeout: float = 60.0,
    ) -> None:
        self._config = config
        self._client = client  # injectable for tests; None => per-call client
        self._timeout = timeout

    def _url(self) -> str:
        c = self._config
        return (
            f"{c.endpoint}/openai/deployments/{c.deployment}/audio/transcriptions"
            f"?api-version={c.api_version}"
        )

    async def transcribe(
        self,
        audio: bytes,
        *,
        filename: str = DEFAULT_UPLOAD_FILENAME,
        content_type: str = DEFAULT_UPLOAD_CONTENT_TYPE,
    ) -> str:
        files = {"file": (filename, audio, content_type)}
        data = {"model": self._config.model, "response_format": "json"}
        headers = {"api-key": self._config.api_key}
        try:
            if self._client is not None:
                resp = await self._client.post(
                    self._url(),
                    files=files,
                    data=data,
                    headers=headers,
                    timeout=self._timeout,
                )
            else:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.post(
                        self._url(), files=files, data=data, headers=headers
                    )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            # Surface status only — never the response body (could echo the key
            # or upstream internals) and never the request headers.
            raise STTUpstreamError(
                f"stt provider returned HTTP {exc.response.status_code}"
            ) from None
        except httpx.HTTPError as exc:
            raise STTUpstreamError(
                f"stt provider request failed: {type(exc).__name__}"
            ) from None

        try:
            text = resp.json().get("text", "")
        except (ValueError, AttributeError):
            # A 200 with a non-JSON / unexpected body is an upstream contract
            # break — surface it as such without echoing the body.
            raise STTUpstreamError("stt provider returned a non-JSON body") from None
        return text if isinstance(text, str) else ""


def build_provider() -> STTProvider | None:
    """Construct the configured provider, or None when STT is not configured.
    Kept dependency-injectable in the route so tests can override with a fake."""
    config = STTConfig.from_env()
    if config is None:
        return None
    return AzureOpenAISTTProvider(config)
