"""Shared susurro-gateway STT — Discord audio bytes → transcript text.

The susurro gateway exposes ``POST /v1/stt?language=es`` with bearer auth and a
raw audio body (not multipart). Discord voice messages are OGG/opus, so callers
default to ``Content-Type: audio/ogg``. The response JSON is
``{"success", "transcript", "engine"}``: the text lives in ``transcript``, not
``text``.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import httpx
import structlog

log = structlog.get_logger()

STT_TIMEOUT_S = 60.0
STT_COLD_START_ATTEMPTS = 2
STT_COLD_START_BACKOFF_S = 2.0
DEFAULT_AUDIO_CONTENT_TYPE = "audio/ogg"
VOICE_FILENAME_SUFFIXES = (".ogg", ".opus", ".mp3", ".m4a", ".wav", ".webm")

AWAKE_PROBE_PATH = "/docs"
AWAKE_PROBE_TIMEOUT_S = 3.0
WAKE_DEADLINE_S = 90.0
WAKE_POLL_INTERVAL_S = 3.0
WAKE_ETA_SECONDS = 30


def _silence_wav(seconds: float = 0.3, sample_rate: int = 16000) -> bytes:
    """A tiny valid mono 16-bit PCM WAV of silence — the hello-world probe body.

    Built in code rather than committed as a binary blob: 44 bytes of RIFF
    header plus zeroed samples is cheaper to read than to store. Susurro answers
    it in under a second on a warm container (verified against prod: HTTP 200,
    `engine=azure-whisper`; Whisper hallucinates its usual "Subtítulos…
    Amara.org" over silence, which is fine — the probe asserts that the pipeline
    RESPONDS, not what it heard).
    """
    import struct

    frames = int(sample_rate * seconds)
    data = b"\x00\x00" * frames
    header = (
        b"RIFF"
        + struct.pack("<I", 36 + len(data))
        + b"WAVEfmt "
        + struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16)
        + b"data"
        + struct.pack("<I", len(data))
    )
    return header + data


async def susurro_is_awake(*, base_url: str, timeout: float = AWAKE_PROBE_TIMEOUT_S) -> bool:
    """Whether susurro answers RIGHT NOW, cheaply.

    Susurro runs scale-to-zero, and Container Apps' ingress HOLDS a request open
    while the replica boots instead of refusing it — so a sleeping gateway looks
    like a hang, never like a connection error, and the only signal is LATENCY.
    (Its `/v1/health` is not a health check at all: the SPA catch-all serves HTML
    with a 200 whatever the state, the exact proxy-that-cannot-fail trap.) A
    short-timeout GET is therefore the honest probe: fast answer = awake,
    timeout = asleep.
    """
    if not base_url:
        return False
    try:
        async with httpx.AsyncClient(timeout=timeout) as http:
            await http.get(f"{base_url.rstrip('/')}{AWAKE_PROBE_PATH}")
        return True
    except Exception:
        return False


async def wake_susurro(*, base_url: str, api_key: str) -> bool:
    """Boot susurro and prove the STT pipeline answers before the real audio.

    Polls until the container serves, then runs the hello-world transcription —
    because "the web server is up" and "Whisper will answer" are different
    claims, and the second is the one the user's voice note depends on. Returns
    whether the pipeline is confirmed working.
    """
    started = asyncio.get_running_loop().time()
    attempts = 0
    while asyncio.get_running_loop().time() - started < WAKE_DEADLINE_S:
        attempts += 1
        if await susurro_is_awake(base_url=base_url, timeout=WAKE_POLL_INTERVAL_S):
            break
        await asyncio.sleep(WAKE_POLL_INTERVAL_S)
    else:
        log.error("susurro_wake_timed_out", attempts=attempts, deadline_s=WAKE_DEADLINE_S)
        return False

    probe = await transcribe_voice_message(
        _silence_wav(),
        base_url=base_url,
        api_key=api_key,
        content_type="audio/wav",
    )
    elapsed = round(asyncio.get_running_loop().time() - started, 1)
    log.info("susurro_woke", attempts=attempts, elapsed_s=elapsed, probe_ok=probe is not None)
    return probe is not None


def is_audio_attachment(*, content_type: str | None, filename: str | None, voice_message: bool) -> bool:
    """Whether one Discord attachment is audio the STT lane should claim.

    Field-level (not `discord.Message`-level) so BOTH readers share one
    definition: the gateway's ingest and the host's receiver. A drifted copy
    would mean one of them transcribes an attachment the other treats as a
    readable document.
    """
    ctype = (content_type or "").lower()
    if ctype.startswith("audio/"):
        return True
    name = (filename or "").lower()
    return bool(voice_message and (not ctype or name.endswith(VOICE_FILENAME_SUFFIXES)))


@dataclass(frozen=True)
class SusurroSttClient:
    """Immutable handle for the susurro STT endpoint: a base URL + bearer key."""

    base_url: str
    api_key: str


class SttTranscript(str):
    """Transcript string carrying the engine for gateway logs."""

    engine: str | None

    def __new__(cls, value: str, *, engine: str | None = None) -> SttTranscript:
        obj = str.__new__(cls, value)
        obj.engine = engine
        return obj


def _is_transient(error: BaseException) -> bool:
    """Whether a failed STT call is worth one more attempt.

    Transport faults (a timed-out read while the container boots, a refused
    connection) and 5xx / 429 are the cold-start signature. A 4xx is the
    server understanding us and saying no — retrying that only doubles the wait
    before the same answer.
    """
    if isinstance(error, httpx.TimeoutException | httpx.ConnectError | httpx.RemoteProtocolError):
        return True
    status = getattr(getattr(error, "response", None), "status_code", None)
    return status is not None and (status >= 500 or status == 429)


def build_susurro_stt_client(*, base_url: str, api_key: str) -> SusurroSttClient | None:
    """Build the susurro STT client, or ``None`` when unconfigured."""
    if not base_url or not api_key:
        return None
    return SusurroSttClient(base_url=base_url.rstrip("/"), api_key=api_key)


async def transcribe_voice_message(
    audio_data: bytes,
    *,
    base_url: str,
    api_key: str,
    language: str = "es",
    content_type: str = DEFAULT_AUDIO_CONTENT_TYPE,
) -> str | None:
    """Transcribe audio bytes via susurro STT.

    Contract: ``POST {base_url}/v1/stt?language=es`` with bearer auth,
    ``Content-Type`` for the raw audio bytes, and JSON response text read from
    ``transcript`` (not ``text``). Returns ``None`` when unconfigured, when the
    transcript is empty, or on any exception so a Discord turn never crashes.

    Susurro runs scale-to-zero (``minReplicas=0``) and cold-started 19 times in
    one day, so a voice note is routinely the request that WAKES it: the first
    POST waits on container startup and dies on the read timeout. A single
    attempt made transcription a coin flip against Azure's boot time — 3 of 10
    voice notes lost on 2026-08-06, each one landing as "el audio no me entra".
    A client of a scale-to-zero service must absorb the start it guarantees, so
    transport failures (timeout / connect / 5xx) get one retry — the first
    attempt paid for the boot, the second hits a warm server.
    """
    if not base_url or not api_key:
        log.warning("susurro_stt_not_configured")
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": content_type or DEFAULT_AUDIO_CONTENT_TYPE,
    }
    url = f"{base_url.rstrip('/')}/v1/stt"
    for attempt in range(1, STT_COLD_START_ATTEMPTS + 1):
        try:
            async with httpx.AsyncClient(timeout=STT_TIMEOUT_S) as http:
                response = await http.post(
                    url,
                    params={"language": language},
                    headers=headers,
                    content=audio_data,
                )
                response.raise_for_status()
                data = response.json()

            text = (data.get("transcript") or "").strip()
            if not text:
                log.warning("susurro_stt_empty_transcription", engine=data.get("engine"))
                return None

            engine = data.get("engine")
            log.info("susurro_stt_transcribed", length=len(text), engine=engine, attempt=attempt)
            return SttTranscript(text, engine=engine)
        except Exception as exc:
            retriable = _is_transient(exc) and attempt < STT_COLD_START_ATTEMPTS
            log.error(
                "susurro_stt_failed",
                error=str(exc),
                error_type=type(exc).__name__,
                attempt=attempt,
                will_retry=retriable,
            )
            if not retriable:
                return None
            await asyncio.sleep(STT_COLD_START_BACKOFF_S)
    return None


__all__ = [
    "AWAKE_PROBE_TIMEOUT_S",
    "DEFAULT_AUDIO_CONTENT_TYPE",
    "STT_COLD_START_ATTEMPTS",
    "STT_COLD_START_BACKOFF_S",
    "STT_TIMEOUT_S",
    "VOICE_FILENAME_SUFFIXES",
    "WAKE_DEADLINE_S",
    "WAKE_ETA_SECONDS",
    "SttTranscript",
    "SusurroSttClient",
    "build_susurro_stt_client",
    "is_audio_attachment",
    "susurro_is_awake",
    "transcribe_voice_message",
    "wake_susurro",
]
