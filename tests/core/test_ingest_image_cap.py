"""El tope de imágenes del gateway: ≥5 fotos ya no matan el turno.

AIRE refusa más de `MAX_IMAGES=4` con un 422 que se lleva el turno entero
(backlog `imagenes-claim-check-discord-aire.md`, hoyo #3). Positivo: 6 fotos →
viajan sólo 4 referencias (ninguna se descarga: AIRE baja la URL, #50) y el turno
lleva la nota para que la persona avise en personaje. Rescatado del PR #97.
Resistencia: con 4 fotos no hay nota ni recorte.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from khimeras_shared.runner.agent_client import _last_user_attachments, _last_user_text
from persona_gateway.ingest import MessageIngest
from shared.personas import Persona


def _photo(i: int):
    att = MagicMock()
    att.filename = f"foto{i}.jpg"
    att.content_type = "image/jpeg"
    att.size = 100
    att.url = f"https://cdn.discordapp.com/attachments/1/{i}/foto{i}.jpg?ex=1&is=2&hm=3"
    att.read = AsyncMock(return_value=b"\xff\xd8jpeg")
    return att


def _message(n: int):
    msg = MagicMock()
    msg.id = 99
    msg.attachments = [_photo(i) for i in range(n)]
    msg.flags = SimpleNamespace(voice=False)
    msg.channel.send = AsyncMock()
    return msg


def _ingest() -> MessageIngest:
    return MessageIngest(Persona(persona_id="insult", display_name="Insult", persona_file="insult.md", token_env="X"))


async def test_six_photos_forward_four_and_the_turn_carries_the_note():
    msg = _message(6)
    blocks = await _ingest().attachment_blocks(msg)

    images = [b for b in blocks if b["type"] == "image"]
    assert len(images) == 4
    # Ninguna foto se descarga: las 4 viajan como referencia y las 2 de más ni se tocan.
    assert [a.read.await_count for a in msg.attachments] == [0] * 6
    assert [b["source"]["url"] for b in images] == [a.url for a in msg.attachments[:4]]
    # La nota viaja como texto del turno: el cliente del runner la pliega al user_text.
    user_text = _last_user_text([{"role": "user", "content": [{"type": "text", "text": "mira"}, *blocks]}])
    assert "6 imágenes" in user_text and "primeras 4" in user_text
    assert len(_last_user_attachments([{"role": "user", "content": blocks}])) == 4
    msg.channel.send.assert_not_awaited()  # el aviso lo da la persona, no un error del sistema


async def test_four_photos_pass_whole_with_no_note():
    """Resistencia: en el tope exacto no hay recorte ni nota."""
    msg = _message(4)
    blocks = await _ingest().attachment_blocks(msg)
    assert [b["type"] for b in blocks] == ["image"] * 4
    assert all(a.read.await_count == 0 for a in msg.attachments)
