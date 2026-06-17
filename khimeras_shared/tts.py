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


__all__ = ["AZURE_TTS_API_VERSION", "build_azure_tts_client", "synthesize_azure_tts"]
