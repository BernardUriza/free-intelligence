"""Per-persona TTS — synthesize a reply in the persona's own voice and post it."""

from __future__ import annotations

import io

import discord
import structlog

from khimeras_shared.tts import should_auto_tts, split_for_tts, synthesize_susurro_tts
from shared.personas import Persona

log = structlog.get_logger()


class VoiceService:
    """Owns one persona's voice. No-op when no susurro TTS client was wired."""

    def __init__(self, persona: Persona, tts_client) -> None:
        self.persona = persona
        self.tts_client = tts_client

    @property
    def enabled(self) -> bool:
        return self.tts_client is not None

    def should_auto_speak(self, text: str, min_chars: int) -> bool:
        """A long reply auto-ships a voice clip (0=off). Gateway-only: no Arbor path."""
        return should_auto_tts(text, min_chars=min_chars, arbor_active=False)

    async def speak(self, channel: discord.abc.Messageable, text: str, *, reason: str) -> None:
        """Synthesize ``text`` in this persona's voice and post it as audio.

        The full text is split into ≤4096-char segments (the speech cap) so a long
        reply is spoken IN FULL across several clips, never truncated. No-op when
        TTS is off or the text is empty. ``reason`` ("manual" 🔊 / "auto" long
        reply) is logged so the two paths stay distinguishable."""
        if self.tts_client is None or not text:
            return
        segments = split_for_tts(text)
        try:
            async with channel.typing():
                for idx, segment in enumerate(segments):
                    audio = await synthesize_susurro_tts(
                        self.tts_client,
                        segment,
                        voice=self.persona.tts_voice,
                    )
                    fname = f"{self.persona.persona_id}{'' if len(segments) == 1 else f'-{idx + 1}'}.mp3"
                    await channel.send(file=discord.File(io.BytesIO(audio), filename=fname))
            log.info(
                "persona_gateway_tts_sent",
                persona_id=self.persona.persona_id,
                voice=self.persona.tts_voice,
                chars=len(text),
                segments=len(segments),
                reason=reason,
            )
        except Exception:
            log.exception("persona_gateway_tts_failed", persona_id=self.persona.persona_id, reason=reason)
