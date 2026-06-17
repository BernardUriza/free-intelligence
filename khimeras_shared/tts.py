"""Shared Azure OpenAI TTS — text → MP3 bytes, persona-neutral.

Both Insult's ``VoiceCog`` and the ``persona_gateway`` (Vultur and future
siblings) synthesize speech via the same Azure OpenAI ``tts`` deployment. This is
the ONE place the client wiring + the speech call live, so a sibling persona owns
its OWN voice (e.g. Vultur in ``echo``) without each surface duplicating the
Azure client — the same capability-ownership rule that gave the gateway its own
Discord host. The voice is the CALLER's choice; this module is voice-agnostic.
"""

from __future__ import annotations

from openai import AsyncAzureOpenAI

# The TTS deployment lives on the same Azure OpenAI account as gpt-4.1/embeddings
# (insult-openai, northcentralus). API version pinned to the one the VoiceCog has
# used in production.
AZURE_TTS_API_VERSION = "2024-12-01-preview"
_MAX_TTS_CHARS = 4096  # Azure speech input cap


def build_azure_tts_client(*, endpoint: str, api_key: str) -> AsyncAzureOpenAI | None:
    """Build the Azure OpenAI client for TTS, or ``None`` when unconfigured.

    Returning ``None`` (instead of raising) lets a surface treat "no Azure creds"
    as "voice off" rather than a crash — the gateway stays alive without TTS env,
    same posture as Insult's lazy ``_get_tts_client``."""
    if not endpoint or not api_key:
        return None
    return AsyncAzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version=AZURE_TTS_API_VERSION,
    )


def should_auto_tts(text: str, *, min_chars: int, arbor_active: bool) -> bool:
    """Whether a delivered reply should auto-speak (one audio of the full text).

    Auto-TTS fires for LONG replies so a wall of text comes with a voice clip you
    can listen to instead of reading. Two hard gates:

    - ``min_chars <= 0`` disables the feature entirely (the off switch).
    - ``arbor_active`` (an ``arbor_tts_url`` is configured) FORBIDS auto-fire:
      Arbor drives a personal ChatGPT session and ``voice.md`` mandates it stays
      on-demand only (automatic traffic flags the account). Auto-TTS is an
      Azure-only capability; with Arbor on, 🔊 stays manual.
    """
    if min_chars <= 0 or arbor_active:
        return False
    return len(text.strip()) >= min_chars


def split_for_tts(text: str, *, cap: int = _MAX_TTS_CHARS) -> list[str]:
    """Split ``text`` into ≤``cap`` segments on paragraph/space boundaries so a
    reply longer than Azure's 4096-char limit is spoken IN FULL across several
    audio clips, never silently truncated. Returns ``[]`` for empty text and a
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


async def synthesize_azure_tts(
    client: AsyncAzureOpenAI,
    text: str,
    *,
    voice: str,
    deployment: str,
) -> bytes:
    """Synthesize ``text`` to MP3 bytes in ``voice`` via the Azure ``deployment``.

    Caller owns the voice (Insult → onyx, ALICE → nova, Vultur → echo). Input is
    capped at Azure's 4096-char limit; chunk reassembly is the caller's job."""
    response = await client.audio.speech.create(
        model=deployment,
        voice=voice,
        input=text[:_MAX_TTS_CHARS],
        response_format="mp3",
    )
    return response.content


__all__ = [
    "AZURE_TTS_API_VERSION",
    "build_azure_tts_client",
    "should_auto_tts",
    "split_for_tts",
    "synthesize_azure_tts",
]
