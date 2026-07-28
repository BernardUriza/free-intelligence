"""Una nota de voz en un DM se transcribe; en un guild NO.

El host es el ÚNICO que transcribe (decisión 2026-07-23) — pero Discord aísla
los canales de DM por bot user, así que el host es estructuralmente SORDO ahí:
nunca ve el mensaje, nunca emite /invite. Con los DM revividos (v4.32.7) una
nota de voz caía en el `return` temprano de `_handle` y moría en silencio total:
sin respuesta, sin "…", sin reacción, sin siquiera marcar `last_message_seen`
para que /health lo viera. Y el DM es justo donde se manda audio desde el
celular.

Mutator rule: positivo (el DM transcribe) + resistencia (el guild NO toca STT,
y cualquier falla degrada al silencio previo en vez de romper el turno).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from khimeras_shared.stt import SusurroSttClient
from persona_gateway import ingest as ingest_mod
from persona_gateway.ingest import MessageIngest
from shared.personas import Persona

pytestmark = pytest.mark.asyncio


def _persona() -> Persona:
    return Persona(
        persona_id="insult",
        display_name="Insult",
        persona_file="insult.md",
        token_env="INSULT_DISCORD_TOKEN",
    )


def _voice_message(*, guild):
    attachment = SimpleNamespace(
        content_type="audio/ogg",
        filename="voice-message.ogg",
        read=AsyncMock(return_value=b"OggS-fake-bytes"),
    )
    return SimpleNamespace(guild=guild, attachments=[attachment], flags=SimpleNamespace(voice=True))


def _client() -> SusurroSttClient:
    return SusurroSttClient(base_url="https://sus.example.com", api_key="k")


async def test_dm_voice_note_is_transcribed():
    ingest = MessageIngest(_persona(), _client())
    with patch.object(ingest_mod, "transcribe_voice_message", new=AsyncMock(return_value="lo que dije")):
        spoken = await ingest.dm_voice_transcript(_voice_message(guild=None))
    assert spoken == "lo que dije"


async def test_guild_voice_note_never_touches_stt():
    """RESISTENCIA — la que protege la doctrina: en un guild el host es el único
    transcriptor. El gateway NO debe convertirse en un segundo consumidor de
    susurro; ni siquiera debe leer el adjunto."""
    message = _voice_message(guild=SimpleNamespace(id=1))
    ingest = MessageIngest(_persona(), _client())
    transcribe = AsyncMock(return_value="no debería correr")
    with patch.object(ingest_mod, "transcribe_voice_message", new=transcribe):
        spoken = await ingest.dm_voice_transcript(message)
    assert spoken == ""
    transcribe.assert_not_awaited()
    message.attachments[0].read.assert_not_awaited()


async def test_no_stt_client_degrades_to_silence_not_a_crash():
    """RESISTENCIA: sin credenciales de susurro el DM se comporta como antes
    (vacío), nunca revienta el turno."""
    ingest = MessageIngest(_persona(), None)
    assert await ingest.dm_voice_transcript(_voice_message(guild=None)) == ""


async def test_dead_susurro_degrades_to_silence():
    """RESISTENCIA: un susurro caído no puede tumbar el turno del DM."""
    ingest = MessageIngest(_persona(), _client())
    with patch.object(ingest_mod, "transcribe_voice_message", new=AsyncMock(side_effect=RuntimeError("502"))):
        assert await ingest.dm_voice_transcript(_voice_message(guild=None)) == ""


async def test_non_audio_dm_attachment_is_left_to_the_document_lane():
    """RESISTENCIA: una imagen en un DM no entra al carril de STT — sigue siendo
    trabajo de `attachment_blocks`."""
    image = SimpleNamespace(content_type="image/png", filename="foto.png", read=AsyncMock())
    message = SimpleNamespace(guild=None, attachments=[image], flags=SimpleNamespace(voice=False))
    ingest = MessageIngest(_persona(), _client())
    transcribe = AsyncMock()
    with patch.object(ingest_mod, "transcribe_voice_message", new=transcribe):
        assert await ingest.dm_voice_transcript(message) == ""
    transcribe.assert_not_awaited()
