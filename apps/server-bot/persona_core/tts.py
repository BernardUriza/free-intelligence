"""Shared susurro-gateway TTS — text → MP3 bytes, persona-neutral.

Both Insult's ``VoiceCog`` and the ``persona_gateway`` (Vultur and future
siblings) synthesize speech through the **susurro gateway** — a project-keyed
proxy (``sus.bernarduriza.com``) that routes to a dedicated Azure OpenAI behind a
single bearer key. This is the ONE place the client wiring + the speech call live,
so a sibling persona owns its OWN voice (e.g. Vultur in ``echo``) without each
surface duplicating the transport. The voice is the CALLER's choice; this module
is voice-agnostic.

Migrated 2026-06-19 off the direct Azure OpenAI ``tts`` deployment (deleted) onto
the susurro gateway. The gateway's ``POST /v1/tts`` returns the raw MP3 bytes
(``audio/mpeg``), NOT JSON.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

# The friendly gateway URL Bernard presents — the canonical base for every call.
DEFAULT_SUSURRO_URL = "https://sus.bernarduriza.com"
_MAX_TTS_CHARS = 4096  # speech input cap (mirrors the upstream Azure speech limit)
_TTS_TIMEOUT_S = 60.0


@dataclass(frozen=True)
class SusurroTtsClient:
    """Immutable handle for the susurro TTS endpoint: a base URL + bearer key.

    There is no persistent connection to pool — each ``synthesize`` is one HTTP
    POST — so this is a value object, not an SDK client. ``None`` (instead of
    raising) is how a surface treats "no susurro creds" as "voice off"."""

    base_url: str
    api_key: str


def build_susurro_tts_client(*, base_url: str, api_key: str) -> SusurroTtsClient | None:
    """Build the susurro TTS client, or ``None`` when unconfigured.

    Returning ``None`` lets a surface treat missing creds as "voice off" rather
    than a crash — the gateway/VoiceCog stays alive without susurro env, same
    posture as Insult's lazy ``_get_tts_client``."""
    if not base_url or not api_key:
        return None
    return SusurroTtsClient(base_url=base_url.rstrip("/"), api_key=api_key)


def should_auto_tts(text: str, *, min_chars: int, arbor_active: bool) -> bool:
    """Whether a delivered reply should auto-speak (one audio of the full text).

    Auto-TTS fires for LONG replies so a wall of text comes with a voice clip you
    can listen to instead of reading. Two hard gates:

    - ``min_chars <= 0`` disables the feature entirely (the off switch).
    - ``arbor_active`` (an ``arbor_tts_url`` is configured) FORBIDS auto-fire:
      Arbor drives a personal ChatGPT session and ``voice.md`` mandates it stays
      on-demand only (automatic traffic flags the account). Auto-TTS is a
      gateway-only capability; with Arbor on, 🔊 stays manual.
    """
    if min_chars <= 0 or arbor_active:
        return False
    return len(text.strip()) >= min_chars


def split_for_tts(text: str, *, cap: int = _MAX_TTS_CHARS) -> list[str]:
    """Split ``text`` into ≤``cap`` segments on paragraph/space boundaries so a
    reply longer than the speech limit is spoken IN FULL across several audio
    clips, never silently truncated. Returns ``[]`` for empty text and a
    single-element list when it already fits."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= cap:
        return [text]
    parts: list[str] = []
    remaining = text
    while len(remaining) > cap:
        cut = remaining.rfind("\n", 0, cap)
        if cut < cap // 2:
            cut = remaining.rfind(" ", 0, cap)
        if cut < cap // 2:
            cut = cap
        parts.append(remaining[:cut].strip())
        remaining = remaining[cut:].strip()
    if remaining:
        parts.append(remaining)
    return parts


async def synthesize_susurro_tts(
    client: SusurroTtsClient,
    text: str,
    *,
    voice: str,
    fmt: str = "mp3",
) -> bytes:
    """Synthesize ``text`` to MP3 bytes in ``voice`` via the gateway ``/v1/tts``.

    Caller owns the voice (Insult → onyx, ALICE → nova, Vultur → echo). Input is
    capped at the gateway's speech limit; chunk reassembly is the caller's job.
    The response body is the raw audio (``audio/mpeg``), returned as bytes."""
    headers = {
        "Authorization": f"Bearer {client.api_key}",
        "Content-Type": "application/json",
    }
    payload = {"input": text[:_MAX_TTS_CHARS], "voice": voice, "format": fmt}
    async with httpx.AsyncClient(timeout=_TTS_TIMEOUT_S) as http:
        response = await http.post(f"{client.base_url}/v1/tts", headers=headers, json=payload)
        response.raise_for_status()
        return response.content


__all__ = [
    "DEFAULT_SUSURRO_URL",
    "SusurroTtsClient",
    "build_susurro_tts_client",
    "should_auto_tts",
    "split_for_tts",
    "synthesize_susurro_tts",
]
