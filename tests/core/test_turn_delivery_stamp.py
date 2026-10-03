"""Un turno que no entregó nada deja de contar como entregado (issue #40).

El 2026-08-11 Frugívoro empezó a escribir en `#general` y no llegó nada: ni
respuesta, ni el `…` de rescate, ni reacción. El KQL de Bernard lo confirmó — el
runner se estaba reiniciando a media petición y devolvió el turno con texto
vacío. `turns.py` regresaba en silencio, sin loguear, y `gateway.py` sellaba
`last_turn_delivered` de todos modos: /health decía "contestó hace un momento"
cuando nadie recibió nada, y `mute_suspected` no podía encenderse jamás por esta
vía.

Regla del mutador: positivo (una respuesta normal reporta entrega) + resistencia
(texto vacío y sólo-marcadores NO reportan entrega y dicen por qué en el log;
sólo-GIF y sólo-reacción SÍ, porque el usuario vio algo).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import discord

from persona_gateway.gateway import PersonaClient
from shared.personas import Persona

URL = "https://tenor.com/view/dance-gif-813685"
CATALOG = f"fiesta: {URL}\n"


class _Typing:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _client(reply_text: str) -> PersonaClient:
    persona = Persona(
        persona_id="frugivoro",
        display_name="Frugívoro",
        persona_file="frugivoro.md",
        token_env="DISCORD_TOKEN",
    )
    memory = MagicMock()
    memory.store = AsyncMock()
    memory.get_recent = AsyncMock(return_value=[])
    agent_client = MagicMock()
    agent_client.chat = AsyncMock(return_value=SimpleNamespace(text=reply_text, model_used="claude"))
    return PersonaClient(persona, memory, agent_client, intents=discord.Intents.none())


def _channel():
    channel = MagicMock(spec=discord.TextChannel)
    channel.send = AsyncMock(return_value=MagicMock(id=1))
    channel.typing = MagicMock(return_value=_Typing())
    return channel


async def _run(client: PersonaClient, channel, *, react_to=None) -> bool:
    return await client._turns.run_and_deliver(
        channel=channel,
        channel_id="1489180895264116736",
        user_id="907264175246569543",
        guild_id="G1",
        channel_name="general",
        messages=[{"role": "user", "content": "¿los confites llevan algo raro?"}],
        bot_user_id="1488415576551325906",
        react_to=react_to,
    )


# --- POSITIVO -----------------------------------------------------------------


async def test_a_normal_reply_reports_delivered():
    """El caso sano: hubo prosa, se mandó, y el turno lo reporta."""
    client = _client("La cera de las manzanas es de origen animal, carnal.")
    channel = _channel()

    assert await _run(client, channel) is True
    assert channel.send.await_count >= 1


# --- RESISTENCIA 1: el turno que se perdió el 2026-08-11 ----------------------


async def test_empty_runner_text_is_not_delivered():
    """El runner devolvió "" — nadie vio nada, y el turno tiene que decirlo.

    Éste es el que estaba rojo antes del arreglo: la función regresaba `None` y
    el gateway sellaba igual.
    """
    client = _client("")
    channel = _channel()

    assert await _run(client, channel) is False
    channel.send.assert_not_awaited()


async def test_empty_runner_text_says_why_in_the_log():
    """Un turno huérfano se busca en KQL, no se deduce por un evento ausente."""
    client = _client("")
    channel = _channel()

    with patch("persona_gateway.turns.log") as log:
        await _run(client, channel)

    events = {c.args[0]: c.kwargs for c in log.info.call_args_list if c.args}
    assert "persona_gateway_turn_empty" in events, "la rama muda volvió a salir sin dejar rastro"
    assert events["persona_gateway_turn_empty"]["reason"] == "runner_empty"
    assert events["persona_gateway_turn_empty"]["delivered"] is False
    assert "persona_gateway_turn_complete" not in events


# --- RESISTENCIA 2: los marcadores se comieron el texto -----------------------


async def test_markers_only_reply_is_not_delivered():
    """Contestó SÓLO con marcadores durables: se persisten y se borran del texto.

    Queda la cadena vacía. El efecto durable ocurrió, pero el usuario tampoco vio
    nada — así que no cuenta como entrega, y la razón lo distingue del caso de
    arriba.
    """
    client = _client("[REMEMBER: a Álex le dan asco los confites encerados]")
    client._turns._markers.route = AsyncMock(return_value="")
    channel = _channel()

    with patch("persona_gateway.turns.log") as log:
        delivered = await _run(client, channel)

    assert delivered is False
    channel.send.assert_not_awaited()
    events = {c.args[0]: c.kwargs for c in log.info.call_args_list if c.args}
    assert events["persona_gateway_turn_empty"]["reason"] == "markers_only"


# --- RESISTENCIA 3: el arreglo no puede volver mudo lo que hoy SÍ llega -------


async def test_gif_only_reply_counts_as_delivered():
    """Sin prosa, pero el GIF se posteó. El usuario sí vio algo."""
    client = _client("[GIF: fiesta]")
    channel = _channel()

    with patch("persona_core.gifs.load_guidance", return_value=CATALOG):
        delivered = await _run(client, channel)

    assert delivered is True
    assert URL in [c.args[0] for c in channel.send.await_args_list]


async def test_reaction_only_reply_counts_as_delivered():
    """Sin prosa y sin GIF, pero el emoji sí aterrizó en el mensaje.

    Decisión de Álex el 2026-08-31: el usuario ve la reacción, así que cuenta.
    Sin esto, una persona que sólo reacciona se vería muda para /health.
    """
    client = _client("[REACT:👀]")
    channel = _channel()
    target = MagicMock(spec=discord.Message)

    with patch("persona_gateway.turns.add_reactions", new=AsyncMock()):
        delivered = await _run(client, channel, react_to=target)

    assert delivered is True
    channel.send.assert_not_awaited()


async def test_a_reaction_with_nowhere_to_land_is_not_delivered():
    """El mismo emoji, pero sin mensaje al cual pegarlo, se cae al piso.

    El código ya lo loguea como `reactions_dropped_no_target`. Si eso contara
    como entrega, volveríamos al bug por la puerta de atrás.
    """
    client = _client("[REACT:👀]")
    channel = _channel()

    assert await _run(client, channel, react_to=None) is False
